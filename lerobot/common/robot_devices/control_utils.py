########################################################################################
# Utilities
########################################################################################


import logging
import time
import traceback
from contextlib import nullcontext
from copy import copy
from functools import cache
import signal
import threading

import cv2
import torch
import tqdm
from deepdiff import DeepDiff
from termcolor import colored

from lerobot.common.datasets.image_writer import safe_stop_image_writer
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.utils import get_features_from_robot
from lerobot.common.robot_devices.robots.utils import Robot
from lerobot.common.robot_devices.utils import busy_wait
from lerobot.common.utils.utils import get_safe_torch_device, has_method

# Global flag for keyboard interrupt
should_stop = False

def signal_handler(sig, frame):
    """Handle keyboard interrupt signal."""
    global should_stop
    logging.info("=== Signal handler called ===")
    logging.info(f"Signal: {sig}")
    logging.info(f"Frame: {frame}")
    logging.info(f"Current thread: {threading.current_thread().ident}")
    logging.info(f"Main thread: {threading.main_thread().ident}")
    logging.info("Setting should_stop to True")
    should_stop = True
    
    # Force exit after a short delay to allow cleanup
    logging.info("Waiting for 1 second before force exit")
    time.sleep(1)
    if should_stop:
        logging.info("Forcing exit...")
        import os
        os._exit(1)

# Register the signal handler for both SIGINT and SIGTERM
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def log_control_info(robot: Robot, dt_s, episode_index=None, frame_index=None, fps=None):
    log_items = []
    if episode_index is not None:
        log_items.append(f"ep:{episode_index}")
    if frame_index is not None:
        log_items.append(f"frame:{frame_index}")

    def log_dt(shortname, dt_val_s):
        nonlocal log_items, fps
        info_str = f"{shortname}:{dt_val_s * 1000:5.2f} ({1/ dt_val_s:3.1f}hz)"
        if fps is not None:
            actual_fps = 1 / dt_val_s
            if actual_fps < fps - 1:
                info_str = colored(info_str, "yellow")
        log_items.append(info_str)

    # total step time displayed in milliseconds and its frequency
    log_dt("dt", dt_s)

    # TODO(aliberts): move robot-specific logs logic in robot.print_logs()
    if not robot.robot_type.startswith("stretch"):
        for name in robot.leader_arms:
            key = f"read_leader_{name}_pos_dt_s"
            if key in robot.logs:
                log_dt("dtRlead", robot.logs[key])

        for name in robot.follower_arms:
            key = f"write_follower_{name}_goal_pos_dt_s"
            if key in robot.logs:
                log_dt("dtWfoll", robot.logs[key])

            key = f"read_follower_{name}_pos_dt_s"
            if key in robot.logs:
                log_dt("dtRfoll", robot.logs[key])

        for name in robot.cameras:
            key = f"read_camera_{name}_dt_s"
            if key in robot.logs:
                log_dt(f"dtR{name}", robot.logs[key])

    info_str = " ".join(log_items)
    logging.info(info_str)


@cache
def is_headless():
    """Detects if python is running without a monitor."""
    try:
        import pynput  # noqa

        return False
    except Exception:
        print(
            "Error trying to import pynput. Switching to headless mode. "
            "As a result, the video stream from the cameras won't be shown, "
            "and you won't be able to change the control flow with keyboards. "
            "For more info, see traceback below.\n"
        )
        traceback.print_exc()
        print()
        return True


def predict_action(observation, policy, device, use_amp):
    observation = copy(observation)
    with (
        torch.inference_mode(),
        torch.autocast(device_type=device.type) if device.type == "cuda" and use_amp else nullcontext(),
    ):
        # Convert to pytorch format: channel first and float32 in [0,1] with batch dimension
        for name in observation:
            if "image" in name:
                observation[name] = observation[name].type(torch.float32) / 255
                observation[name] = observation[name].permute(2, 0, 1).contiguous()
            observation[name] = observation[name].unsqueeze(0)
            observation[name] = observation[name].to(device)

        # Compute the next action with the policy
        # based on the current observation
        action = policy.select_action(observation)

        # Remove batch dimension
        action = action.squeeze(0)

        # Move to cpu, if not already the case
        action = action.to("cpu")

    return action


def init_keyboard_listener():
    # Allow to exit early while recording an episode or resetting the environment,
    # by tapping the right arrow key '->'. This might require a sudo permission
    # to allow your terminal to monitor keyboard events.
    events = {}
    events["exit_early"] = False
    events["rerecord_episode"] = False
    events["stop_recording"] = False

    if is_headless():
        logging.warning(
            "Headless environment detected. On-screen cameras display and keyboard inputs will not be available."
        )
        listener = None
        return listener, events

    # Only import pynput if not in a headless environment
    from pynput import keyboard

    def on_press(key):
        try:
            if key == keyboard.Key.right:
                print("Right arrow key pressed. Exiting loop...")
                events["exit_early"] = True
            elif key == keyboard.Key.left:
                print("Left arrow key pressed. Exiting loop and rerecord the last episode...")
                events["rerecord_episode"] = True
                events["exit_early"] = True
            elif key == keyboard.Key.esc:
                print("Escape key pressed. Stopping data recording...")
                events["stop_recording"] = True
                events["exit_early"] = True
        except Exception as e:
            print(f"Error handling key press: {e}")

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    return listener, events


def warmup_record(
    robot,
    events,
    enable_teleoperation,
    warmup_time_s,
    display_cameras,
    fps,
):
    logging.info("Starting warmup record...")
    try:
        control_loop(
            robot=robot,
            control_time_s=warmup_time_s,
            display_cameras=display_cameras,
            events=events,
            fps=fps,
            teleoperate=enable_teleoperation,
        )
        logging.info("Warmup record completed successfully")
    except Exception as e:
        logging.error(f"Error during warmup record: {e}")
        logging.error(traceback.format_exc())
        raise


def record_episode(
    robot,
    dataset,
    events,
    episode_time_s,
    display_cameras,
    policy,
    device,
    use_amp,
    fps,
):
    control_loop(
        robot=robot,
        control_time_s=episode_time_s,
        display_cameras=display_cameras,
        dataset=dataset,
        events=events,
        policy=policy,
        device=device,
        use_amp=use_amp,
        fps=fps,
        teleoperate=policy is None,
    )


@safe_stop_image_writer
def control_loop(
    robot,
    control_time_s=None,
    teleoperate=False,
    display_cameras=False,
    dataset: LeRobotDataset | None = None,
    events=None,
    policy=None,
    device: torch.device | str | None = None,
    use_amp: bool | None = None,
    fps: int | None = None,
):
    global should_stop
    should_stop = False

    # Initialize keyboard listener
    listener, keyboard_events = init_keyboard_listener()
    if events is None:
        events = {"exit_early": False, "rerecord_episode": False, "stop_recording": False}
    events.update(keyboard_events)
    if not robot.is_connected:
        robot.connect()
    # Initialize cameras first with timeout
    if hasattr(robot, 'cameras'):
        for name, camera in robot.cameras.items():
            if should_stop:
                break
            try:
                if not camera.is_connected:
                    logging.info(f"Connecting camera {name}...")
                    camera.connect()
                    # Try to read a frame to ensure the camera is working
                    try:
                        camera.async_read()
                        logging.info(f"Camera {name} connected successfully")
                    except Exception as e:
                        logging.error(f"Failed to read from camera {name}: {e}")
                        # If we can't read from the camera, try to reconnect
                        camera.disconnect()
                        time.sleep(1)
                        camera.connect()
            except Exception as e:
                logging.error(f"Error initializing camera {name}: {e}")
                should_stop = True
                break



    timestamp = 0
    start_episode_t = time.perf_counter()
    last_check_time = start_episode_t
    check_interval = 1.0  # Check connection every second
    
    logging.info(f"Starting control loop with control_time_s={control_time_s}")
    try:
        while timestamp < control_time_s and not should_stop:
            start_loop_t = time.perf_counter()
            
            # Check connections periodically
            current_time = time.perf_counter()
            if current_time - last_check_time > check_interval:
                if not robot.is_connected:
                    logging.error("Robot connection lost")
                    should_stop = True
                    break
                if hasattr(robot, 'cameras'):
                    for name, camera in robot.cameras.items():
                        if not camera.is_connected:
                            logging.error(f"Camera {name} connection lost")
                            should_stop = True
                            break
                last_check_time = current_time
            
            try:
                if should_stop:
                    break

                if teleoperate:
                    logging.debug("Performing teleop step...")
                    try:
                        observation, action = robot.teleop_step(record_data=True)
                        # Ensure action is a dictionary
                        if isinstance(action, str):
                            action = {"action": action}
                    except Exception as e:
                        logging.error(f"Error in teleop_step: {e}")
                        should_stop = True
                        break
                else:
                    logging.debug("Capturing observation...")
                    # Try to get observation with a timeout
                    max_retries = 3
                    retry_count = 0
                    while retry_count < max_retries and not should_stop:
                        try:
                            observation = robot.capture_observation()
                            break
                        except Exception as e:
                            retry_count += 1
                            if retry_count == max_retries:
                                logging.error(f"Failed to capture observation after {max_retries} retries: {e}")
                                should_stop = True
                                break
                            logging.warning(f"Failed to capture observation, retrying ({retry_count}/{max_retries}): {e}")
                            time.sleep(0.1)

                    if should_stop:
                        break

                    if policy is not None:
                        logging.debug("Computing policy action...")
                        try:
                            pred_action = predict_action(observation, policy, device, use_amp)
                            action = robot.send_action(pred_action)
                            action = {"action": action}
                        except Exception as e:
                            logging.error(f"Error in policy action: {e}")
                            should_stop = True
                            break
                    else:
                        action = {"action": None}

                if should_stop:
                    break

                if dataset is not None and not should_stop:
                    logging.debug("Adding frame to dataset...")
                    frame = {**observation, **action}
                    dataset.add_frame(frame)

                if display_cameras and not is_headless() and not should_stop:
                    logging.debug("Displaying camera images...")
                    image_keys = [key for key in observation if "image" in key]
                    for key in image_keys:
                        try:
                            cv2.imshow(key, cv2.cvtColor(observation[key], cv2.COLOR_RGB2BGR))
                        except Exception as e:
                            logging.error(f"Error displaying camera {key}: {e}")
                    cv2.waitKey(1)

                if fps is not None and not should_stop:
                    dt_s = time.perf_counter() - start_loop_t
                    busy_wait(1 / fps - dt_s)

                dt_s = time.perf_counter() - start_loop_t
                log_control_info(robot, dt_s, fps=fps)

                timestamp = time.perf_counter() - start_episode_t
                if events["exit_early"] or should_stop:
                    events["exit_early"] = False
                    break
                    
            except Exception as e:
                logging.error(f"Error in control loop: {e}")
                logging.error(traceback.format_exc())
                # Add a small delay to prevent rapid error logging
                time.sleep(0.1)
                if should_stop:
                    break
    finally:
        # Clean up keyboard listener
        if listener is not None:
            listener.stop()
        # Clean up camera displays
        if display_cameras and not is_headless():
            cv2.destroyAllWindows()
        # Disconnect robot
        if robot.is_connected:
            robot.disconnect()
    # Check robot connection
    if not robot.is_connected:
        logging.error("Robot is not connected")
        should_stop = True
        return

def reset_environment(robot, events, reset_time_s):
    # TODO(rcadene): refactor warmup_record and reset_environment
    # TODO(alibets): allow for teleop during reset
    if has_method(robot, "teleop_safety_stop"):
        robot.teleop_safety_stop()

    timestamp = 0
    start_vencod_t = time.perf_counter()

    # Wait if necessary
    with tqdm.tqdm(total=reset_time_s, desc="Waiting") as pbar:
        while timestamp < reset_time_s:
            time.sleep(1)
            timestamp = time.perf_counter() - start_vencod_t
            pbar.update(1)
            if events["exit_early"]:
                events["exit_early"] = False
                break


def stop_recording(robot, listener, display_cameras):
    robot.disconnect()

    if not is_headless():
        if listener is not None:
            listener.stop()

        if display_cameras:
            cv2.destroyAllWindows()


def sanity_check_dataset_name(repo_id, policy_cfg):
    _, dataset_name = repo_id.split("/")
    # either repo_id doesnt start with "eval_" and there is no policy
    # or repo_id starts with "eval_" and there is a policy

    # Check if dataset_name starts with "eval_" but policy is missing
    if dataset_name.startswith("eval_") and policy_cfg is None:
        raise ValueError(
            f"Your dataset name begins with 'eval_' ({dataset_name}), but no policy is provided ({policy_cfg.type})."
        )

    # Check if dataset_name does not start with "eval_" but policy is provided
    if not dataset_name.startswith("eval_") and policy_cfg is not None:
        raise ValueError(
            f"Your dataset name does not begin with 'eval_' ({dataset_name}), but a policy is provided ({policy_cfg.type})."
        )


def sanity_check_dataset_robot_compatibility(
    dataset: LeRobotDataset, robot: Robot, fps: int, use_videos: bool
) -> None:
    fields = [
        ("robot_type", dataset.meta.robot_type, robot.robot_type),
        ("fps", dataset.fps, fps),
        ("features", dataset.features, get_features_from_robot(robot, use_videos)),
    ]

    mismatches = []
    for field, dataset_value, present_value in fields:
        diff = DeepDiff(dataset_value, present_value, exclude_regex_paths=[r".*\['info'\]$"])
        if diff:
            mismatches.append(f"{field}: expected {present_value}, got {dataset_value}")

    if mismatches:
        raise ValueError(
            "Dataset metadata compatibility check failed with mismatches:\n" + "\n".join(mismatches)
        )
