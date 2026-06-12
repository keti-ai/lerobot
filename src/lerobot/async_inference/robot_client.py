# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example command:
```shell
python src/lerobot/async_inference/robot_client.py \
    --robot.type=so100_follower \
    --robot.port=/dev/tty.usbmodem58760431541 \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 1920, height: 1080, fps: 30}}" \
    --robot.id=black \
    --task="dummy" \
    --server_address=127.0.0.1:8080 \
    --policy_type=act \
    --pretrained_name_or_path=user/model \
    --policy_device=mps \
    --client_device=cpu \
    --actions_per_chunk=50 \
    --chunk_size_threshold=0.5 \
    --aggregate_fn_name=weighted_average \
    --debug_visualize_queue_size=True
```
"""

import csv
import logging
import pickle  # nosec
import threading
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from pprint import pformat
from queue import Queue
from typing import Any

import draccus
import grpc
import torch

from lerobot.cameras.opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.cameras.realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    bi_so_follower,
    koch_follower,
    make_robot_from_config,
    omx_follower,
    so_follower,
)
from lerobot.transport import (
    services_pb2,  # type: ignore
    services_pb2_grpc,  # type: ignore
)
from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks
from lerobot.utils.action_interpolator import ActionInterpolator
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.joint_trajectory import JointProfileLimits, OnlineTrajectoryGenerator
from lerobot.utils.robot_utils import precise_sleep

from .configs import RobotClientConfig
from .helpers import (
    Action,
    FPSTracker,
    Observation,
    RawObservation,
    RemotePolicyConfig,
    TimedAction,
    TimedObservation,
    get_logger,
    map_robot_keys_to_lerobot_features,
    visualize_action_queue_size,
)


class LatencyBreakdownRecorder:
    fieldnames = [
        "step",
        "obs_capture_ms",
        "send_ms",
        "obs_serialize_ms",
        "obs_grpc_ms",
        "server_rtt_ms",
        "deserialize_ms",
        "queue_update_ms",
        "total_ms",
    ]

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._rows: dict[int, dict[str, Any]] = {}
        self._write_csv()

    def record_observation(
        self,
        *,
        step: int,
        obs_capture_ms: float,
        send_ms: float,
        obs_serialize_ms: float,
        obs_grpc_ms: float,
    ) -> None:
        self._update(
            step,
            obs_capture_ms=obs_capture_ms,
            send_ms=send_ms,
            obs_serialize_ms=obs_serialize_ms,
            obs_grpc_ms=obs_grpc_ms,
        )

    def record_chunk_receive(
        self,
        *,
        step: int,
        action_timestamp: float,
        receive_time: float,
        deserialize_ms: float,
        queue_update_ms: float,
    ) -> None:
        self._update(
            step,
            server_rtt_ms=(receive_time - action_timestamp) * 1000,
            deserialize_ms=deserialize_ms,
            queue_update_ms=queue_update_ms,
        )

    def record_action_apply(self, *, step: int, action_timestamp: float) -> None:
        self._update(step, total_ms=(time.time() - action_timestamp) * 1000)

    def _update(self, step: int, **values: float) -> None:
        with self._lock:
            row = self._rows.setdefault(step, {"step": step})
            row.update(values)
            self._write_csv_locked()

    def _write_csv(self) -> None:
        with self._lock:
            self._write_csv_locked()

    def _write_csv_locked(self) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.fieldnames)
            writer.writeheader()
            for step in sorted(self._rows):
                writer.writerow({field: self._rows[step].get(field, "") for field in self.fieldnames})


class RobotClient:
    prefix = "robot_client"
    logger = get_logger(prefix)

    def __init__(self, config: RobotClientConfig):
        """Initialize RobotClient with unified configuration.

        Args:
            config: RobotClientConfig containing all configuration parameters
        """
        # Store configuration
        self.config = config
        self.robot = make_robot_from_config(config.robot)
        self.robot.connect()

        lerobot_features = map_robot_keys_to_lerobot_features(self.robot)

        # Use environment variable if server_address is not provided in config
        self.server_address = config.server_address

        self.policy_config = RemotePolicyConfig(
            config.policy_type,
            config.pretrained_name_or_path,
            lerobot_features,
            config.actions_per_chunk,
            config.policy_device,
        )
        self.channel = grpc.insecure_channel(
            self.server_address, grpc_channel_options(initial_backoff=f"{config.environment_dt:.4f}s")
        )
        self.stub = services_pb2_grpc.AsyncInferenceStub(self.channel)
        self.logger.info(f"Initializing client to connect to server at {self.server_address}")

        self.shutdown_event = threading.Event()

        # Initialize client side variables
        self.latest_action_lock = threading.Lock()
        self.latest_action = -1
        self.action_chunk_size = -1

        self._chunk_size_threshold = config.chunk_size_threshold

        self.action_queue = Queue()
        self.action_queue_lock = threading.Lock()  # Protect queue operations
        self.action_queue_size = []
        self.start_barrier = threading.Barrier(2)  # 2 threads: action receiver, control loop
        self.interpolator = ActionInterpolator(config.action_interpolation_multiplier)

        # High-rate trajectory streamer: a dedicated thread tracks the latest VLA setpoint
        # with a velocity/acceleration-limited profile and streams motor commands at
        # config.trajectory_streamer_hz, decoupled from the (camera-bound) control loop.
        self.trajectory_streamer_enabled = config.trajectory_streamer_hz > 0
        self._traj_target_lock = threading.Lock()
        self._traj_target: torch.Tensor | None = None
        self._traj_thread: threading.Thread | None = None
        self._traj_generator: OnlineTrajectoryGenerator | None = None
        if self.trajectory_streamer_enabled:
            self._traj_generator = OnlineTrajectoryGenerator(
                names=list(self.robot.action_features),
                limits=self._build_trajectory_limits(config),
                profile=config.trajectory_profile,
            )
            self.logger.info(
                f"Trajectory streamer enabled: {config.trajectory_streamer_hz} Hz, "
                f"profile={config.trajectory_profile}"
            )
        self.latency_breakdown = (
            LatencyBreakdownRecorder(config.latency_breakdown_csv)
            if config.latency_breakdown_csv
            else None
        )

        # FPS measurement
        self.fps_tracker = FPSTracker(target_fps=self.config.fps)

        self.logger.info("Robot connected and ready")

        # Use an event for thread-safe coordination
        self.must_go = threading.Event()
        self.must_go.set()  # Initially set - observations qualify for direct processing

    @property
    def running(self):
        return not self.shutdown_event.is_set()

    def start(self):
        """Start the robot client and connect to the policy server"""
        try:
            # client-server handshake
            start_time = time.perf_counter()
            self.stub.Ready(services_pb2.Empty())
            end_time = time.perf_counter()
            self.logger.debug(f"Connected to policy server in {end_time - start_time:.4f}s")

            # send policy instructions
            policy_config_bytes = pickle.dumps(self.policy_config)
            policy_setup = services_pb2.PolicySetup(data=policy_config_bytes)

            self.logger.info("Sending policy instructions to policy server")
            self.logger.debug(
                f"Policy type: {self.policy_config.policy_type} | "
                f"Pretrained name or path: {self.policy_config.pretrained_name_or_path} | "
                f"Device: {self.policy_config.device}"
            )

            self.stub.SendPolicyInstructions(policy_setup)

            self.shutdown_event.clear()
            self.interpolator.reset()

            if self.trajectory_streamer_enabled:
                self._traj_thread = threading.Thread(
                    target=self._trajectory_streamer_loop, daemon=True, name="trajectory_streamer"
                )
                self._traj_thread.start()

            return True

        except grpc.RpcError as e:
            self.logger.error(f"Failed to connect to policy server: {e}")
            return False

    def stop(self):
        """Stop the robot client"""
        self.shutdown_event.set()

        if self._traj_thread is not None:
            self._traj_thread.join(timeout=2.0)
            self._traj_thread = None

        self.robot.disconnect()
        self.logger.debug("Robot disconnected")

        self.interpolator.reset()

        self.channel.close()
        self.logger.debug("Client stopped, channel closed")

    @staticmethod
    def _build_trajectory_limits(config: RobotClientConfig) -> dict[str, JointProfileLimits]:
        """Build per-joint profile limits: defaults + per-motor-suffix overrides from config."""
        default = JointProfileLimits(
            v_max=config.trajectory_v_max_deg_s,
            a_max=config.trajectory_a_max_deg_s2,
            j_max=config.trajectory_j_max_deg_s3,
        )
        limits: dict[str, JointProfileLimits] = {"default": default}
        for key, override in (config.trajectory_limits_overrides or {}).items():
            limits[key] = JointProfileLimits(
                v_max=override.get("v_max", default.v_max),
                a_max=override.get("a_max", default.a_max),
                j_max=override.get("j_max", default.j_max),
            )
        return limits

    def _read_present_positions(self) -> list[float] | None:
        """Read current joint positions ordered like robot.action_features (one-shot, for init)."""
        try:
            observation = self.robot.get_observation()
        except Exception:
            self.logger.exception("Trajectory streamer: failed to read initial robot positions")
            return None
        positions = []
        for key in self.robot.action_features:
            if key not in observation:
                self.logger.warning(f"Trajectory streamer: '{key}' missing from observation")
                return None
            positions.append(float(observation[key]))
        return positions

    def _trajectory_streamer_loop(self):
        """Stream velocity/acceleration-limited joint commands at trajectory_streamer_hz.

        The control loop only updates the target setpoint (latest VLA action); this thread
        owns robot.send_action. The profile generator is initialized from the robot's present
        positions so the first commands ramp smoothly from wherever the robot currently is.
        """
        dt = 1.0 / self.config.trajectory_streamer_hz
        generator = self._traj_generator
        action_keys = list(self.robot.action_features)
        consecutive_errors = 0

        self.logger.info(f"Trajectory streamer thread starting ({self.config.trajectory_streamer_hz} Hz)")

        while self.running:
            tick_start = time.perf_counter()

            with self._traj_target_lock:
                target = self._traj_target

            if target is not None:
                try:
                    if not generator.initialized:
                        present = self._read_present_positions()
                        generator.reset(
                            present if present is not None else target.detach().cpu().numpy()
                        )
                    generator.set_target(target.detach().cpu().numpy())
                    command = generator.step(dt)
                    self.robot.send_action(
                        {key: float(command[i]) for i, key in enumerate(action_keys)}
                    )
                    consecutive_errors = 0
                except Exception:
                    consecutive_errors += 1
                    if consecutive_errors <= 3 or consecutive_errors % 100 == 0:
                        self.logger.exception(
                            f"Trajectory streamer: send failed ({consecutive_errors} consecutive)"
                        )

            precise_sleep(max(0.0, dt - (time.perf_counter() - tick_start)))

        self.logger.info("Trajectory streamer thread stopping")

    def send_observation(
        self,
        obs: TimedObservation,
    ) -> bool:
        """Send observation to the policy server.
        Returns True if the observation was sent successfully, False otherwise."""
        if not self.running:
            raise RuntimeError("Client not running. Run RobotClient.start() before sending observations.")

        if not isinstance(obs, TimedObservation):
            raise ValueError("Input observation needs to be a TimedObservation!")

        start_time = time.perf_counter()
        observation_bytes = pickle.dumps(obs)
        serialize_time = time.perf_counter() - start_time
        self.logger.debug(f"Observation serialization time: {serialize_time:.6f}s")

        try:
            grpc_send_start = time.perf_counter()
            observation_iterator = send_bytes_in_chunks(
                observation_bytes,
                services_pb2.Observation,
                log_prefix="[CLIENT] Observation",
                silent=True,
            )
            _ = self.stub.SendObservations(observation_iterator)
            grpc_send_time = time.perf_counter() - grpc_send_start
            obs_timestep = obs.get_timestep()
            self.logger.debug(f"Sent observation #{obs_timestep} | ")
            setattr(
                obs,
                "_client_send_timing",
                {
                    "serialize_ms": serialize_time * 1000,
                    "grpc_ms": grpc_send_time * 1000,
                    "send_ms": (serialize_time + grpc_send_time) * 1000,
                },
            )

            return True

        except grpc.RpcError as e:
            self.logger.error(f"Error sending observation #{obs.get_timestep()}: {e}")
            return False

    def _inspect_action_queue(self):
        with self.action_queue_lock:
            queue_size = self.action_queue.qsize()
            timestamps = sorted([action.get_timestep() for action in self.action_queue.queue])
        self.logger.debug(f"Queue size: {queue_size}, Queue contents: {timestamps}")
        return queue_size, timestamps

    @staticmethod
    def _format_timestep_range(timesteps: list[int]) -> str:
        if not timesteps:
            return "empty"
        return f"{timesteps[0]}:{timesteps[-1]}"

    def _log_action_queue_update(
        self,
        *,
        latest_action: int,
        old_timesteps: list[int],
        incoming_timesteps: list[int],
        new_timesteps: list[int],
        old_size: int,
        new_size: int,
        queue_update_time: float,
    ) -> None:
        try:
            self.logger.info(
                f"Latest action: {latest_action} | "
                f"Old action steps: {self._format_timestep_range(old_timesteps)} | "
                f"Incoming action steps: {self._format_timestep_range(incoming_timesteps)} | "
                f"Updated action steps: {self._format_timestep_range(new_timesteps)}"
            )
            self.logger.debug(
                f"Queue update complete ({queue_update_time:.6f}s) | "
                f"Before: {old_size} items | "
                f"After: {new_size} items | "
            )
            if incoming_timesteps and not new_timesteps and incoming_timesteps[-1] <= latest_action:
                self.logger.debug(
                    "Received fully stale action chunk; all incoming timesteps "
                    f"{self._format_timestep_range(incoming_timesteps)} were already consumed."
                )
        except Exception:
            self.logger.exception("Failed to log action queue update.")

    def _aggregate_action_queues(
        self,
        incoming_actions: list[TimedAction],
        aggregate_fn: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    ):
        """Finds the same timestep actions in the queue and aggregates them using the aggregate_fn"""
        if aggregate_fn is None:
            # default aggregate function: take the latest action
            def aggregate_fn(x1, x2):
                return x2

        future_action_queue = Queue()
        with self.action_queue_lock:
            internal_queue = self.action_queue.queue

        current_action_queue = {action.get_timestep(): action.get_action() for action in internal_queue}

        for new_action in incoming_actions:
            with self.latest_action_lock:
                latest_action = self.latest_action

            # New action is older than the latest action in the queue, skip it
            if new_action.get_timestep() <= latest_action:
                continue

            # If the new action's timestep is not in the current action queue, add it directly
            elif new_action.get_timestep() not in current_action_queue:
                future_action_queue.put(new_action)
                continue

            # If the new action's timestep is in the current action queue, aggregate it
            # TODO: There is probably a way to do this with broadcasting of the two action tensors
            future_action_queue.put(
                TimedAction(
                    timestamp=new_action.get_timestamp(),
                    timestep=new_action.get_timestep(),
                    action=aggregate_fn(
                        current_action_queue[new_action.get_timestep()], new_action.get_action()
                    ),
                )
            )

        with self.action_queue_lock:
            self.action_queue = future_action_queue

    def receive_actions(self, verbose: bool = False):
        """Receive actions from the policy server"""
        # Wait at barrier for synchronized start
        self.start_barrier.wait()
        self.logger.info("Action receiving thread starting")

        while self.running:
            try:
                # Use StreamActions to get a stream of actions from the server
                actions_chunk = self.stub.GetActions(services_pb2.Empty())
                if len(actions_chunk.data) == 0:
                    continue  # received `Empty` from server, wait for next call

                receive_time = time.time()

                # Deserialize bytes back into list[TimedAction]
                deserialize_start = time.perf_counter()
                timed_actions = pickle.loads(actions_chunk.data)  # nosec
                deserialize_time = time.perf_counter() - deserialize_start
                if not timed_actions:
                    self.logger.debug("Received empty action chunk from server.")
                    continue

                # Log device type of received actions
                received_device = timed_actions[0].get_action().device.type
                self.logger.debug(f"Received actions on device: {received_device}")

                # Move actions to client_device (e.g., for downstream planners that need GPU)
                client_device = self.config.client_device
                if client_device != "cpu":
                    for timed_action in timed_actions:
                        if timed_action.get_action().device.type != client_device:
                            timed_action.action = timed_action.get_action().to(client_device)
                    self.logger.debug(f"Converted actions to device: {client_device}")
                else:
                    self.logger.debug(f"Actions kept on device: {client_device}")

                self.action_chunk_size = max(self.action_chunk_size, len(timed_actions))

                # Calculate network latency if we have matching observations
                if verbose:
                    with self.latest_action_lock:
                        latest_action = self.latest_action

                    self.logger.debug(f"Current latest action: {latest_action}")

                    # Get queue state before changes
                    old_size, old_timesteps = self._inspect_action_queue()

                    # Log incoming actions
                    incoming_timesteps = [a.get_timestep() for a in timed_actions]

                    first_action_timestep = timed_actions[0].get_timestep()
                    server_to_client_latency = (receive_time - timed_actions[0].get_timestamp()) * 1000

                    self.logger.info(
                        f"Received action chunk for step #{first_action_timestep} | "
                        f"Latest action: #{latest_action} | "
                        f"Incoming actions: {incoming_timesteps[0]}:{incoming_timesteps[-1]} | "
                        f"Network latency (server->client): {server_to_client_latency:.2f}ms | "
                        f"Deserialization time: {deserialize_time * 1000:.2f}ms"
                    )

                # Update action queue
                start_time = time.perf_counter()
                self._aggregate_action_queues(timed_actions, self.config.aggregate_fn)
                queue_update_time = time.perf_counter() - start_time
                if self.latency_breakdown is not None:
                    first_action = timed_actions[0]
                    self.latency_breakdown.record_chunk_receive(
                        step=first_action.get_timestep(),
                        action_timestamp=first_action.get_timestamp(),
                        receive_time=receive_time,
                        deserialize_ms=deserialize_time * 1000,
                        queue_update_ms=queue_update_time * 1000,
                    )

                self.must_go.set()  # after receiving actions, next empty queue triggers must-go processing!

                if verbose:
                    # Get queue state after changes
                    new_size, new_timesteps = self._inspect_action_queue()

                    with self.latest_action_lock:
                        latest_action = self.latest_action

                    self._log_action_queue_update(
                        latest_action=latest_action,
                        old_timesteps=old_timesteps,
                        incoming_timesteps=incoming_timesteps,
                        new_timesteps=new_timesteps,
                        old_size=old_size,
                        new_size=new_size,
                        queue_update_time=queue_update_time,
                    )

            except grpc.RpcError as e:
                self.logger.error(f"Error receiving actions: {e}")

    def actions_available(self):
        """Check if there are actions available in the queue"""
        if self.interpolator.enabled and not self.interpolator.needs_new_action():
            return True
        with self.action_queue_lock:
            return not self.action_queue.empty()

    def get_control_interval(self) -> float:
        """Return the current control interval, including optional interpolation."""
        return self.interpolator.get_control_interval(self.config.fps)

    def _action_tensor_to_action_dict(self, action_tensor: torch.Tensor) -> dict[str, float]:
        action = {key: action_tensor[i].item() for i, key in enumerate(self.robot.action_features)}
        return action

    def control_loop_action(self, verbose: bool = False) -> dict[str, Any]:
        """Reading and performing actions in local queue"""

        # Trajectory streamer mode: the control loop only refreshes the target setpoint at the
        # action rate (fps); the dedicated streamer thread sends profiled motor commands.
        if self.trajectory_streamer_enabled:
            with self.action_queue_lock:
                self.action_queue_size.append(self.action_queue.qsize())
                timed_action = self.action_queue.get_nowait()
            with self._traj_target_lock:
                self._traj_target = timed_action.get_action()
            with self.latest_action_lock:
                self.latest_action = timed_action.get_timestep()
            if self.latency_breakdown is not None:
                self.latency_breakdown.record_action_apply(
                    step=timed_action.get_timestep(),
                    action_timestamp=timed_action.get_timestamp(),
                )
            return None

        # Lock only for queue operations
        get_start = time.perf_counter()
        timed_action = None
        if self.interpolator.enabled:
            if self.interpolator.needs_new_action():
                with self.action_queue_lock:
                    self.action_queue_size.append(self.action_queue.qsize())
                    # Get action from queue
                    timed_action = self.action_queue.get_nowait()
                self.interpolator.add(timed_action.get_action())
            else:
                with self.action_queue_lock:
                    self.action_queue_size.append(self.action_queue.qsize())

            action_tensor = self.interpolator.get()
            if action_tensor is None:
                raise RuntimeError("Interpolator had no action despite actions_available() being true.")
        else:
            with self.action_queue_lock:
                self.action_queue_size.append(self.action_queue.qsize())
                # Get action from queue
                timed_action = self.action_queue.get_nowait()
            action_tensor = timed_action.get_action()
        get_end = time.perf_counter() - get_start

        _performed_action = self.robot.send_action(self._action_tensor_to_action_dict(action_tensor))
        if timed_action is not None:
            with self.latest_action_lock:
                self.latest_action = timed_action.get_timestep()
            if self.latency_breakdown is not None:
                self.latency_breakdown.record_action_apply(
                    step=timed_action.get_timestep(),
                    action_timestamp=timed_action.get_timestamp(),
                )

        if verbose:
            with self.action_queue_lock:
                current_queue_size = self.action_queue.qsize()

            if timed_action is not None:
                timestamp = timed_action.get_timestamp()
                timestep = timed_action.get_timestep()
            else:
                timestamp = None
                with self.latest_action_lock:
                    timestep = self.latest_action

            self.logger.debug(
                f"Ts={timestamp} | "
                f"Action #{timestep} performed | "
                f"Queue size: {current_queue_size}"
            )

            self.logger.debug(
                f"Popping action from queue to perform took {get_end:.6f}s | Queue size: {current_queue_size}"
            )

        return _performed_action

    def _has_interpolated_action_pending(self) -> bool:
        return self.interpolator.enabled and not self.interpolator.needs_new_action()

    def _ready_to_send_observation(self):
        """Flags when the client is ready to send an observation"""
        with self.action_queue_lock:
            return self.action_queue.qsize() / self.action_chunk_size <= self._chunk_size_threshold

    def control_loop_observation(self, task: str, verbose: bool = False) -> RawObservation:
        try:
            # Get serialized observation bytes from the function
            start_time = time.perf_counter()

            raw_observation: RawObservation = self.robot.get_observation()
            raw_observation["task"] = task

            with self.latest_action_lock:
                latest_action = self.latest_action

            observation = TimedObservation(
                timestamp=time.time(),  # need time.time() to compare timestamps across client and server
                observation=raw_observation,
                timestep=max(latest_action, 0),
            )

            obs_capture_time = time.perf_counter() - start_time

            # If there are no actions left in the queue, the observation must go through processing!
            with self.action_queue_lock:
                observation.must_go = (
                    self.must_go.is_set()
                    and self.action_queue.empty()
                    and not self._has_interpolated_action_pending()
                )
                current_queue_size = self.action_queue.qsize()

            _ = self.send_observation(observation)
            if self.latency_breakdown is not None:
                send_timing = getattr(observation, "_client_send_timing", {})
                self.latency_breakdown.record_observation(
                    step=observation.get_timestep(),
                    obs_capture_ms=obs_capture_time * 1000,
                    send_ms=send_timing.get("send_ms", 0.0),
                    obs_serialize_ms=send_timing.get("serialize_ms", 0.0),
                    obs_grpc_ms=send_timing.get("grpc_ms", 0.0),
                )

            self.logger.debug(f"QUEUE SIZE: {current_queue_size} (Must go: {observation.must_go})")
            if observation.must_go:
                # must-go event will be set again after receiving actions
                self.must_go.clear()

            if verbose:
                # Calculate comprehensive FPS metrics
                fps_metrics = self.fps_tracker.calculate_fps_metrics(observation.get_timestamp())

                self.logger.info(
                    f"Obs #{observation.get_timestep()} | "
                    f"Avg FPS: {fps_metrics['avg_fps']:.2f} | "
                    f"Target: {fps_metrics['target_fps']:.2f}"
                )

                self.logger.debug(
                    f"Ts={observation.get_timestamp():.6f} | Capturing observation took {obs_capture_time:.6f}s"
                )

            return raw_observation

        except Exception as e:
            self.logger.error(f"Error in observation sender: {e}")

    def control_loop(self, task: str, verbose: bool = False) -> tuple[Observation, Action]:
        """Combined function for executing actions and streaming observations"""
        # Wait at barrier for synchronized start
        self.start_barrier.wait()
        self.logger.info("Control loop thread starting")

        _performed_action = None
        _captured_observation = None

        while self.running:
            control_loop_start = time.perf_counter()
            """Control loop: (1) Performing actions, when available"""
            if self.actions_available():
                _performed_action = self.control_loop_action(verbose)

            """Control loop: (2) Streaming observations to the remote policy server"""
            if self._ready_to_send_observation():
                _captured_observation = self.control_loop_observation(task, verbose)

            self.logger.debug(f"Control loop (ms): {(time.perf_counter() - control_loop_start) * 1000:.2f}")
            # Dynamically adjust sleep time to maintain the desired control frequency
            time.sleep(max(0, self.get_control_interval() - (time.perf_counter() - control_loop_start)))

        return _captured_observation, _performed_action


@draccus.wrap()
def async_client(cfg: RobotClientConfig):
    logging.info(pformat(asdict(cfg)))

    # TODO: Assert if checking robot support is still needed with the plugin system
    # if cfg.robot.type not in SUPPORTED_ROBOTS:
    #     raise ValueError(f"Robot {cfg.robot.type} not yet supported!")

    client = RobotClient(cfg)

    if client.start():
        client.logger.info("Starting action receiver thread...")

        # Create and start action receiver thread
        action_receiver_thread = threading.Thread(target=client.receive_actions, daemon=True)

        # Start action receiver thread
        action_receiver_thread.start()

        try:
            # The main thread runs the control loop
            client.control_loop(task=cfg.task)

        finally:
            client.stop()
            action_receiver_thread.join()
            if cfg.debug_visualize_queue_size:
                visualize_action_queue_size(client.action_queue_size)
            client.logger.info("Client stopped")


if __name__ == "__main__":
    register_third_party_plugins()
    async_client()  # run the client
