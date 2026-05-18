#!/usr/bin/env python
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pyrealsense2 as rs

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.damiao import DamiaoMotorsBus
from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase


ACTION_NAMES = [
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
    "right_gripper.pos",
    "left_joint_1.pos",
    "left_joint_2.pos",
    "left_joint_3.pos",
    "left_joint_4.pos",
    "left_joint_5.pos",
    "left_joint_6.pos",
    "left_joint_7.pos",
    "left_gripper.pos",
]
RIGHT_ARM_FEATURES = ACTION_NAMES[:7]
LEFT_ARM_FEATURES = ACTION_NAMES[8:15]
GRIPPER_FEATURES = ["right_gripper.pos", "left_gripper.pos"]
JOINT4_FEATURES = ["right_joint_4.pos", "left_joint_4.pos"]
FULL_16_FEATURES = ACTION_NAMES.copy()
SELECTED_SCOPE_FEATURES = {
    "right-arm": RIGHT_ARM_FEATURES,
    "both-arms": RIGHT_ARM_FEATURES + LEFT_ARM_FEATURES,
    "full-16": FULL_16_FEATURES,
}
FEATURE_TO_MOTOR = {
    "right_joint_1.pos": "joint_1",
    "right_joint_2.pos": "joint_2",
    "right_joint_3.pos": "joint_3",
    "right_joint_4.pos": "joint_4",
    "right_joint_5.pos": "joint_5",
    "right_joint_6.pos": "joint_6",
    "right_joint_7.pos": "joint_7",
    "right_gripper.pos": "gripper",
    "left_joint_1.pos": "joint_1",
    "left_joint_2.pos": "joint_2",
    "left_joint_3.pos": "joint_3",
    "left_joint_4.pos": "joint_4",
    "left_joint_5.pos": "joint_5",
    "left_joint_6.pos": "joint_6",
    "left_joint_7.pos": "joint_7",
    "left_gripper.pos": "gripper",
}
FEATURE_SIDE = {
    **{key: "right" for key in RIGHT_ARM_FEATURES},
    "right_gripper.pos": "right",
    **{key: "left" for key in LEFT_ARM_FEATURES},
    "left_gripper.pos": "left",
}
MOTOR_INDEX = {
    "joint_1": 0,
    "joint_2": 1,
    "joint_3": 2,
    "joint_4": 3,
    "joint_5": 4,
    "joint_6": 5,
    "joint_7": 6,
    "gripper": 7,
}
FEATURE_LIMITS = {
    "right_joint_1.pos": (-75.0, 75.0),
    "right_joint_2.pos": (-9.0, 90.0),
    "right_joint_3.pos": (-85.0, 85.0),
    "right_joint_4.pos": (0.0, 135.0),
    "right_joint_5.pos": (-85.0, 85.0),
    "right_joint_6.pos": (-40.0, 40.0),
    "right_joint_7.pos": (-80.0, 80.0),
    "right_gripper.pos": (-65.0, 0.0),
    "left_joint_1.pos": (-75.0, 75.0),
    "left_joint_2.pos": (-90.0, 9.0),
    "left_joint_3.pos": (-85.0, 85.0),
    "left_joint_4.pos": (0.0, 135.0),
    "left_joint_5.pos": (-85.0, 85.0),
    "left_joint_6.pos": (-40.0, 40.0),
    "left_joint_7.pos": (-80.0, 80.0),
    "left_gripper.pos": (-65.0, 0.0),
}
ROBOT_CONFIG_ID = "openarms_follower:16d:3cam:v1"
ACTION_SPACE_VERSION = "openarm_folding_abs_16d_deg_v1"
ACTION_UNITS = "degrees"
IMAGE_KEYS = ["left_wrist", "right_wrist", "base"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def selected_features_for_scope(scope: str) -> list[str]:
    return SELECTED_SCOPE_FEATURES[scope].copy()


def excluded_features_for(selected_features: list[str]) -> list[str]:
    selected = set(selected_features)
    return [key for key in ACTION_NAMES if key not in selected]


def make_bus(port: str) -> DamiaoMotorsBus:
    motors: dict[str, Motor] = {}
    for motor_name, (send_id, recv_id, motor_type_str) in OpenArmFollowerConfigBase("").motor_config.items():
        motor = Motor(send_id, motor_type_str, MotorNormMode.DEGREES)
        motor.recv_id = recv_id
        motor.motor_type_str = motor_type_str
        motors[motor_name] = motor
    return DamiaoMotorsBus(
        port=port,
        motors=motors,
        can_interface="socketcan",
        use_can_fd=True,
        bitrate=1000000,
        data_bitrate=5000000,
    )


class EventLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.file = self.path.open("a", buffering=1)

    def write(self, event: str, **payload: Any) -> None:
        row = {
            "event": event,
            "timestamp": time.time(),
            **payload,
        }
        with self.lock:
            self.file.write(json.dumps(row, sort_keys=True) + "\n")

    def close(self) -> None:
        with self.lock:
            self.file.close()


class RealSenseColorStream:
    def __init__(
        self,
        *,
        name: str,
        serial: str,
        width: int,
        height: int,
        fps: int,
        start_retries: int,
        read_retries: int,
    ):
        self.name = name
        self.serial = serial
        self.width = width
        self.height = height
        self.fps = fps
        self.start_retries = start_retries
        self.read_retries = read_retries
        self.pipeline = rs.pipeline()
        self.started = False
        self.actual_profile: tuple[int, int, int] | None = None

    def start(self) -> None:
        last_error: Exception | None = None
        profiles = [
            (self.width, self.height, self.fps),
            (640, 480, self.fps),
            (424, 240, self.fps),
            (640, 480, 30),
            (424, 240, 30),
            (1280, 720, 15),
            (640, 480, 15),
        ]
        profiles = list(dict.fromkeys(profiles))
        for attempt in range(1, self.start_retries + 1):
            for width, height, fps in profiles:
                cfg = rs.config()
                cfg.enable_device(self.serial)
                cfg.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
                try:
                    self.pipeline.start(cfg)
                    self.started = True
                    self.actual_profile = (width, height, fps)
                    for _ in range(10):
                        self.pipeline.wait_for_frames(2000)
                    return
                except Exception as exc:
                    last_error = exc
                    self.stop()
                    time.sleep(min(2.0, 0.1 * attempt))
        raise RuntimeError(f"{self.name} RealSense start failed after {self.start_retries} attempts: {last_error!r}")

    def read(self, timeout_ms: int) -> tuple[np.ndarray, float]:
        last_error: Exception | None = None
        for _ in range(self.read_retries):
            try:
                frames = self.pipeline.wait_for_frames(timeout_ms)
                color = frames.get_color_frame()
                if color:
                    return np.asanyarray(color.get_data()), time.time()
                last_error = RuntimeError(f"{self.name} produced no color frame")
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"{self.name} read failed after {self.read_retries} attempts: {last_error!r}")

    def stop(self) -> None:
        if self.started:
            self.pipeline.stop()
            self.started = False


class LiveCameras:
    def __init__(self, args: argparse.Namespace):
        self.streams = {
            "left_wrist": RealSenseColorStream(
                name="left_wrist",
                serial=args.left_wrist_serial,
                width=args.wrist_width,
                height=args.wrist_height,
                fps=args.camera_fps,
                start_retries=args.camera_start_retries,
                read_retries=args.camera_read_retries,
            ),
            "right_wrist": RealSenseColorStream(
                name="right_wrist",
                serial=args.right_wrist_serial,
                width=args.wrist_width,
                height=args.wrist_height,
                fps=args.camera_fps,
                start_retries=args.camera_start_retries,
                read_retries=args.camera_read_retries,
            ),
            "base": RealSenseColorStream(
                name="base",
                serial=args.base_serial,
                width=args.base_width,
                height=args.base_height,
                fps=args.camera_fps,
                start_retries=args.camera_start_retries,
                read_retries=args.camera_read_retries,
            ),
        }

    def start(self) -> None:
        for stream in self.streams.values():
            stream.start()

    def profiles(self) -> dict[str, list[int] | None]:
        return {
            key: list(stream.actual_profile) if stream.actual_profile is not None else None
            for key, stream in self.streams.items()
        }

    def read_all(self, timeout_ms: int) -> dict[str, tuple[np.ndarray, float]]:
        return {key: stream.read(timeout_ms) for key, stream in self.streams.items()}

    def stop(self) -> None:
        for stream in self.streams.values():
            stream.stop()


class MotorIO:
    def __init__(self, *, right_port: str, left_port: str, selected_features: list[str]):
        self.selected_features = selected_features
        self.by_side = {
            "right": [key for key in selected_features if FEATURE_SIDE[key] == "right"],
            "left": [key for key in selected_features if FEATURE_SIDE[key] == "left"],
        }
        self.all_features_by_side = {
            "right": [key for key in ACTION_NAMES if FEATURE_SIDE[key] == "right"],
            "left": [key for key in ACTION_NAMES if FEATURE_SIDE[key] == "left"],
        }
        self.ports = {"right": right_port, "left": left_port}
        self.buses: dict[str, DamiaoMotorsBus] = {}
        self.connected: set[str] = set()
        self.torque_enabled: dict[str, set[str]] = {"right": set(), "left": set()}
        self.cleanup_errors: list[str] = []
        self.lock = threading.Lock()

    def connect(self) -> None:
        with self.lock:
            for side in ["right", "left"]:
                if self.all_features_by_side[side]:
                    bus = make_bus(self.ports[side])
                    bus.connect(handshake=False)
                    self.buses[side] = bus
                    self.connected.add(side)

    def read_features(self, features: list[str]) -> dict[str, float]:
        with self.lock:
            result: dict[str, float] = {}
            for side in ["right", "left"]:
                side_features = [key for key in features if FEATURE_SIDE[key] == side]
                if not side_features:
                    continue
                motors = [FEATURE_TO_MOTOR[key] for key in side_features]
                states = self.buses[side].sync_read_all_states(motors)
                for key in side_features:
                    result[key] = float(states[FEATURE_TO_MOTOR[key]]["position"])
            return result

    def enable_selected_torque(self) -> None:
        with self.lock:
            for side in ["right", "left"]:
                features = self.by_side[side]
                if not features:
                    continue
                motors = [FEATURE_TO_MOTOR[key] for key in features]
                self.buses[side].enable_torque(motors)
                self.torque_enabled[side].update(motors)

    def disable_selected_torque(self) -> list[str]:
        errors: list[str] = []
        with self.lock:
            for side in ["right", "left"]:
                motors = sorted(self.torque_enabled[side], key=lambda motor: MOTOR_INDEX[motor])
                for motor in motors:
                    try:
                        # Send several disable frames even when the first call reports no
                        # exception; Damiao's simple command path may not raise on a
                        # missing response, and cleanup must favor leaving motors idle.
                        for _ in range(3):
                            self.buses[side].disable_torque([motor], num_retry=1)
                            time.sleep(0.03)
                        self.torque_enabled[side].discard(motor)
                    except Exception as exc:
                        message = f"{side}.{motor} disable_torque_failed: {exc!r}"
                        errors.append(message)
                        self.cleanup_errors.append(message)
            return errors

    def send_targets(self, targets: dict[str, float]) -> None:
        commands_by_side = build_commands_by_side(targets, self.ports)
        with self.lock:
            for side, commands in commands_by_side.items():
                if commands:
                    self.buses[side]._mit_control_batch(commands)

    def disconnect(self) -> list[str]:
        errors = self.disable_selected_torque()
        with self.lock:
            for side in list(self.connected):
                try:
                    self.buses[side].disconnect(disable_torque=False)
                    self.connected.discard(side)
                except Exception as exc:
                    message = f"{side}.disconnect_failed: {exc!r}"
                    errors.append(message)
                    self.cleanup_errors.append(message)
            return errors


class LiveActionQueue:
    def __init__(self):
        self.lock = threading.Lock()
        self.queue: list[list[float]] = []
        self.source_obs_seq: int | None = None
        self.actions_executed = 0
        self.chunks_received = 0
        self.chunks_accepted = 0

    def qsize(self) -> int:
        with self.lock:
            return len(self.queue)

    def action_index(self) -> int:
        with self.lock:
            return self.actions_executed

    def leftover(self) -> list[list[float]] | None:
        with self.lock:
            if not self.queue:
                return None
            return [row.copy() for row in self.queue]

    def replace(self, actions: list[list[float]], *, skip: int, obs_seq: int) -> int:
        with self.lock:
            self.chunks_received += 1
            accepted = actions[max(0, skip) :]
            self.queue = [row.copy() for row in accepted]
            self.source_obs_seq = obs_seq
            self.chunks_accepted += 1
            return len(self.queue)

    def pop(self) -> list[float] | None:
        with self.lock:
            if not self.queue:
                return None
            action = self.queue.pop(0)
            self.actions_executed += 1
            return action


def build_commands_by_side(
    targets: dict[str, float],
    ports: dict[str, str],
) -> dict[str, dict[str, tuple[float, float, float, float, float]]]:
    configs = {
        "right": OpenArmFollowerConfigBase(port=ports["right"], side="right"),
        "left": OpenArmFollowerConfigBase(port=ports["left"], side="left"),
    }
    commands: dict[str, dict[str, tuple[float, float, float, float, float]]] = {"right": {}, "left": {}}
    for key, target_deg in targets.items():
        side = FEATURE_SIDE[key]
        motor = FEATURE_TO_MOTOR[key]
        idx = MOTOR_INDEX[motor]
        config = configs[side]
        kp = config.position_kp[idx] if isinstance(config.position_kp, list) else config.position_kp
        kd = config.position_kd[idx] if isinstance(config.position_kd, list) else config.position_kd
        commands[side][motor] = (float(kp), float(kd), float(target_deg), 0.0, 0.0)
    return commands


def encode_image(image_bgr: np.ndarray, *, quality: int) -> dict[str, Any]:
    ok, encoded = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError("failed to encode JPEG")
    raw = encoded.tobytes()
    return {
        "encoding": "jpeg_base64",
        "data": base64.b64encode(raw).decode("ascii"),
        "sha256": sha256_bytes(raw),
        "shape": list(image_bgr.shape),
    }


def live_observation_checksum(*, obs_seq: int, state: list[float], image_sha256: dict[str, str]) -> str:
    payload = {
        "image_sha256": image_sha256,
        "obs_seq": int(obs_seq),
        "state": [float(value) for value in state],
        "state_names": ACTION_NAMES,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def post_json(url: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    cleanup_errors: list[str] = []
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {error_body}") from exc


def get_json(url: str, timeout_s: float) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_health(payload: dict[str, Any], envelope: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "ok":
        errors.append(f"health status is not ok: {payload.get('status')!r}")
    for key, expected in [
        ("robot_config_id", ROBOT_CONFIG_ID),
        ("action_space_version", ACTION_SPACE_VERSION),
        ("joint_order", ACTION_NAMES),
        ("action_units", ACTION_UNITS),
    ]:
        if payload.get(key) != expected:
            errors.append(f"health {key} mismatch")
    if payload.get("send_allowed") is not False or payload.get("motion_allowed") is not False:
        errors.append("health motion flags are not false")
    if envelope is not None:
        for key in ["model_id", "checkpoint_id", "robot_config_id", "action_normalization_id"]:
            if key in envelope and envelope[key] != payload.get(key):
                errors.append(f"health envelope {key} mismatch")
    return errors


def validate_proposal(
    proposal: dict[str, Any],
    *,
    request_payload: dict[str, Any],
    envelope: dict[str, Any] | None,
    excluded_features: list[str],
    relaxed_proposal_validation: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if proposal.get("schema") != "openarm_folding_live_action_proposal_v1":
        errors.append("unexpected proposal schema")
    if proposal.get("obs_seq") != request_payload.get("obs_seq"):
        if relaxed_proposal_validation:
            warnings.append("proposal obs_seq mismatch")
        else:
            errors.append("proposal obs_seq mismatch")
    if proposal.get("obs_checksum") != request_payload.get("obs_checksum"):
        if relaxed_proposal_validation:
            warnings.append("proposal obs_checksum mismatch")
        else:
            errors.append("proposal obs_checksum mismatch")
    if proposal.get("action_shape") != [1, 30, 16]:
        errors.append(f"unexpected action_shape={proposal.get('action_shape')!r}")
    if proposal.get("all_finite") is not True:
        errors.append("proposal all_finite is not true")
    if proposal.get("send_allowed") is not False or proposal.get("motion_allowed") is not False:
        errors.append("proposal motion flags are not false")
    if proposal.get("actuator_commands_sent") is not False:
        errors.append("proposal actuator_commands_sent is not false")
    for key, expected in [
        ("robot_config_id", ROBOT_CONFIG_ID),
        ("action_space_version", ACTION_SPACE_VERSION),
        ("joint_order", ACTION_NAMES),
        ("action_units", ACTION_UNITS),
        ("is_absolute_action", True),
    ]:
        if proposal.get(key) != expected:
            errors.append(f"proposal {key} mismatch")
    rows = proposal.get("rows", [])
    for row in rows:
        if row.get("key") in excluded_features and row.get("send_allowed") is not False:
            errors.append(f"excluded feature marked send_allowed: {row.get('key')}")
    if envelope is not None:
        for key in [
            "model_id",
            "checkpoint_id",
            "robot_config_id",
            "action_normalization_id",
            "action_space_version",
            "joint_order",
            "action_units",
            "is_absolute_action",
        ]:
            if key in envelope and envelope[key] != proposal.get(key):
                errors.append(f"proposal envelope {key} mismatch")
    try:
        actions = proposal["predicted_abs_action_chunk"]
        if len(actions) != 1 or len(actions[0]) != 30:
            errors.append("predicted_abs_action_chunk shape mismatch")
        for step in actions[0]:
            if len(step) != 16 or not all(np.isfinite(float(value)) for value in step):
                errors.append("invalid action step in predicted_abs_action_chunk")
                break
    except Exception as exc:
        errors.append(f"invalid predicted_abs_action_chunk: {exc!r}")
    return errors, warnings


def action_chunk(proposal: dict[str, Any]) -> list[list[float]]:
    return [[float(value) for value in row] for row in proposal["predicted_abs_action_chunk"][0]]


def feature_delta_cap(key: str, args: argparse.Namespace) -> float:
    if key in GRIPPER_FEATURES:
        return float(args.gripper_delta_cap_deg)
    return float(args.arm_delta_cap_deg)


def readback_threshold(key: str, *, soft: bool, args: argparse.Namespace) -> float:
    if key in GRIPPER_FEATURES:
        return float(args.gripper_readback_soft_error_deg if soft else args.gripper_readback_hard_error_deg)
    return float(args.arm_readback_soft_error_deg if soft else args.arm_readback_hard_error_deg)


def maybe_saturate_limit(
    key: str,
    value: float,
    *,
    args: argparse.Namespace,
) -> tuple[float, int, int, int]:
    lo, hi = FEATURE_LIMITS[key]
    clamped = clamp(value, lo, hi)
    if clamped == value:
        return value, 0, 0, 0
    if key in GRIPPER_FEATURES and args.allow_gripper_limit_saturation:
        return clamped, 1, 0, 0
    if key in JOINT4_FEATURES and args.allow_joint4_limit_saturation:
        return clamped, 0, 1, 0
    if args.allow_joint_limit_saturation:
        return clamped, 0, 0, 1
    return value, 0, 0, 0


def validate_runtime_args(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    """One-time startup check for constant CLI parameters, kept out of the action hot-path."""
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    if args.action_period_s <= 0:
        hard_errors.append("--action-period-s must be positive")
    if args.interpolation_multiplier <= 0:
        hard_errors.append("--interpolation-multiplier must be positive")
    if args.record_frame_every_n_obs <= 0:
        hard_errors.append("--record-frame-every-n-obs must be positive")
    if args.camera_start_retries <= 0:
        hard_errors.append("--camera-start-retries must be positive")
    if args.camera_read_retries <= 0:
        hard_errors.append("--camera-read-retries must be positive")
    if args.max_chunks <= 0:
        hard_errors.append("--max-chunks must be positive")
    if args.max_session_duration_s <= 0:
        hard_errors.append("--max-session-duration-s must be positive")
    if args.camera_fps < 30:
        soft_warnings.append("camera_fps below robot-folding recipe/data rate of 30 fps")
    if args.action_period_s > (1.0 / 30.0) + 1e-6:
        soft_warnings.append("action_period_s slower than robot-folding 30 Hz policy cadence")
    return hard_errors, soft_warnings


def prepare_action_targets(
    action: list[float],
    current: dict[str, float],
    *,
    selected_features: list[str],
    args: argparse.Namespace,
) -> tuple[dict[str, float], list[str], list[str], int, int, int, int]:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    targets = {key: float(action[ACTION_NAMES.index(key)]) for key in selected_features}
    gripper_saturated = 0
    joint4_saturated = 0
    joint_limit_saturated = 0
    clipped = 0
    for key in selected_features:
        lo, hi = FEATURE_LIMITS[key]
        targets[key], grip_sat, j4_sat, joint_sat = maybe_saturate_limit(key, targets[key], args=args)
        gripper_saturated += grip_sat
        joint4_saturated += j4_sat
        joint_limit_saturated += joint_sat
        if not (lo <= targets[key] <= hi):
            hard_errors.append(f"{key} target {targets[key]:.6f} outside [{lo}, {hi}]")
            continue
        cap = feature_delta_cap(key, args)
        delta = targets[key] - current[key]
        if abs(delta) > cap + 1e-6:
            if args.clip_to_delta_cap:
                targets[key] = clamp(current[key] + clamp(delta, -cap, cap), lo, hi)
                clipped += 1
            else:
                soft_warnings.append(f"{key} delta {delta:.6f} exceeds cap {cap:.6f}")
        targets[key], grip_sat, j4_sat, joint_sat = maybe_saturate_limit(key, targets[key], args=args)
        gripper_saturated += grip_sat
        joint4_saturated += j4_sat
        joint_limit_saturated += joint_sat
        if not (lo <= targets[key] <= hi):
            hard_errors.append(f"{key} target {targets[key]:.6f} outside [{lo}, {hi}]")
    return targets, hard_errors, soft_warnings, clipped, gripper_saturated, joint4_saturated, joint_limit_saturated


def execute_one_action(
    action: list[float],
    *,
    motor_io: MotorIO,
    selected_features: list[str],
    args: argparse.Namespace,
    logger: EventLogger,
    step_index: int,
) -> tuple[bool, bool, dict[str, Any]]:
    current = motor_io.read_features(selected_features)
    (
        targets,
        hard_errors,
        soft_warnings,
        clipped,
        gripper_saturated,
        joint4_saturated,
        joint_limit_saturated,
    ) = prepare_action_targets(
        action,
        current,
        selected_features=selected_features,
        args=args,
    )
    if hard_errors:
        return False, False, {"hard_errors": hard_errors, "soft_warnings": soft_warnings}
    if soft_warnings and not args.safety_monitor_only:
        return True, False, {"hard_errors": [], "soft_warnings": soft_warnings}

    substeps = max(1, int(args.interpolation_multiplier))
    subperiod = float(args.action_period_s) / substeps
    for substep in range(1, substeps + 1):
        ratio = substep / substeps
        interpolated = {
            key: current[key] + (targets[key] - current[key]) * ratio
            for key in selected_features
        }
        motor_io.send_targets(interpolated)
        time.sleep(subperiod)

    # Readback is a blocking CAN sync-read that adds ~5–10 ms per step.
    # With --readback-stride N, only read every N steps (0 = never).
    # Use --readback-stride 0 for smooth 30 Hz motion; default 1 preserves old behaviour.
    stride = int(args.readback_stride)
    do_readback = stride > 0 and (step_index % stride == 0)
    per_joint: dict[str, Any] = {}
    hard_readback: list[str] = []
    soft_readback: list[str] = []
    if do_readback:
        readback = motor_io.read_features(selected_features)
        for key in selected_features:
            error = readback[key] - targets[key]
            abs_error = abs(error)
            soft_threshold = readback_threshold(key, soft=True, args=args)
            hard_threshold = readback_threshold(key, soft=False, args=args)
            per_joint[key] = {
                "target_deg": targets[key],
                "readback_deg": readback[key],
                "error_deg": error,
                "soft_threshold_deg": soft_threshold,
                "hard_threshold_deg": hard_threshold,
            }
            if abs_error > soft_threshold:
                soft_readback.append(f"{key} readback {abs_error:.6f} > soft {soft_threshold:.6f}")
            if abs_error > hard_threshold:
                hard_readback.append(f"{key} readback {abs_error:.6f} > hard {hard_threshold:.6f}")
    commanded_deltas = {key: abs(targets[key] - current[key]) for key in selected_features}
    max_commanded_key = max(commanded_deltas, key=commanded_deltas.get)
    max_commanded_delta = commanded_deltas[max_commanded_key]
    max_readback_key = None
    max_readback_error = None
    if per_joint:
        max_readback_key = max(per_joint, key=lambda key: abs(per_joint[key]["error_deg"]))
        max_readback_error = abs(per_joint[max_readback_key]["error_deg"])
    logger.write(
        "action_executed",
        step_index=step_index,
        clipped_features=clipped,
        gripper_saturated_features=gripper_saturated,
        joint4_saturated_features=joint4_saturated,
        joint_limit_saturated_features=joint_limit_saturated,
        max_abs_commanded_delta_key=max_commanded_key,
        max_abs_commanded_delta_deg=max_commanded_delta,
        max_abs_readback_error_key=max_readback_key,
        max_abs_readback_error_deg=max_readback_error,
        readback_performed=bool(per_joint),
        hard_readback=hard_readback,
        soft_readback=soft_readback,
    )
    command_ok = not hard_readback if not args.safety_monitor_only else True
    soft_ok = not soft_readback if not args.safety_monitor_only else True
    return command_ok, soft_ok, {
        "hard_errors": hard_readback,
        "soft_warnings": [*soft_warnings, *soft_readback],
        "per_joint": per_joint,
        "clipped_features": clipped,
        "gripper_saturated_features": gripper_saturated,
        "joint4_saturated_features": joint4_saturated,
        "joint_limit_saturated_features": joint_limit_saturated,
        "max_abs_commanded_delta_key": max_commanded_key,
        "max_abs_commanded_delta_deg": max_commanded_delta,
        "max_abs_readback_error_key": max_readback_key,
        "max_abs_readback_error_deg": max_readback_error,
    }


def build_live_request(
    *,
    obs_seq: int,
    motor_io: MotorIO,
    cameras: LiveCameras,
    action_queue: LiveActionQueue,
    args: argparse.Namespace,
    last_inference_latency_s: float,
) -> dict[str, Any]:
    state_dict = motor_io.read_features(ACTION_NAMES)
    state = [float(np.float32(state_dict[key])) for key in ACTION_NAMES]
    camera_frames = cameras.read_all(int(args.camera_timeout_ms))
    images = {}
    image_sha256 = {}
    camera_age_s = {}
    now = time.time()
    for key, (image, timestamp) in camera_frames.items():
        if args.record_eval_frames and obs_seq % int(args.record_frame_every_n_obs) == 0:
            frame_dir = args.trial_root / "live_session" / "eval_frames"
            frame_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(frame_dir / f"obs_{obs_seq:06d}_{key}.jpg"), image)
        entry = encode_image(image, quality=args.jpeg_quality)
        images[key] = entry
        image_sha256[key] = entry["sha256"]
        camera_age_s[key] = now - timestamp
    obs_checksum = live_observation_checksum(obs_seq=obs_seq, state=state, image_sha256=image_sha256)
    estimated_delay = max(0, int(round(last_inference_latency_s / float(args.action_period_s))))
    return {
        "schema": "openarm_folding_live_observation_v1",
        "obs_seq": obs_seq,
        "obs_timestamp": now,
        "obs_checksum": obs_checksum,
        "robot_type": args.robot_type,
        "task": args.task,
        "state_names": ACTION_NAMES,
        "state": state,
        "images": images,
        "image_keys": IMAGE_KEYS,
        "image_sha256": image_sha256,
        "camera_age_s": camera_age_s,
        "prev_leftover_abs_action_chunk": action_queue.leftover(),
        "inference_delay_steps": estimated_delay,
        "execution_horizon": args.execution_horizon,
        "send_action": False,
    }


def default_approval_phrase(trial_id: str) -> str:
    return f"APPROVE_LIVE_ROLLOUT_SESSION_{trial_id.upper().replace('-', '_')}"


def write_approval_draft(path_json: Path | None, path_md: Path | None, envelope: dict[str, Any]) -> None:
    if path_json is not None:
        path_json.parent.mkdir(parents=True, exist_ok=True)
        path_json.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    if path_md is None:
        return
    selected = envelope["selected_features"]
    lines = [
        "# OpenArm Live Rollout Session Envelope Approval Draft",
        "",
        "This is a draft only. It is not approval.",
        "",
        "```text",
            "operator_at_robot: true",
            "power_abort_control_held: true",
            "estop_ready: true",
        "right_arm_workspace_clear: true",
    ]
    if any(FEATURE_SIDE[key] == "left" for key in selected):
        lines.append("left_arm_workspace_clear: true")
    if any(key in GRIPPER_FEATURES for key in selected):
        lines.append("gripper_workspace_clear: true")
    lines.extend(
        [
            "human_body_clear_of_arm: true",
            "approval_applies_to_live_rollout_session_envelope: true",
            f"approval_phrase: {envelope['approval_phrase']}",
            "```",
            "",
            "Safety measurements are monitor-only in this envelope. The operator's visual review and power cutoff are the safety gates.",
            "",
            "```json",
            json.dumps(envelope, indent=2, sort_keys=True),
            "```",
        ]
    )
    path_md.parent.mkdir(parents=True, exist_ok=True)
    path_md.write_text("\n".join(lines) + "\n")


def build_envelope(args: argparse.Namespace, metadata: dict[str, Any], selected_features: list[str]) -> dict[str, Any]:
    trial_id = args.trial_root.name
    return {
        "schema": "openarm_folding_live_rollout_session_envelope_v1",
        "rollout_trial_id": trial_id,
        "approval_phrase": default_approval_phrase(trial_id),
        "model_id": metadata.get("model_id"),
        "checkpoint_id": metadata.get("checkpoint_id"),
        "robot_config_id": metadata.get("robot_config_id"),
        "action_normalization_id": metadata.get("action_normalization_id"),
        "action_space_version": metadata.get("action_space_version"),
        "joint_order": metadata.get("joint_order"),
        "action_units": metadata.get("action_units"),
        "is_absolute_action": metadata.get("is_absolute_action", True),
        "rtc_enabled": metadata.get("rtc_enabled"),
        "rtc_execution_horizon": metadata.get("rtc_execution_horizon"),
        "rtc_max_guidance_weight": metadata.get("rtc_max_guidance_weight"),
        "rtc_prefix_attention_schedule": metadata.get("rtc_prefix_attention_schedule"),
        "use_relative_actions": metadata.get("use_relative_actions"),
        "selected_scope": args.selected_scope,
        "selected_features": selected_features,
        "max_session_duration_s": args.max_session_duration_s,
        "max_chunks": args.max_chunks,
        "execution_horizon": args.execution_horizon,
        "refresh_queue_threshold": args.refresh_queue_threshold,
        "action_period_s": args.action_period_s,
        "interpolation_multiplier": args.interpolation_multiplier,
        "arm_delta_cap_deg": args.arm_delta_cap_deg,
        "gripper_delta_cap_deg": args.gripper_delta_cap_deg,
        "arm_readback_soft_error_deg": args.arm_readback_soft_error_deg,
        "arm_readback_hard_error_deg": args.arm_readback_hard_error_deg,
        "gripper_readback_soft_error_deg": args.gripper_readback_soft_error_deg,
        "gripper_readback_hard_error_deg": args.gripper_readback_hard_error_deg,
        "request_timeout_s": args.request_timeout_s,
        "max_consecutive_inference_errors": args.max_consecutive_inference_errors,
        "clip_to_delta_cap": args.clip_to_delta_cap,
        "readback_stride": args.readback_stride,
        "hold_last_action": args.hold_last_action,
        "relaxed_proposal_validation": args.relaxed_proposal_validation,
        "record_eval_frames": args.record_eval_frames,
        "record_frame_every_n_obs": args.record_frame_every_n_obs,
        "allow_gripper_limit_saturation": args.allow_gripper_limit_saturation,
        "allow_joint4_limit_saturation": args.allow_joint4_limit_saturation,
        "allow_joint_limit_saturation": args.allow_joint_limit_saturation,
        "safety_monitor_only": args.safety_monitor_only,
        "operator_visual_review_and_power_cutoff_are_safety_gates": args.safety_monitor_only,
        "forbid_send_action_path": True,
        "forbid_lerobot_rollout_actual_path": True,
        "forbid_openarm_follower_connect_actual_path": True,
        "actuator_path": "DamiaoMotorsBus guarded MIT batch",
    }


def validate_envelope(envelope: dict[str, Any], args: argparse.Namespace, selected_features: list[str]) -> list[str]:
    errors: list[str] = []
    if envelope.get("schema") != "openarm_folding_live_rollout_session_envelope_v1":
        errors.append("unexpected envelope schema")
    if envelope.get("rollout_trial_id") != args.trial_root.name:
        errors.append("envelope rollout_trial_id mismatch")
    if envelope.get("selected_features") != selected_features:
        errors.append("envelope selected_features mismatch")
    if "max_session_duration_s" in envelope and float(args.max_session_duration_s) > float(envelope["max_session_duration_s"]) + 1e-6:
        errors.append("max_session_duration_s exceeds envelope")
    if "max_chunks" in envelope and int(args.max_chunks) > int(envelope["max_chunks"]):
        errors.append("max_chunks exceeds envelope")
    if "execution_horizon" in envelope and int(args.execution_horizon) != int(envelope["execution_horizon"]):
        errors.append("execution_horizon mismatch")
    if "refresh_queue_threshold" in envelope and int(args.refresh_queue_threshold) != int(envelope["refresh_queue_threshold"]):
        errors.append("refresh_queue_threshold mismatch")
    for key, value in [
        ("action_period_s", args.action_period_s),
        ("interpolation_multiplier", args.interpolation_multiplier),
        ("arm_delta_cap_deg", args.arm_delta_cap_deg),
        ("gripper_delta_cap_deg", args.gripper_delta_cap_deg),
        ("arm_readback_soft_error_deg", args.arm_readback_soft_error_deg),
        ("arm_readback_hard_error_deg", args.arm_readback_hard_error_deg),
        ("gripper_readback_soft_error_deg", args.gripper_readback_soft_error_deg),
        ("gripper_readback_hard_error_deg", args.gripper_readback_hard_error_deg),
        ("request_timeout_s", args.request_timeout_s),
    ]:
        if key in envelope and abs(float(envelope[key]) - float(value)) > 1e-6:
            errors.append(f"envelope {key} mismatch")
    for key, value in [
        ("max_consecutive_inference_errors", args.max_consecutive_inference_errors),
        ("record_frame_every_n_obs", args.record_frame_every_n_obs),
    ]:
        if key in envelope and int(envelope[key]) != int(value):
            errors.append(f"envelope {key} mismatch")
    for key, value in [
        ("clip_to_delta_cap", args.clip_to_delta_cap),
        ("relaxed_proposal_validation", args.relaxed_proposal_validation),
        ("record_eval_frames", args.record_eval_frames),
        ("allow_gripper_limit_saturation", args.allow_gripper_limit_saturation),
        ("allow_joint4_limit_saturation", args.allow_joint4_limit_saturation),
        ("allow_joint_limit_saturation", args.allow_joint_limit_saturation),
        ("safety_monitor_only", args.safety_monitor_only),
    ]:
        if key in envelope and bool(envelope[key]) != bool(value):
            errors.append(f"envelope {key} mismatch")
    for key in ["forbid_send_action_path", "forbid_lerobot_rollout_actual_path", "forbid_openarm_follower_connect_actual_path"]:
        if envelope.get(key) is not True:
            errors.append(f"envelope {key} must be true")
    if envelope.get("actuator_path") != "DamiaoMotorsBus guarded MIT batch":
        errors.append("envelope actuator_path mismatch")
    return errors


def inference_loop(
    *,
    args: argparse.Namespace,
    cameras: LiveCameras,
    motor_io: MotorIO,
    action_queue: LiveActionQueue,
    selected_features: list[str],
    excluded_features: list[str],
    envelope: dict[str, Any] | None,
    logger: EventLogger,
    stop_event: threading.Event,
    shared: dict[str, Any],
) -> None:
    obs_seq = 0
    last_latency = 0.0
    consecutive_errors = 0
    while not stop_event.is_set():
        if time.time() - shared["session_started_at"] > float(args.max_session_duration_s):
            shared["stop_reason"] = "max_session_duration_s"
            stop_event.set()
            break
        if action_queue.chunks_accepted >= int(args.max_chunks):
            shared["stop_reason"] = "max_chunks"
            stop_event.set()
            break
        if action_queue.qsize() > int(args.refresh_queue_threshold):
            time.sleep(0.01)
            continue
        action_index_before = action_queue.action_index()
        try:
            request_payload = build_live_request(
                obs_seq=obs_seq,
                motor_io=motor_io,
                cameras=cameras,
                action_queue=action_queue,
                args=args,
                last_inference_latency_s=last_latency,
            )
            started = time.time()
            proposal = post_json(args.predict_url, request_payload, args.request_timeout_s)
            last_latency = time.time() - started
            errors, warnings = validate_proposal(
                proposal,
                request_payload=request_payload,
                envelope=envelope,
                excluded_features=excluded_features,
                relaxed_proposal_validation=args.relaxed_proposal_validation,
            )
            if warnings:
                logger.write("proposal_validation_warning", obs_seq=obs_seq, warnings=warnings)
            if errors:
                shared["stop_reason"] = f"proposal_validation_failed: {errors}"
                logger.write("hard_block", reason=shared["stop_reason"])
                stop_event.set()
                break
            observed_delay = max(0, action_queue.action_index() - action_index_before)
            accepted = action_queue.replace(
                action_chunk(proposal),
                skip=observed_delay,
                obs_seq=obs_seq,
            )
            logger.write(
                "chunk_accepted",
                obs_seq=obs_seq,
                accepted_actions=accepted,
                observed_delay_steps=observed_delay,
                estimated_delay_steps=request_payload["inference_delay_steps"],
                inference_latency_s=last_latency,
                queue_depth=action_queue.qsize(),
            )
            consecutive_errors = 0
            obs_seq += 1
        except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
            consecutive_errors += 1
            logger.write("inference_error", error=repr(exc), consecutive_errors=consecutive_errors)
            if action_queue.qsize() == 0 or consecutive_errors >= int(args.max_consecutive_inference_errors):
                shared["stop_reason"] = f"inference_failed: {exc!r}"
                stop_event.set()
                break
            time.sleep(0.05)


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live guarded OpenArm folding rollout client.")
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument("--predict-url", default="http://10.252.205.103:8765/predict_live")
    parser.add_argument("--health-url", default="http://10.252.205.103:8765/health")
    parser.add_argument("--task", default="Fold the T-shirt properly")
    parser.add_argument("--robot-type", default="openarms_follower")
    parser.add_argument("--left-wrist-serial", default="315122270766")
    parser.add_argument("--right-wrist-serial", default="230322273311")
    parser.add_argument("--base-serial", required=True)
    parser.add_argument("--left-port", default="can0")
    parser.add_argument("--right-port", default="can1")
    parser.add_argument("--camera-fps", type=int, default=30)
    parser.add_argument("--wrist-width", type=int, default=640)
    parser.add_argument("--wrist-height", type=int, default=480)
    parser.add_argument("--base-width", type=int, default=640)
    parser.add_argument("--base-height", type=int, default=480)
    parser.add_argument("--camera-timeout-ms", type=int, default=2000)
    parser.add_argument("--camera-start-retries", type=int, default=3)
    parser.add_argument("--camera-read-retries", type=int, default=2)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--request-timeout-s", type=float, default=60.0)
    parser.add_argument("--selected-scope", choices=sorted(SELECTED_SCOPE_FEATURES), default="full-16")
    parser.add_argument("--max-session-duration-s", type=float, default=30.0)
    parser.add_argument("--max-chunks", type=int, default=12)
    parser.add_argument("--refresh-queue-threshold", type=int, default=10)
    parser.add_argument("--execution-horizon", type=int, default=20)
    parser.add_argument("--action-period-s", type=float, default=1.0 / 30.0)
    parser.add_argument("--interpolation-multiplier", type=int, default=3)
    parser.add_argument("--arm-delta-cap-deg", type=float, default=7.0)
    parser.add_argument("--gripper-delta-cap-deg", type=float, default=30.0)
    parser.add_argument("--arm-readback-soft-error-deg", type=float, default=5.0)
    parser.add_argument("--arm-readback-hard-error-deg", type=float, default=5.0)
    parser.add_argument("--gripper-readback-soft-error-deg", type=float, default=30.0)
    parser.add_argument("--gripper-readback-hard-error-deg", type=float, default=30.0)
    parser.add_argument("--max-consecutive-inference-errors", type=int, default=5)
    parser.add_argument("--max-repeated-hard-readback", type=int, default=2)
    parser.add_argument("--clip-to-delta-cap", action="store_true")
    parser.add_argument(
        "--readback-stride",
        type=int,
        default=1,
        help=(
            "Read back motor positions every N action steps to check tracking error. "
            "0 = never read back (removes blocking CAN read from hot-path, smoothest motion). "
            "1 = every step (default, original behaviour). "
            "30 = once per chunk (balanced logging vs. timing)."
        ),
    )
    parser.add_argument(
        "--hold-last-action",
        action="store_true",
        help=(
            "When the action queue drains between inference chunks, re-send the last "
            "absolute target instead of pausing. Eliminates motion gaps during chunk refresh."
        ),
    )
    parser.add_argument(
        "--relaxed-proposal-validation",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "When set, demote proposal obs_seq / obs_checksum mismatches from hard "
            "errors to soft warnings. schema/action_shape/all_finite/motion_flags "
            "checks remain hard. Use for long closed-loop sessions where state read "
            "race with inference is acceptable."
        ),
    )
    parser.add_argument("--allow-gripper-limit-saturation", action="store_true")
    parser.add_argument("--allow-joint4-limit-saturation", action="store_true")
    parser.add_argument("--allow-joint-limit-saturation", action="store_true")
    parser.add_argument(
        "--safety-monitor-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Log delta/readback/camera safety measurements without using them as software pause/block gates.",
    )
    parser.add_argument("--session-envelope-json", type=Path)
    parser.add_argument("--approval-draft-json", type=Path)
    parser.add_argument("--approval-draft-md", type=Path)
    parser.add_argument("--record-eval-frames", action="store_true")
    parser.add_argument("--record-frame-every-n-obs", type=int, default=30)
    parser.add_argument("--operator-stop-file", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--operator-session-approval-given", action="store_true")
    parser.add_argument("--operator-at-robot", action="store_true")
    parser.add_argument("--power-held", action="store_true")
    parser.add_argument("--abort-ready", action="store_true")
    parser.add_argument("--estop-ready", action="store_true")
    parser.add_argument("--right-arm-workspace-clear", action="store_true")
    parser.add_argument("--left-arm-workspace-clear", action="store_true")
    parser.add_argument("--gripper-workspace-clear", action="store_true")
    parser.add_argument("--human-body-clear-of-arm", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.trial_root.mkdir(parents=True, exist_ok=True)
    session_root = args.trial_root / "live_session"
    events_path = session_root / "events.ndjson"
    summary_path = session_root / "summary.json"
    logger = EventLogger(events_path)
    selected_features = selected_features_for_scope(args.selected_scope)
    excluded_features = excluded_features_for(selected_features)
    envelope = json.loads(args.session_envelope_json.read_text()) if args.session_envelope_json else None
    rt_hard, rt_soft = validate_runtime_args(args)
    hard_errors: list[str] = list(rt_hard)
    soft_warnings: list[str] = list(rt_soft)
    if envelope is not None:
        hard_errors.extend(validate_envelope(envelope, args, selected_features))
    if args.execute:
        if envelope is None:
            hard_errors.append("--session-envelope-json is required with --execute")
        else:
            if args.confirm != envelope.get("approval_phrase"):
                hard_errors.append("approval phrase mismatch")
        for flag, message in [
            (args.operator_session_approval_given, "--operator-session-approval-given is required"),
            (args.operator_at_robot, "--operator-at-robot is required"),
            (args.power_held, "--power-held is required"),
            (args.abort_ready, "--abort-ready is required"),
            (args.estop_ready, "--estop-ready is required"),
            (args.right_arm_workspace_clear, "--right-arm-workspace-clear is required"),
            (args.human_body_clear_of_arm, "--human-body-clear-of-arm is required"),
        ]:
            if not flag:
                hard_errors.append(message)
        if any(FEATURE_SIDE[key] == "left" for key in selected_features) and not args.left_arm_workspace_clear:
            hard_errors.append("--left-arm-workspace-clear is required")
        if any(key in GRIPPER_FEATURES for key in selected_features) and not args.gripper_workspace_clear:
            hard_errors.append("--gripper-workspace-clear is required")
    if hard_errors:
        payload = {
            "schema": "openarm_folding_live_rollout_summary_v1",
            "motion_status": "BLOCKED_FOR_REVIEW",
            "hard_errors": hard_errors,
            "soft_warnings": soft_warnings,
            "actuator_commands_sent": False,
        }
        write_summary(summary_path, payload)
        logger.write("blocked_before_start", hard_errors=hard_errors)
        logger.close()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2
    if soft_warnings:
        logger.write("startup_soft_warnings", soft_warnings=soft_warnings)

    action_queue = LiveActionQueue()
    cameras = LiveCameras(args)
    motor_io = MotorIO(right_port=args.right_port, left_port=args.left_port, selected_features=selected_features)
    stop_event = threading.Event()
    shared: dict[str, Any] = {
        "session_started_at": time.time(),
        "stop_reason": None,
    }
    stats: dict[str, Any] = {
        "actions_executed": 0,
        "chunks_accepted": 0,
        "clipped_features": 0,
        "gripper_saturated_features": 0,
        "joint4_saturated_features": 0,
        "joint_limit_saturated_features": 0,
        "soft_warnings": 0,
        "hard_readback_streak": 0,
        "max_abs_readback_error_deg": None,
        "max_abs_commanded_delta_deg": None,
    }
    motion_status = "LIVE_MONITOR_NO_ACTUATION"
    actuator_commands_sent = False
    exit_code = 0
    try:
        health = get_json(args.health_url, args.request_timeout_s)
        health_errors = validate_health(health, envelope)
        if health_errors:
            raise RuntimeError(f"health validation failed: {health_errors}")
        logger.write("health_ok", health=health)
        if args.approval_draft_json or args.approval_draft_md:
            draft = build_envelope(args, health, selected_features)
            write_approval_draft(args.approval_draft_json, args.approval_draft_md, draft)
            logger.write("approval_draft_written_from_health", approval_phrase=draft["approval_phrase"])
            if not args.execute:
                shared["stop_reason"] = "approval_draft_written_from_health"
                motion_status = "ARMED_ENVELOPE_DRAFT_ONLY"
                return 0
        cameras.start()
        logger.write("cameras_started", profiles=cameras.profiles())
        motor_io.connect()
        if args.execute:
            motor_io.enable_selected_torque()
            motion_status = "ROLLOUT_SESSION_ACTIVE"

        worker = threading.Thread(
            target=inference_loop,
            kwargs={
                "args": args,
                "cameras": cameras,
                "motor_io": motor_io,
                "action_queue": action_queue,
                "selected_features": selected_features,
                "excluded_features": excluded_features,
                "envelope": envelope,
                "logger": logger,
                "stop_event": stop_event,
                "shared": shared,
            },
            daemon=True,
        )
        worker.start()
        step_index = 0
        last_action: list[float] | None = None
        while not stop_event.is_set():
            if args.operator_stop_file is not None and args.operator_stop_file.exists():
                shared["stop_reason"] = "operator_stop_file"
                stop_event.set()
                break
            if time.time() - shared["session_started_at"] > float(args.max_session_duration_s):
                shared["stop_reason"] = "max_session_duration_s"
                stop_event.set()
                break
            if not args.execute:
                time.sleep(0.05)
                continue
            action = action_queue.pop()
            if action is None:
                # When the queue drains between chunks, hold the last absolute target
                # instead of sleeping so the robot stays in position without a motion gap.
                if args.hold_last_action and last_action is not None:
                    action = last_action
                else:
                    time.sleep(0.005)
                    continue
            actuator_commands_sent = True
            last_action = action
            hard_ok, soft_ok, result = execute_one_action(
                action,
                motor_io=motor_io,
                selected_features=selected_features,
                args=args,
                logger=logger,
                step_index=step_index,
            )
            stats["actions_executed"] += 1
            stats["clipped_features"] += int(result.get("clipped_features", 0))
            stats["gripper_saturated_features"] += int(result.get("gripper_saturated_features", 0))
            stats["joint4_saturated_features"] += int(result.get("joint4_saturated_features", 0))
            stats["joint_limit_saturated_features"] += int(result.get("joint_limit_saturated_features", 0))
            stats["soft_warnings"] += len(result.get("soft_warnings", []))
            if result.get("per_joint"):
                max_readback = float(result["max_abs_readback_error_deg"])
                previous_readback = stats["max_abs_readback_error_deg"]
                stats["max_abs_readback_error_deg"] = (
                    max_readback if previous_readback is None else max(previous_readback, max_readback)
                )
                max_commanded = float(result["max_abs_commanded_delta_deg"])
                previous_commanded = stats["max_abs_commanded_delta_deg"]
                stats["max_abs_commanded_delta_deg"] = (
                    max_commanded if previous_commanded is None else max(previous_commanded, max_commanded)
                )
            if not hard_ok:
                stats["hard_readback_streak"] += 1
                if stats["hard_readback_streak"] >= int(args.max_repeated_hard_readback):
                    shared["stop_reason"] = f"hard_readback_repeated: {result.get('hard_errors')}"
                    stop_event.set()
                    motion_status = "BLOCKED_FOR_REVIEW"
                    exit_code = 2
                    break
            else:
                stats["hard_readback_streak"] = 0
                if not soft_ok:
                    motion_status = "PAUSED_SOFT_REVIEW"
                else:
                    motion_status = "ROLLOUT_SESSION_ACTIVE"
            step_index += 1
        worker.join(timeout=5.0)
    except Exception as exc:
        shared["stop_reason"] = f"exception: {exc!r}"
        logger.write("hard_block", reason=shared["stop_reason"])
        motion_status = "BLOCKED_FOR_REVIEW"
        exit_code = 2
    finally:
        try:
            cleanup_errors = motor_io.disconnect()
        finally:
            cameras.stop()
            remaining_torque_enabled = {
                side: sorted(motors, key=lambda motor: MOTOR_INDEX[motor])
                for side, motors in motor_io.torque_enabled.items()
                if motors
            }
            if cleanup_errors:
                logger.write("cleanup_errors", cleanup_errors=cleanup_errors)
                if args.execute:
                    motion_status = "BLOCKED_FOR_REVIEW"
            stats["chunks_accepted"] = action_queue.chunks_accepted
            summary = {
                "schema": "openarm_folding_live_rollout_summary_v1",
                "timestamp": time.strftime("%Y%m%d_%H%M%S"),
                "hostname": socket.gethostname(),
                "trial_root": str(args.trial_root),
                "session_root": str(session_root),
                "selected_scope": args.selected_scope,
                "selected_features": selected_features,
                "excluded_features": excluded_features,
                "execute_requested": bool(args.execute),
                "actuator_commands_sent": actuator_commands_sent,
                "motion_status": motion_status,
                "stop_reason": shared.get("stop_reason") or "completed",
                "safety_mode": "monitor_only_operator_visual_power_gate"
                if args.safety_monitor_only
                else "software_pause_block_enabled",
                "software_safety_measurements_blocking": not bool(args.safety_monitor_only),
                "startup_soft_warnings": soft_warnings,
                "cleanup_errors": cleanup_errors,
                "remaining_torque_enabled_motors": remaining_torque_enabled,
                "torque_disable_complete": not cleanup_errors and not remaining_torque_enabled,
                "stats": stats,
                "events": str(events_path),
                "command_path": "DamiaoMotorsBus guarded MIT batch" if actuator_commands_sent else "not_run",
                "forbidden_paths": {
                    "send_action": True,
                    "lerobot_rollout_actual": True,
                    "openarm_follower_connect_actual": True,
                },
            }
            write_summary(summary_path, summary)
            logger.write("summary", **summary)
            logger.close()
            print(json.dumps(summary, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
