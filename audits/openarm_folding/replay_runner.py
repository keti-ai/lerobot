#!/usr/bin/env python
"""Safe physical replay for the OpenArm handover clean dataset.

This wrapper is intentionally narrower than ``lerobot-replay``:
- it reuses the K4-tested bimanual OpenArm follower configuration,
- it requires a positive max_relative_target cap, and
- it verifies dataset action order before any motion.

Physical replay still requires an on-site operator with power abort / E-stop.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import subprocess
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from pprint import pformat
from typing import Any

from lerobot.cameras.realsense import RealSenseCameraConfig
from lerobot.datasets import LeRobotDataset
from lerobot.processor import make_default_robot_action_processor
from lerobot.robots import (  # noqa: F401
    bi_openarm_follower,
    make_robot_from_config,
    openarm_follower,
)
from lerobot.robots.bi_openarm_follower.config_bi_openarm_follower import BiOpenArmFollowerConfig
from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase
from lerobot.utils.constants import ACTION
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.robot_utils import precise_sleep
from lerobot.utils.utils import init_logging, log_say

DATASET_REPO_ID = "KETI-IRRC/openarm_handover_v0_20260521_202117_clean"
LOG_DIR = Path("/home/syhlabtop/k4_logs")

ARM_MOTORS = tuple(f"joint_{idx}" for idx in range(1, 8))
ALL_MOTORS = (*ARM_MOTORS, "gripper")
EXPECTED_ACTION_NAMES = tuple(
    [f"right_joint_{idx}.pos" for idx in range(1, 8)]
    + ["right_gripper.pos"]
    + [f"left_joint_{idx}.pos" for idx in range(1, 8)]
    + ["left_gripper.pos"]
)


class ClampCounterHandler(logging.Handler):
    """Counts OpenArm max_relative_target clamp warnings without changing behavior."""

    _joint_re = re.compile(r"'([^']+)': \{")

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.events = 0
        self.joint_counts: Counter[str] = Counter()

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "Relative goal position magnitude had to be clamped to be safe" not in message:
            return
        self.events += 1
        for joint in self._joint_re.findall(message):
            self.joint_counts[joint] += 1


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("cap values must be positive; cap=None/0 is refused")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe OpenArm dataset action replay with capped steps.")
    parser.add_argument("--episode", type=int, default=0, help="Dataset episode to replay.")
    parser.add_argument("--fps", type=float, default=None, help="Replay FPS. Defaults to dataset fps.")
    parser.add_argument("--max-arm-cap", type=positive_float, default=15.0, help="Arm per-step cap in degrees.")
    parser.add_argument("--max-grip-cap", type=positive_float, default=65.0, help="Gripper per-step cap in degrees.")
    parser.add_argument("--dry-run", action="store_true", help="Load dataset and verify mappings; do not connect.")
    parser.add_argument(
        "--gripper-trace",
        type=Path,
        default=None,
        help="Optional CSV path for per-frame gripper command/sent/readback trace.",
    )
    parser.add_argument(
        "--gripper-probe",
        action="store_true",
        help="Hold the arms at the current pose and probe gripper close/open instead of replaying the dataset.",
    )
    parser.add_argument(
        "--action-only",
        action="store_true",
        help="Replay dataset actions without per-frame robot.get_observation(); trace reads only gripper motors.",
    )
    parser.add_argument(
        "--prealign-start-s",
        type=nonnegative_float,
        default=0.0,
        help="Before replay, hold dataset frame-0 action for this many seconds to align the start pose.",
    )
    parser.add_argument(
        "--probe-values",
        default="-20,-45,0",
        help="Comma-separated gripper targets for --gripper-probe, in degrees.",
    )
    parser.add_argument(
        "--probe-hold-s",
        type=positive_float,
        default=1.0,
        help="Seconds to hold each gripper probe target.",
    )
    parser.add_argument("--play-sounds", action="store_true", help="Use system speech for start messages.")
    return parser.parse_args()


def build_max_relative_target(max_arm_cap: float, max_grip_cap: float) -> dict[str, float]:
    return {
        **{motor_name: max_arm_cap for motor_name in ARM_MOTORS},
        "gripper": max_grip_cap,
    }


def build_robot_config(
    max_relative_target: dict[str, float],
    *,
    include_cameras: bool,
) -> BiOpenArmFollowerConfig:
    if not max_relative_target:
        raise ValueError("max_relative_target is required for physical replay safety")

    return BiOpenArmFollowerConfig(
        id="openarm_bimanual_follower",
        left_arm_config=OpenArmFollowerConfigBase(
            port="can0",
            side="left",
            max_relative_target=max_relative_target,
        ),
        right_arm_config=OpenArmFollowerConfigBase(
            port="can1",
            side="right",
            max_relative_target=max_relative_target,
        ),
        cameras=build_camera_configs() if include_cameras else {},
    )


def build_camera_configs() -> dict[str, RealSenseCameraConfig]:
    return {
        "left_wrist": RealSenseCameraConfig(
            serial_number_or_name="315122270766",
            width=640,
            height=480,
            fps=30,
            warmup_s=3,
        ),
        "right_wrist": RealSenseCameraConfig(
            serial_number_or_name="230322273311",
            width=640,
            height=480,
            fps=30,
            warmup_s=3,
        ),
        "base": RealSenseCameraConfig(
            serial_number_or_name="213622075840",
            width=640,
            height=480,
            fps=30,
            warmup_s=3,
        ),
    }


def get_action_names(dataset: LeRobotDataset) -> tuple[str, ...]:
    action_feature = dataset.features.get(ACTION)
    if not isinstance(action_feature, dict) or "names" not in action_feature:
        raise ValueError(f"Dataset action feature does not expose names: {action_feature!r}")
    return tuple(action_feature["names"])


def verify_action_mapping(dataset_action_names: tuple[str, ...], robot_action_names: tuple[str, ...]) -> None:
    problems: list[str] = []
    if dataset_action_names != EXPECTED_ACTION_NAMES:
        problems.append(
            "dataset action names do not match expected OpenArm order:\n"
            f"expected={EXPECTED_ACTION_NAMES}\nactual={dataset_action_names}"
        )
    if robot_action_names != EXPECTED_ACTION_NAMES:
        problems.append(
            "robot action names do not match expected OpenArm order:\n"
            f"expected={EXPECTED_ACTION_NAMES}\nactual={robot_action_names}"
        )
    if dataset_action_names != robot_action_names:
        problems.append(
            "dataset and robot action names differ:\n"
            f"dataset={dataset_action_names}\nrobot={robot_action_names}"
        )
    if problems:
        raise ValueError("\n\n".join(problems))


def countdown(play_sounds: bool) -> None:
    log_say(
        "Operator must be present with power abort ready. Replay starts after countdown.",
        play_sounds,
        blocking=False,
    )
    logging.warning("Physical replay starts in 3 seconds. First frames may ramp toward dataset start pose.")
    for remaining in (3, 2, 1):
        logging.warning("Starting in %s...", remaining)
        time.sleep(1.0)


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")


def scalar(value: Any) -> float:
    if hasattr(value, "item"):
        return float(value.item())
    return float(value)


def parse_probe_values(values: str) -> list[float]:
    parsed = [float(value.strip()) for value in values.split(",") if value.strip()]
    if not parsed:
        raise ValueError("--probe-values must contain at least one numeric target")
    for value in parsed:
        if not -65.0 <= value <= 0.0:
            raise ValueError(f"gripper probe value must be in [-65, 0], got {value}")
    return parsed


def log_can_state(context: str) -> None:
    for interface in ("can0", "can1"):
        result = subprocess.run(
            ["ip", "-br", "link", "show", interface],
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip() or result.stderr.strip()
        logging.info("%s CAN state %s: %s", context, interface, output or f"missing rc={result.returncode}")


def safe_disconnect(robot: Any) -> str | None:
    try:
        robot.disconnect()
        return None
    except Exception as exc:
        logging.exception("robot.disconnect() failed; attempting CAN bus cleanup.")
        for arm_name in ("left_arm", "right_arm"):
            arm = getattr(robot, arm_name, None)
            bus = getattr(arm, "bus", None)
            if bus is None or not getattr(bus, "is_connected", False):
                continue
            try:
                bus.disconnect(getattr(arm.config, "disable_torque_on_disconnect", True))
            except Exception:
                logging.exception("Failed to disconnect %s bus during cleanup.", arm_name)
        return repr(exc)


def make_trace_writer(path: Path) -> tuple[Any, csv.DictWriter]:
    path.parent.mkdir(parents=True, exist_ok=True)
    trace_file = path.open("w", newline="", encoding="utf-8")
    trace_writer = csv.DictWriter(
        trace_file,
        fieldnames=[
            "frame",
            "phase",
            "right_cmd",
            "right_processed",
            "right_sent",
            "right_readback_before",
            "right_readback_after",
            "left_cmd",
            "left_processed",
            "left_sent",
            "left_readback_before",
            "left_readback_after",
        ],
    )
    trace_writer.writeheader()
    return trace_file, trace_writer


def read_gripper_positions(robot: Any) -> dict[str, float | None]:
    try:
        right_pos = robot.right_arm.bus.sync_read("Present_Position").get("gripper")
        left_pos = robot.left_arm.bus.sync_read("Present_Position").get("gripper")
        return {
            "right_gripper.pos": right_pos,
            "left_gripper.pos": left_pos,
        }
    except Exception:
        logging.exception("Failed to read gripper positions.")
        return {
            "right_gripper.pos": None,
            "left_gripper.pos": None,
        }


def read_motor_positions(robot: Any) -> dict[str, float]:
    positions: dict[str, float] = {}
    for prefix, arm in (("right", robot.right_arm), ("left", robot.left_arm)):
        try:
            arm_positions = arm.bus.sync_read("Present_Position")
        except Exception:
            logging.exception("Failed to read %s arm motor positions.", prefix)
            continue
        for motor_name, position in arm_positions.items():
            positions[f"{prefix}_{motor_name}.pos"] = scalar(position)
    return positions


def action_from_array(action_array: Any, action_names: tuple[str, ...]) -> dict[str, Any]:
    return {name: action_array[i] for i, name in enumerate(action_names)}


def summarize_start_error(target_action: dict[str, Any], current_positions: dict[str, float]) -> dict[str, Any]:
    errors: dict[str, float] = {}
    missing: list[str] = []
    for name in EXPECTED_ACTION_NAMES:
        if name not in current_positions:
            missing.append(name)
            continue
        errors[name] = scalar(target_action[name]) - current_positions[name]

    arm_abs = [abs(error) for name, error in errors.items() if "gripper" not in name]
    gripper_abs = [abs(error) for name, error in errors.items() if "gripper" in name]
    top_errors = sorted(
        ({"name": name, "error_deg": error, "abs_error_deg": abs(error)} for name, error in errors.items()),
        key=lambda item: item["abs_error_deg"],
        reverse=True,
    )[:6]

    return {
        "max_arm_abs_deg": max(arm_abs) if arm_abs else None,
        "mean_arm_abs_deg": sum(arm_abs) / len(arm_abs) if arm_abs else None,
        "max_gripper_abs_deg": max(gripper_abs) if gripper_abs else None,
        "top_errors": top_errors,
        "missing": missing,
    }


def write_gripper_trace_row(
    trace_writer: csv.DictWriter | None,
    *,
    frame: int,
    phase: str,
    action: dict[str, Any],
    processed_action: dict[str, Any],
    sent_action: dict[str, Any],
    readback_before: dict[str, Any],
    readback_after: dict[str, Any],
) -> None:
    if trace_writer is None:
        return

    def maybe_scalar(mapping: dict[str, Any], key: str) -> float | None:
        value = mapping.get(key)
        return None if value is None else scalar(value)

    trace_writer.writerow(
        {
            "frame": frame,
            "phase": phase,
            "right_cmd": scalar(action["right_gripper.pos"]),
            "right_processed": scalar(processed_action["right_gripper.pos"]),
            "right_sent": scalar(sent_action["right_gripper.pos"]),
            "right_readback_before": maybe_scalar(readback_before, "right_gripper.pos"),
            "right_readback_after": maybe_scalar(readback_after, "right_gripper.pos"),
            "left_cmd": scalar(action["left_gripper.pos"]),
            "left_processed": scalar(processed_action["left_gripper.pos"]),
            "left_sent": scalar(sent_action["left_gripper.pos"]),
            "left_readback_before": maybe_scalar(readback_before, "left_gripper.pos"),
            "left_readback_after": maybe_scalar(readback_after, "left_gripper.pos"),
        }
    )


def run_start_prealign(
    *,
    robot: Any,
    robot_action_processor: Any,
    first_action: dict[str, Any],
    trace_writer: csv.DictWriter | None,
    hold_s: float,
    fps: float,
) -> int:
    prealign_frames = max(1, int(round(hold_s * fps)))
    logging.warning(
        "Pre-aligning to dataset frame-0 action for %.2fs (%d frames).",
        hold_s,
        prealign_frames,
    )
    for frame_idx in range(prealign_frames):
        start_frame_t = time.perf_counter()
        readback_before = read_gripper_positions(robot) if trace_writer is not None else {}
        processed_action = robot_action_processor((first_action, {}))
        sent_action = robot.send_action(processed_action)
        readback_after = read_gripper_positions(robot) if trace_writer is not None else {}
        write_gripper_trace_row(
            trace_writer,
            frame=frame_idx - prealign_frames,
            phase="prealign",
            action=first_action,
            processed_action=processed_action,
            sent_action=sent_action,
            readback_before=readback_before,
            readback_after=readback_after,
        )
        elapsed = time.perf_counter() - start_frame_t
        precise_sleep(max(1.0 / fps - elapsed, 0.0))
    return prealign_frames


def run_gripper_probe(
    *,
    robot: Any,
    robot_action_processor: Any,
    trace_writer: csv.DictWriter | None,
    probe_values: list[float],
    hold_s: float,
    fps: float,
) -> int:
    sent_frames = 0
    hold_frames = max(1, int(round(hold_s * fps)))
    logging.warning(
        "Running gripper-only probe at current arm pose. Targets=%s hold_s=%.2f fps=%.1f",
        probe_values,
        hold_s,
        fps,
    )

    for target in probe_values:
        logging.warning("Gripper probe target %.1f deg", target)
        for _ in range(hold_frames):
            start_frame_t = time.perf_counter()
            robot_obs = robot.get_observation()
            action = {name: robot_obs[name] for name in EXPECTED_ACTION_NAMES}
            action["right_gripper.pos"] = target
            action["left_gripper.pos"] = target
            processed_action = robot_action_processor((action, robot_obs))
            sent_action = robot.send_action(processed_action)
            readback_after = robot.get_observation()
            write_gripper_trace_row(
                trace_writer,
                frame=sent_frames,
                phase=f"probe_{target:.1f}",
                action=action,
                processed_action=processed_action,
                sent_action=sent_action,
                readback_before=robot_obs,
                readback_after=readback_after,
            )
            sent_frames += 1
            elapsed = time.perf_counter() - start_frame_t
            precise_sleep(max(1.0 / fps - elapsed, 0.0))

    return sent_frames


def replay(args: argparse.Namespace) -> None:
    init_logging()
    logging.info("Safe replay args:\n%s", pformat(vars(args)))

    max_relative_target = build_max_relative_target(args.max_arm_cap, args.max_grip_cap)
    include_cameras = not (args.action_only or args.gripper_probe)
    robot_config = build_robot_config(max_relative_target, include_cameras=include_cameras)
    logging.info("Robot config max_relative_target: %s", max_relative_target)
    logging.info("Robot config include_cameras: %s", include_cameras)

    dataset = LeRobotDataset(DATASET_REPO_ID, episodes=[args.episode])
    actions = dataset.select_columns(ACTION)
    dataset_action_names = get_action_names(dataset)

    robot = make_robot_from_config(robot_config)
    robot_action_names = tuple(robot.action_features)
    verify_action_mapping(dataset_action_names, robot_action_names)

    replay_fps = args.fps if args.fps is not None else float(dataset.fps)
    if replay_fps <= 0:
        raise ValueError(f"Replay FPS must be positive, got {replay_fps}")

    mapping_info = {
        "dataset_repo_id": DATASET_REPO_ID,
        "episode": args.episode,
        "num_frames": dataset.num_frames,
        "dataset_fps": dataset.fps,
        "replay_fps": replay_fps,
        "action_names": dataset_action_names,
        "max_relative_target": max_relative_target,
        "include_cameras": include_cameras,
        "robot_config": asdict(robot_config),
    }
    logging.info("Mapping verified:\n%s", pformat(mapping_info))

    if args.dry_run:
        write_summary(LOG_DIR / f"replay_dry_episode_{args.episode}.json", mapping_info)
        logging.info("Dry-run complete; no robot connection or motion was attempted.")
        return

    clamp_counter = ClampCounterHandler()
    logging.getLogger().addHandler(clamp_counter)
    robot_action_processor = make_default_robot_action_processor()
    sent_frames = 0
    started_at = time.time()
    control_started_at: float | None = None
    control_elapsed_s: float | None = None
    probe_values = parse_probe_values(args.probe_values) if args.gripper_probe else []
    gripper_trace = args.gripper_trace
    if args.gripper_probe and gripper_trace is None:
        gripper_trace = LOG_DIR / f"lr_gripper_probe_episode_{args.episode}.csv"
        logging.info("Gripper probe trace path defaulted to %s", gripper_trace)

    trace_file = None
    trace_writer = None
    if gripper_trace is not None:
        trace_file, trace_writer = make_trace_writer(gripper_trace)

    log_can_state("pre-connect")
    robot.connect()
    start_error_before: dict[str, Any] | None = None
    start_error_after: dict[str, Any] | None = None
    prealign_frames = 0
    disconnect_error = None
    try:
        countdown(args.play_sounds)
        first_action = action_from_array(actions[0][ACTION], dataset_action_names)
        if not args.gripper_probe:
            start_error_before = summarize_start_error(first_action, read_motor_positions(robot))
            logging.info("Start error before pre-align:\n%s", pformat(start_error_before))
            if args.prealign_start_s > 0:
                prealign_frames = run_start_prealign(
                    robot=robot,
                    robot_action_processor=robot_action_processor,
                    first_action=first_action,
                    trace_writer=trace_writer,
                    hold_s=args.prealign_start_s,
                    fps=replay_fps,
                )
                start_error_after = summarize_start_error(first_action, read_motor_positions(robot))
                logging.info("Start error after pre-align:\n%s", pformat(start_error_after))

        if args.gripper_probe:
            log_say("Running gripper probe", args.play_sounds, blocking=False)
            control_started_at = time.perf_counter()
            sent_frames = run_gripper_probe(
                robot=robot,
                robot_action_processor=robot_action_processor,
                trace_writer=trace_writer,
                probe_values=probe_values,
                hold_s=args.probe_hold_s,
                fps=replay_fps,
            )
            control_elapsed_s = time.perf_counter() - control_started_at
        else:
            log_say("Replaying clean dataset episode", args.play_sounds, blocking=False)
            control_started_at = time.perf_counter()
            for idx in range(dataset.num_frames):
                start_frame_t = time.perf_counter()

                action_array = actions[idx][ACTION]
                action = action_from_array(action_array, dataset_action_names)
                if args.action_only:
                    robot_obs = {}
                    readback_before = read_gripper_positions(robot) if trace_writer is not None else {}
                else:
                    robot_obs = robot.get_observation()
                    readback_before = robot_obs
                processed_action = robot_action_processor((action, robot_obs))
                sent_action = robot.send_action(processed_action)
                if trace_writer is not None:
                    readback_after = (
                        read_gripper_positions(robot) if args.action_only else robot.get_observation()
                    )
                    write_gripper_trace_row(
                        trace_writer,
                        frame=idx,
                        phase="replay",
                        action=action,
                        processed_action=processed_action,
                        sent_action=sent_action,
                        readback_before=readback_before,
                        readback_after=readback_after,
                    )
                sent_frames += 1

                elapsed = time.perf_counter() - start_frame_t
                precise_sleep(max(1.0 / replay_fps - elapsed, 0.0))
            control_elapsed_s = time.perf_counter() - control_started_at
    finally:
        if trace_file is not None:
            trace_file.close()
        disconnect_error = safe_disconnect(robot)
        log_can_state("post-disconnect")
        logging.getLogger().removeHandler(clamp_counter)

        summary = {
            **mapping_info,
            "sent_frames": sent_frames,
            "elapsed_s": time.time() - started_at,
            "control_elapsed_s": control_elapsed_s,
            "effective_control_fps": (sent_frames / control_elapsed_s)
            if control_elapsed_s and control_elapsed_s > 0
            else None,
            "prealign_start_s": args.prealign_start_s,
            "prealign_frames": prealign_frames,
            "start_error_before": start_error_before,
            "start_error_after": start_error_after,
            "disconnect_error": disconnect_error,
            "clamp_events": clamp_counter.events,
            "clamp_joint_counts": dict(sorted(clamp_counter.joint_counts.items())),
            "gripper_trace": str(gripper_trace) if gripper_trace is not None else None,
            "gripper_probe": args.gripper_probe,
            "action_only": args.action_only,
        }
        write_summary(LOG_DIR / f"replay_summary_episode_{args.episode}.json", summary)
        logging.info("Replay summary:\n%s", pformat(summary))


def main() -> None:
    register_third_party_plugins()
    replay(parse_args())


if __name__ == "__main__":
    main()
