#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audits.openarm_folding import stage37_guarded_served_proposal_write as shared


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
RIGHT_ARM_FEATURES = [
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
]
LEFT_ARM_FEATURES = [
    "left_joint_1.pos",
    "left_joint_2.pos",
    "left_joint_3.pos",
    "left_joint_4.pos",
    "left_joint_5.pos",
    "left_joint_6.pos",
    "left_joint_7.pos",
]
GRIPPER_FEATURES = ["right_gripper.pos", "left_gripper.pos"]
FULL_16_FEATURES = ACTION_NAMES.copy()
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
SELECTED_SCOPE_FEATURES = {
    "right-arm": RIGHT_ARM_FEATURES,
    "both-arms": RIGHT_ARM_FEATURES + LEFT_ARM_FEATURES,
    "full-16": FULL_16_FEATURES,
}
ROBOT_CONFIG_ID = "openarms_follower:16d:3cam:v1"
ACTION_SPACE_VERSION = "openarm_folding_abs_16d_deg_v1"
ACTION_UNITS = "degrees"
STATE_FRESHNESS_TTL_S = 5.0
READBACK_SOFT_ERROR_DEG = 1.0
READBACK_HARD_ERROR_DEG = 2.0
MAX_TOTAL_JOINT_DELTA_DEG = 30.0

RISK_LEVELS = {
    0: {"name": "no_execute_only", "max_actions": 0, "max_duration_s": 0.0, "cap_deg": 0.0, "interpolate": False},
    1: {"name": "micro", "max_actions": 3, "max_duration_s": 2.0, "cap_deg": 2.0, "interpolate": False},
    2: {"name": "short", "max_actions": 10, "max_duration_s": 5.0, "cap_deg": 4.0, "interpolate": True},
    3: {"name": "chunk", "max_actions": 30, "max_duration_s": 10.0, "cap_deg": 6.0, "interpolate": True},
    4: {"name": "bounded_session", "max_actions": 30, "max_duration_s": 10.0, "cap_deg": 8.0, "interpolate": True},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def trial_id_from_root(path: Path) -> str:
    return path.name


def approval_phrase(trial_id: str) -> str:
    normalized = trial_id.upper().replace("-", "_")
    return f"APPROVE_ROLLOUT_SESSION_{normalized}"


def selected_features_for_scope(scope: str) -> list[str]:
    return SELECTED_SCOPE_FEATURES[scope].copy()


def excluded_features_for(selected_features: list[str]) -> list[str]:
    selected = set(selected_features)
    return [key for key in ACTION_NAMES if key not in selected]


def make_bus(port: str):
    return shared.make_right_bus(port)


def read_features_from_bus(port: str, features: list[str]) -> dict[str, float]:
    if not features:
        return {}
    motors = [FEATURE_TO_MOTOR[key] for key in features]
    bus = make_bus(port)
    bus.connect(handshake=False)
    try:
        states = shared.read_selected(bus, motors)
        return {key: float(states[FEATURE_TO_MOTOR[key]]) for key in features}
    finally:
        bus.disconnect(disable_torque=False)


def read_fresh_current(
    path: Path | None,
    *,
    right_port: str,
    left_port: str,
    selected_features: list[str],
) -> dict[str, float]:
    if path is not None:
        data = load_json(path)
        if "fresh_current_deg" in data:
            data = data["fresh_current_deg"]
        result = {}
        for key in selected_features:
            motor = FEATURE_TO_MOTOR[key]
            side_motor = f"{FEATURE_SIDE[key]}.{motor}"
            if key in data:
                result[key] = float(data[key])
            elif side_motor in data:
                result[key] = float(data[side_motor])
            elif motor in data:
                result[key] = float(data[motor])
            else:
                raise KeyError(f"fresh-current JSON missing {key}/{side_motor}/{motor}")
        return result
    result: dict[str, float] = {}
    right_features = [key for key in selected_features if FEATURE_SIDE[key] == "right"]
    left_features = [key for key in selected_features if FEATURE_SIDE[key] == "left"]
    result.update(read_features_from_bus(right_port, right_features))
    result.update(read_features_from_bus(left_port, left_features))
    return result


def proposal_payload(path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    payload = load_json(path)
    proposal = payload.get("proposal", payload)
    return payload, proposal, sha256(path)


def chunk_array(proposal: dict[str, Any]) -> list[list[float]]:
    chunk = proposal.get("predicted_abs_action_chunk")
    if not isinstance(chunk, list) or len(chunk) != 1 or not isinstance(chunk[0], list):
        raise ValueError("proposal missing predicted_abs_action_chunk with batch size 1")
    actions = chunk[0]
    if len(actions) != 30:
        raise ValueError(f"expected 30 action steps, got {len(actions)}")
    for idx, action in enumerate(actions):
        if not isinstance(action, list) or len(action) != 16:
            raise ValueError(f"action step {idx} must be 16D")
        for value in action:
            if not math.isfinite(float(value)):
                raise ValueError(f"non-finite action at step {idx}")
    return [[float(value) for value in action] for action in actions]


def validate_proposal_metadata(
    client_payload: dict[str, Any],
    proposal: dict[str, Any],
    *,
    expected_obs_id: str | None,
    excluded_features: list[str],
) -> list[str]:
    errors: list[str] = []
    request = client_payload.get("request", {})
    require(client_payload.get("schema") == "openarm_folding_remote_proposal_client_result_v1", "unexpected client schema", errors)
    require(proposal.get("schema") == "openarm_folding_action_proposal_v1", "unexpected proposal schema", errors)
    require(proposal.get("action_shape") == [1, 30, 16], f"unexpected action_shape={proposal.get('action_shape')}", errors)
    require(proposal.get("all_finite") is True, "proposal all_finite is not true", errors)
    require(proposal.get("send_allowed") is False, "proposal send_allowed is not false", errors)
    require(proposal.get("motion_allowed") is False, "proposal motion_allowed is not false", errors)
    require(proposal.get("actuator_commands_sent") is False, "proposal actuator_commands_sent is not false", errors)
    if expected_obs_id is not None:
        require(proposal.get("obs_id") == expected_obs_id, f"unexpected obs_id={proposal.get('obs_id')!r}", errors)
    if request.get("obs_id") is not None:
        require(proposal.get("obs_id") == request.get("obs_id"), "proposal obs_id does not match request obs_id", errors)
    if request.get("snapshot_checksum") is not None:
        require(
            proposal.get("snapshot_checksum") == request.get("snapshot_checksum"),
            "proposal snapshot_checksum does not match request snapshot_checksum",
            errors,
        )
    require(proposal.get("robot_config_id") == ROBOT_CONFIG_ID, f"unexpected robot_config_id={proposal.get('robot_config_id')!r}", errors)
    require(proposal.get("checkpoint_id") is not None, "missing checkpoint_id", errors)
    require(proposal.get("action_normalization_id") is not None, "missing action_normalization_id", errors)
    require(proposal.get("joint_order") == ACTION_NAMES, "joint_order mismatch", errors)
    require(proposal.get("action_units") == ACTION_UNITS, f"unexpected action_units={proposal.get('action_units')!r}", errors)
    require(proposal.get("action_space_version") == ACTION_SPACE_VERSION, "action_space_version mismatch", errors)
    require(proposal.get("is_absolute_action") is True, "proposal is_absolute_action is not true", errors)
    rows = proposal.get("rows", [])
    for row in rows:
        if row.get("key") in excluded_features:
            require(row.get("send_allowed") is False, f"excluded row send_allowed true: {row.get('key')}", errors)
    return errors


def default_envelope(
    trial_id: str,
    proposal: dict[str, Any],
    *,
    selected_features: list[str],
    max_chunks: int = 3,
) -> dict[str, Any]:
    includes_left = any(FEATURE_SIDE[key] == "left" for key in selected_features)
    includes_gripper = any(key in GRIPPER_FEATURES for key in selected_features)
    return {
        "schema": "openarm_folding_rollout_session_envelope_v1",
        "rollout_trial_id": trial_id,
        "approval_phrase": approval_phrase(trial_id),
        "model_id": proposal.get("model_id"),
        "checkpoint_id": proposal.get("checkpoint_id"),
        "robot_config_id": proposal.get("robot_config_id"),
        "action_normalization_id": proposal.get("action_normalization_id"),
        "action_space_version": proposal.get("action_space_version"),
        "joint_order": proposal.get("joint_order"),
        "action_units": proposal.get("action_units"),
        "is_absolute_action": proposal.get("is_absolute_action"),
        "selected_features": selected_features,
        "max_risk_level": 4,
        "max_session_duration_s": 60.0,
        "max_chunks": max_chunks,
        "max_actions_per_chunk": 30,
        "max_per_step_delta_cap_deg": 8.0,
        "optional_hard_ceiling_delta_cap_deg": 10.0,
        "max_total_joint_delta_per_session_deg": MAX_TOTAL_JOINT_DELTA_DEG,
        "readback_soft_error_deg": READBACK_SOFT_ERROR_DEG,
        "readback_hard_error_deg": READBACK_HARD_ERROR_DEG,
        "forbid_left_arm": not includes_left,
        "forbid_gripper": not includes_gripper,
        "forbid_send_action_path": True,
        "forbid_lerobot_rollout_actual_path": True,
        "forbid_openarm_follower_connect_actual_path": True,
        "actuator_path": "DamiaoMotorsBus guarded MIT batch",
    }


def validate_envelope(
    envelope: dict[str, Any],
    proposal: dict[str, Any],
    *,
    trial_id: str,
    risk_level: int,
    chunk_index: int,
    selected_features: list[str],
) -> list[str]:
    errors: list[str] = []
    level = RISK_LEVELS[risk_level]
    require(envelope.get("schema") == "openarm_folding_rollout_session_envelope_v1", "unexpected envelope schema", errors)
    require(envelope.get("rollout_trial_id") == trial_id, "envelope trial id mismatch", errors)
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
        require(envelope.get(key) == proposal.get(key), f"envelope {key} mismatch", errors)
    require(envelope.get("selected_features") == selected_features, "envelope selected_features mismatch", errors)
    require(int(envelope.get("max_risk_level", -1)) >= risk_level, "risk level exceeds envelope", errors)
    require(int(envelope.get("max_chunks", -1)) > chunk_index, "chunk index exceeds envelope", errors)
    require(int(envelope.get("max_actions_per_chunk", -1)) >= int(level["max_actions"]), "max_actions exceeds envelope", errors)
    require(float(envelope.get("max_per_step_delta_cap_deg", -1.0)) >= float(level["cap_deg"]), "per-step cap exceeds envelope", errors)
    if any(FEATURE_SIDE[key] == "left" for key in selected_features):
        require(envelope.get("forbid_left_arm") is False, "left arm is selected but forbidden by envelope", errors)
    else:
        require(envelope.get("forbid_left_arm") is True, "left arm is not forbidden by envelope", errors)
    if any(key in GRIPPER_FEATURES for key in selected_features):
        require(envelope.get("forbid_gripper") is False, "gripper is selected but forbidden by envelope", errors)
    else:
        require(envelope.get("forbid_gripper") is True, "gripper is not forbidden by envelope", errors)
    require(envelope.get("forbid_send_action_path") is True, "send_action path is not forbidden by envelope", errors)
    require(envelope.get("forbid_lerobot_rollout_actual_path") is True, "lerobot rollout path is not forbidden by envelope", errors)
    require(envelope.get("forbid_openarm_follower_connect_actual_path") is True, "OpenArm follower path is not forbidden by envelope", errors)
    return errors


def validate_runtime_envelope(envelope: dict[str, Any], args: argparse.Namespace) -> list[str]:
    errors: list[str] = []
    if "clip_to_delta_cap" in envelope:
        require(bool(envelope["clip_to_delta_cap"]) == bool(args.clip_to_delta_cap), "clip_to_delta_cap mismatch", errors)
    if "allow_gripper_limit_saturation" in envelope:
        require(
            bool(envelope["allow_gripper_limit_saturation"]) == bool(args.allow_gripper_limit_saturation),
            "allow_gripper_limit_saturation mismatch",
            errors,
        )
    for key, value in [
        ("arm_delta_cap_deg", args.arm_delta_cap_deg),
        ("gripper_delta_cap_deg", args.gripper_delta_cap_deg),
        ("arm_readback_soft_error_deg", args.arm_readback_soft_error_deg),
        ("arm_readback_hard_error_deg", args.arm_readback_hard_error_deg),
        ("gripper_readback_soft_error_deg", args.gripper_readback_soft_error_deg),
        ("gripper_readback_hard_error_deg", args.gripper_readback_hard_error_deg),
    ]:
        if key in envelope:
            require(value is not None, f"{key} is required by envelope", errors)
            if value is not None:
                require(abs(float(envelope[key]) - float(value)) <= 1e-6, f"{key} mismatch", errors)
    return errors


def within_limits(key: str, value: float) -> bool:
    lo, hi = FEATURE_LIMITS[key]
    return lo <= value <= hi


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def feature_delta_cap(
    key: str,
    *,
    base_cap_deg: float,
    arm_delta_cap_deg: float | None,
    gripper_delta_cap_deg: float | None,
) -> float:
    if key in GRIPPER_FEATURES and gripper_delta_cap_deg is not None:
        return gripper_delta_cap_deg
    if key not in GRIPPER_FEATURES and arm_delta_cap_deg is not None:
        return arm_delta_cap_deg
    return base_cap_deg


def feature_readback_threshold(
    key: str,
    *,
    default_deg: float,
    arm_deg: float | None,
    gripper_deg: float | None,
) -> float:
    if key in GRIPPER_FEATURES and gripper_deg is not None:
        return gripper_deg
    if key not in GRIPPER_FEATURES and arm_deg is not None:
        return arm_deg
    return default_deg


def make_step(
    *,
    step_id: int,
    model_action_index: int,
    previous: dict[str, float],
    target: dict[str, float],
    cap_deg: float,
    feature_caps: dict[str, float],
    derived: bool,
    selected_features: list[str],
    limit_saturated_features: list[str] | None = None,
) -> dict[str, Any]:
    rows = []
    for key in selected_features:
        delta = target[key] - previous[key]
        feature_cap = feature_caps[key]
        lo, hi = FEATURE_LIMITS[key]
        rows.append(
            {
                "key": key,
                "side": FEATURE_SIDE[key],
                "motor": FEATURE_TO_MOTOR[key],
                "previous_deg": previous[key],
                "target_deg": target[key],
                "delta_deg": delta,
                "delta_cap_deg": feature_cap,
                "limit_min_deg": lo,
                "limit_max_deg": hi,
                "within_delta_cap": abs(delta) <= feature_cap + 1e-6,
                "within_joint_limits": lo <= target[key] <= hi,
            }
        )
    return {
        "step_id": step_id,
        "model_action_index": model_action_index,
        "derived_from_model_action": derived,
        "limit_saturated_features": limit_saturated_features or [],
        "cap_deg": cap_deg,
        "rows": rows,
    }


def build_plan(
    actions: list[list[float]],
    fresh_current: dict[str, float],
    *,
    risk_level: int,
    envelope: dict[str, Any] | None,
    selected_features: list[str],
    clip_to_delta_cap: bool,
    allow_gripper_limit_saturation: bool,
    arm_delta_cap_deg: float | None,
    gripper_delta_cap_deg: float | None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    level = RISK_LEVELS[risk_level]
    cap_deg = float(level["cap_deg"])
    if risk_level == 0:
        return [], [], []
    max_commands = int(level["max_actions"])
    if envelope is not None:
        max_commands = min(max_commands, int(envelope.get("max_actions_per_chunk", max_commands)))
        cap_deg = min(cap_deg, float(envelope.get("max_per_step_delta_cap_deg", cap_deg)))
    feature_caps = {
        key: feature_delta_cap(
            key,
            base_cap_deg=cap_deg,
            arm_delta_cap_deg=arm_delta_cap_deg,
            gripper_delta_cap_deg=gripper_delta_cap_deg,
        )
        for key in selected_features
    }
    previous = {key: float(fresh_current[key]) for key in selected_features}
    session_start = previous.copy()
    plan: list[dict[str, Any]] = []
    for model_idx, action in enumerate(actions):
        target = {key: float(action[ACTION_NAMES.index(key)]) for key in selected_features}
        limit_saturated_features: list[str] = []
        if allow_gripper_limit_saturation:
            for key in selected_features:
                if key not in GRIPPER_FEATURES:
                    continue
                lo, hi = FEATURE_LIMITS[key]
                saturated = clamp(target[key], lo, hi)
                if saturated != target[key]:
                    target[key] = saturated
                    limit_saturated_features.append(key)
        deltas = {key: target[key] - previous[key] for key in selected_features}
        max_cap_ratio = max(abs(deltas[key]) / feature_caps[key] for key in selected_features if feature_caps[key] > 0)
        max_abs_delta = max(abs(value) for value in deltas.values())
        if max_cap_ratio <= 1.0 + 1e-6:
            invalid_limits = [key for key, value in target.items() if not within_limits(key, value)]
            if invalid_limits:
                hard_errors.append(f"joint limit violation at model action {model_idx}: {invalid_limits}")
                break
            if len(plan) >= max_commands:
                break
            plan.append(
                make_step(
                    step_id=len(plan),
                    model_action_index=model_idx,
                    previous=previous,
                    target=target,
                    cap_deg=cap_deg,
                    feature_caps=feature_caps,
                    derived=bool(limit_saturated_features),
                    selected_features=selected_features,
                    limit_saturated_features=limit_saturated_features,
                )
            )
            previous = target
        elif clip_to_delta_cap:
            invalid_limits = [key for key, value in target.items() if not within_limits(key, value)]
            if invalid_limits:
                hard_errors.append(f"joint limit violation at model action {model_idx}: {invalid_limits}")
                break
            if len(plan) >= max_commands:
                break
            clipped_target = {}
            for key in selected_features:
                lo, hi = FEATURE_LIMITS[key]
                clipped_delta = clamp(deltas[key], -feature_caps[key], feature_caps[key])
                clipped_target[key] = clamp(previous[key] + clipped_delta, lo, hi)
            plan.append(
                make_step(
                    step_id=len(plan),
                    model_action_index=model_idx,
                    previous=previous,
                    target=clipped_target,
                    cap_deg=cap_deg,
                    feature_caps=feature_caps,
                    derived=True,
                    selected_features=selected_features,
                    limit_saturated_features=limit_saturated_features,
                )
            )
            previous = clipped_target
        elif bool(level["interpolate"]):
            invalid_limits = [key for key, value in target.items() if not within_limits(key, value)]
            if invalid_limits:
                hard_errors.append(f"joint limit violation at model action {model_idx}: {invalid_limits}")
                break
            segments = max(2, math.ceil(max_cap_ratio))
            for segment in range(1, segments + 1):
                if len(plan) >= max_commands:
                    soft_warnings.append(f"interpolation truncated at action budget before model action {model_idx}")
                    break
                ratio = segment / segments
                interpolated = {key: previous[key] + deltas[key] * ratio for key in selected_features}
                plan.append(
                    make_step(
                        step_id=len(plan),
                        model_action_index=model_idx,
                        previous={key: previous[key] + deltas[key] * ((segment - 1) / segments) for key in selected_features},
                        target=interpolated,
                        cap_deg=cap_deg,
                        feature_caps=feature_caps,
                        derived=True,
                        selected_features=selected_features,
                        limit_saturated_features=limit_saturated_features,
                    )
                )
            previous = target if len(plan) < max_commands else {
                key: plan[-1]["rows"][idx]["target_deg"] for idx, key in enumerate(selected_features)
            }
        else:
            soft_warnings.append(f"per-step cap exceeded at level {risk_level} model action {model_idx}: {max_abs_delta:.6f} deg")
            break
        total_delta = {key: abs(previous[key] - session_start[key]) for key in selected_features}
        max_total = float(envelope.get("max_total_joint_delta_per_session_deg", MAX_TOTAL_JOINT_DELTA_DEG)) if envelope else MAX_TOTAL_JOINT_DELTA_DEG
        if max(total_delta.values()) > max_total + 1e-6:
            hard_errors.append(f"max total joint delta exceeded: {max(total_delta.values()):.6f} deg")
            break
        if len(plan) >= max_commands:
            break
    return plan, hard_errors, soft_warnings


def build_commands_by_side(
    step: dict[str, Any],
    *,
    right_port: str,
    left_port: str,
) -> dict[str, dict[str, tuple[float, float, float, float, float]]]:
    from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase

    configs = {
        "right": OpenArmFollowerConfigBase(port=right_port, side="right"),
        "left": OpenArmFollowerConfigBase(port=left_port, side="left"),
    }
    commands: dict[str, dict[str, tuple[float, float, float, float, float]]] = {"right": {}, "left": {}}
    for row in step["rows"]:
        side = str(row["side"])
        motor = str(row["motor"])
        idx = shared.MOTOR_INDEX[motor]
        config = configs[side]
        kp = config.position_kp[idx] if isinstance(config.position_kp, list) else config.position_kp
        kd = config.position_kd[idx] if isinstance(config.position_kd, list) else config.position_kd
        commands[side][motor] = (float(kp), float(kd), float(row["target_deg"]), 0.0, 0.0)
    return commands


def check_health(url: str, timeout_s: float) -> tuple[bool, dict[str, Any] | str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
        ok = (
            payload.get("status") == "ok"
            and payload.get("send_allowed") is False
            and payload.get("motion_allowed") is False
        )
        return ok, payload
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, repr(exc)


def summarize_readback(
    readbacks: list[dict[str, Any]],
    *,
    soft_threshold: float,
    hard_threshold: float,
) -> tuple[list[str], list[str]]:
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    hard_streak = 0
    for item in readbacks:
        max_error = float(item["max_abs_error_deg"])
        if max_error > hard_threshold:
            hard_streak += 1
            if hard_streak >= 2:
                hard_errors.append(f"repeated hard readback error: {max_error:.6f} deg")
        else:
            hard_streak = 0
        if max_error > soft_threshold:
            soft_warnings.append(f"soft readback warning at step {item['step_id']}: {max_error:.6f} deg")
    return hard_errors, soft_warnings


def build_metrics(
    planned_steps: list[dict[str, Any]],
    readbacks: list[dict[str, Any]],
    *,
    selected_features: list[str],
) -> dict[str, Any]:
    commanded: dict[str, list[float]] = {key: [] for key in selected_features}
    errors: dict[str, list[float]] = {key: [] for key in selected_features}
    for step in planned_steps:
        for row in step["rows"]:
            commanded[row["key"]].append(abs(float(row["delta_deg"])))
    for readback in readbacks:
        for key, item in readback["per_joint"].items():
            errors[key].append(abs(float(item["error_deg"])))
    return {
        "max_commanded_delta_per_joint_deg": {
            key: max(values) if values else None for key, values in commanded.items()
        },
        "max_readback_error_per_joint_deg": {
            key: max(values) if values else None for key, values in errors.items()
        },
        "mean_readback_error_per_joint_deg": {
            key: (sum(values) / len(values)) if values else None for key, values in errors.items()
        },
        "max_abs_commanded_delta_deg": max(
            (value for values in commanded.values() for value in values),
            default=None,
        ),
        "max_abs_readback_error_deg": max(
            (value for values in errors.values() for value in values),
            default=None,
        ),
    }


def execute_plan(
    plan: list[dict[str, Any]],
    *,
    right_port: str,
    left_port: str,
    action_period_s: float,
    selected_features: list[str],
    readback_soft_error_deg: float,
    readback_hard_error_deg: float,
    arm_readback_soft_error_deg: float | None,
    arm_readback_hard_error_deg: float | None,
    gripper_readback_soft_error_deg: float | None,
    gripper_readback_hard_error_deg: float | None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    selected_by_side = {
        "right": [key for key in selected_features if FEATURE_SIDE[key] == "right"],
        "left": [key for key in selected_features if FEATURE_SIDE[key] == "left"],
    }
    selected_motors = {
        side: [FEATURE_TO_MOTOR[key] for key in features] for side, features in selected_by_side.items()
    }
    buses = {
        side: make_bus(port)
        for side, port in {"right": right_port, "left": left_port}.items()
        if selected_by_side[side]
    }
    readbacks: list[dict[str, Any]] = []
    hard_errors: list[str] = []
    soft_warnings: list[str] = []
    hard_streak = 0
    torque_enabled: set[str] = set()
    connected: set[str] = set()
    try:
        for side, bus in buses.items():
            bus.connect(handshake=False)
            connected.add(side)
            bus.enable_torque(selected_motors[side])
            torque_enabled.add(side)
        for step in plan:
            commands = build_commands_by_side(step, right_port=right_port, left_port=left_port)
            for side, bus in buses.items():
                if commands[side]:
                    bus._mit_control_batch(commands[side])
            time.sleep(action_period_s)
            current_by_feature: dict[str, float] = {}
            for side, bus in buses.items():
                current = shared.read_selected(bus, selected_motors[side])
                for key in selected_by_side[side]:
                    current_by_feature[key] = float(current[FEATURE_TO_MOTOR[key]])
            per_joint = {}
            for row in step["rows"]:
                key = row["key"]
                error = float(current_by_feature[key]) - float(row["target_deg"])
                soft_threshold = feature_readback_threshold(
                    key,
                    default_deg=readback_soft_error_deg,
                    arm_deg=arm_readback_soft_error_deg,
                    gripper_deg=gripper_readback_soft_error_deg,
                )
                hard_threshold = feature_readback_threshold(
                    key,
                    default_deg=readback_hard_error_deg,
                    arm_deg=arm_readback_hard_error_deg,
                    gripper_deg=gripper_readback_hard_error_deg,
                )
                per_joint[row["key"]] = {
                    "readback_deg": float(current_by_feature[key]),
                    "target_deg": float(row["target_deg"]),
                    "error_deg": error,
                    "soft_threshold_deg": soft_threshold,
                    "hard_threshold_deg": hard_threshold,
                }
            max_abs_error = max(abs(item["error_deg"]) for item in per_joint.values())
            soft_exceeded = [
                {"key": key, "abs_error_deg": abs(item["error_deg"]), "threshold_deg": item["soft_threshold_deg"]}
                for key, item in per_joint.items()
                if abs(item["error_deg"]) > float(item["soft_threshold_deg"])
            ]
            hard_exceeded = [
                {"key": key, "abs_error_deg": abs(item["error_deg"]), "threshold_deg": item["hard_threshold_deg"]}
                for key, item in per_joint.items()
                if abs(item["error_deg"]) > float(item["hard_threshold_deg"])
            ]
            readback = {
                "step_id": step["step_id"],
                "model_action_index": step["model_action_index"],
                "derived_from_model_action": step["derived_from_model_action"],
                "per_joint": per_joint,
                "max_abs_error_deg": max_abs_error,
                "soft_threshold_exceeded": soft_exceeded,
                "hard_threshold_exceeded": hard_exceeded,
            }
            readbacks.append(readback)
            if soft_exceeded:
                worst = max(soft_exceeded, key=lambda item: item["abs_error_deg"] - item["threshold_deg"])
                soft_warnings.append(
                    f"soft readback warning at step {step['step_id']}: "
                    f"{worst['key']} {worst['abs_error_deg']:.6f} deg > {worst['threshold_deg']:.6f} deg"
                )
            if hard_exceeded:
                hard_streak += 1
                if hard_streak >= 2:
                    worst = max(hard_exceeded, key=lambda item: item["abs_error_deg"] - item["threshold_deg"])
                    hard_errors.append(
                        f"repeated hard readback error at step {step['step_id']}: "
                        f"{worst['key']} {worst['abs_error_deg']:.6f} deg > {worst['threshold_deg']:.6f} deg"
                    )
                    readback["abort_after_step"] = True
                    break
            else:
                hard_streak = 0
        for side, bus in buses.items():
            bus.disable_torque(selected_motors[side], num_retry=2)
            torque_enabled.discard(side)
        return readbacks, hard_errors, soft_warnings
    finally:
        for side, bus in buses.items():
            if side in connected and side in torque_enabled:
                bus.disable_torque(selected_motors[side], num_retry=2)
            if side in connected:
                bus.disconnect(disable_torque=False)


def write_approval_draft(json_path: Path | None, md_path: Path | None, envelope: dict[str, Any]) -> None:
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    if md_path is not None:
        selected_features = envelope.get("selected_features", [])
        clearance_lines = [
            "right_arm_workspace_clear: true",
        ]
        if any(FEATURE_SIDE[key] == "left" for key in selected_features):
            clearance_lines.append("left_arm_workspace_clear: true")
        if any(key in GRIPPER_FEATURES for key in selected_features):
            clearance_lines.append("gripper_workspace_clear: true")
        clearance_lines.append("human_body_clear_of_arm: true")
        lines = [
            "# Rollout Trial Session Envelope Approval Draft",
            "",
            "This is a draft only. It is not approval.",
            "",
            "## Required Confirmation",
            "",
            "```text",
            "operator_at_robot: true",
            "power_abort_control_held: true",
            "estop_ready: true",
            *clearance_lines,
            "approval_applies_to_rollout_session_envelope: true",
            f"approval_phrase: {envelope['approval_phrase']}",
            "```",
            "",
            "## Envelope",
            "",
            "```json",
            json.dumps(envelope, indent=2, sort_keys=True),
            "```",
        ]
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("\n".join(lines) + "\n")


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Rollout Trial Guarded Session Chunk",
        "",
        "## Status",
        "",
        f"- Trial: `{payload['rollout_trial_id']}`",
        f"- Chunk index: `{payload['chunk_index']}`",
        f"- Risk level: `{payload['risk_level']}`",
        f"- Execute requested: `{payload['execute_requested']}`",
        f"- Motion status: `{payload['motion_status']}`",
        f"- Hard errors: `{len(payload['hard_errors'])}`",
        f"- Soft warnings: `{len(payload['soft_warnings'])}`",
        f"- Planned command steps: `{len(payload['planned_steps'])}`",
        f"- Actuator commands sent: `{payload['actuator_commands_sent']}`",
        f"- Max commanded delta deg: `{payload['metrics']['max_abs_commanded_delta_deg']}`",
        f"- Max readback error deg: `{payload['metrics']['max_abs_readback_error_deg']}`",
        "",
        "## Planned Steps",
        "",
        "| Step | Model action | Derived | Max abs delta deg |",
        "| ---: | ---: | --- | ---: |",
    ]
    for step in payload["planned_steps"]:
        max_delta = max(abs(row["delta_deg"]) for row in step["rows"])
        lines.append(
            f"| {step['step_id']} | {step['model_action_index']} | `{step['derived_from_model_action']}` | {max_delta:.6f} |"
        )
    if payload["hard_errors"]:
        lines.extend(["", "## Hard Errors", ""])
        lines.extend(f"- `{error}`" for error in payload["hard_errors"])
    if payload["soft_warnings"]:
        lines.extend(["", "## Soft Warnings", ""])
        lines.extend(f"- `{warning}`" for warning in payload["soft_warnings"])
    lines.extend(["", "## Boundary", ""])
    lines.append("Only selected envelope features may be commanded; LeRobot rollout/send_action paths are forbidden.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded progressive right-arm-only rollout trial chunk.")
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument("--proposal-json", type=Path, required=True)
    parser.add_argument("--chunk-index", type=int, default=0)
    parser.add_argument("--risk-level", type=int, default=1, choices=sorted(RISK_LEVELS))
    parser.add_argument("--expected-obs-id")
    parser.add_argument("--session-envelope-json", type=Path)
    parser.add_argument("--approval-draft-json", type=Path)
    parser.add_argument("--approval-draft-md", type=Path)
    parser.add_argument("--fresh-current-json", type=Path)
    parser.add_argument("--right-port", default="can1")
    parser.add_argument("--left-port", default="can0")
    parser.add_argument("--selected-scope", choices=sorted(SELECTED_SCOPE_FEATURES), default="right-arm")
    parser.add_argument("--action-period-s", type=float, default=0.25)
    parser.add_argument("--health-url")
    parser.add_argument("--health-timeout-s", type=float, default=10.0)
    parser.add_argument("--readback-soft-error-deg", type=float)
    parser.add_argument("--readback-hard-error-deg", type=float)
    parser.add_argument("--arm-readback-soft-error-deg", type=float)
    parser.add_argument("--arm-readback-hard-error-deg", type=float)
    parser.add_argument("--gripper-readback-soft-error-deg", type=float)
    parser.add_argument("--gripper-readback-hard-error-deg", type=float)
    parser.add_argument("--clip-to-delta-cap", action="store_true")
    parser.add_argument("--allow-gripper-limit-saturation", action="store_true")
    parser.add_argument("--arm-delta-cap-deg", type=float)
    parser.add_argument("--gripper-delta-cap-deg", type=float)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
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
    parser.add_argument("--operator-stop-file", type=Path)
    parser.add_argument("--confirm", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    trial_id = trial_id_from_root(args.trial_root)
    selected_features = selected_features_for_scope(args.selected_scope)
    excluded_features = excluded_features_for(selected_features)
    client_payload, proposal, proposal_digest = proposal_payload(args.proposal_json)
    hard_errors = validate_proposal_metadata(
        client_payload,
        proposal,
        expected_obs_id=args.expected_obs_id,
        excluded_features=excluded_features,
    )
    soft_warnings: list[str] = []
    try:
        actions = chunk_array(proposal)
    except Exception as exc:
        actions = []
        hard_errors.append(repr(exc))

    envelope = load_json(args.session_envelope_json) if args.session_envelope_json else None
    readback_soft_error_deg = (
        float(args.readback_soft_error_deg)
        if args.readback_soft_error_deg is not None
        else float(envelope.get("readback_soft_error_deg", READBACK_SOFT_ERROR_DEG)) if envelope else READBACK_SOFT_ERROR_DEG
    )
    readback_hard_error_deg = (
        float(args.readback_hard_error_deg)
        if args.readback_hard_error_deg is not None
        else float(envelope.get("readback_hard_error_deg", READBACK_HARD_ERROR_DEG)) if envelope else READBACK_HARD_ERROR_DEG
    )
    draft = default_envelope(trial_id, proposal, selected_features=selected_features)
    write_approval_draft(args.approval_draft_json, args.approval_draft_md, draft)
    if envelope is not None:
        hard_errors.extend(
            validate_envelope(
                envelope,
                proposal,
                trial_id=trial_id,
                risk_level=args.risk_level,
                chunk_index=args.chunk_index,
                selected_features=selected_features,
            )
        )
        hard_errors.extend(validate_runtime_envelope(envelope, args))

    if args.execute:
        require(envelope is not None, "--session-envelope-json is required with --execute", hard_errors)
        require(args.operator_session_approval_given, "--operator-session-approval-given is required", hard_errors)
        require(args.operator_at_robot, "--operator-at-robot is required", hard_errors)
        require(args.power_held, "--power-held is required", hard_errors)
        require(args.abort_ready, "--abort-ready is required", hard_errors)
        require(args.estop_ready, "--estop-ready is required", hard_errors)
        require(args.right_arm_workspace_clear, "--right-arm-workspace-clear is required", hard_errors)
        if any(FEATURE_SIDE[key] == "left" for key in selected_features):
            require(args.left_arm_workspace_clear, "--left-arm-workspace-clear is required", hard_errors)
        if any(key in GRIPPER_FEATURES for key in selected_features):
            require(args.gripper_workspace_clear, "--gripper-workspace-clear is required", hard_errors)
        require(args.human_body_clear_of_arm, "--human-body-clear-of-arm is required", hard_errors)
        require(envelope is not None and args.confirm == envelope.get("approval_phrase"), "approval phrase mismatch", hard_errors)
        if args.operator_stop_file is not None and args.operator_stop_file.exists():
            hard_errors.append("operator stop file exists before execution")

    health_result: dict[str, Any] | str | None = None
    if args.health_url:
        ok, health_result = check_health(args.health_url, args.health_timeout_s)
        if not ok:
            soft_warnings.append(f"A6000 health transient or failure: {health_result!r}")

    read_time = time.time()
    try:
        fresh_current = read_fresh_current(
            args.fresh_current_json,
            right_port=args.right_port,
            left_port=args.left_port,
            selected_features=selected_features,
        )
    except Exception as exc:
        fresh_current = {}
        hard_errors.append(f"fresh motor state read failed: {exc!r}")
    state_age_s = time.time() - read_time
    if state_age_s > STATE_FRESHNESS_TTL_S:
        hard_errors.append(f"fresh state TTL exceeded: {state_age_s:.6f}s")

    planned_steps: list[dict[str, Any]] = []
    if not hard_errors and fresh_current:
        planned_steps, plan_hard, plan_soft = build_plan(
            actions,
            fresh_current,
            risk_level=args.risk_level,
            envelope=envelope,
            selected_features=selected_features,
            clip_to_delta_cap=args.clip_to_delta_cap,
            allow_gripper_limit_saturation=args.allow_gripper_limit_saturation,
            arm_delta_cap_deg=args.arm_delta_cap_deg,
            gripper_delta_cap_deg=args.gripper_delta_cap_deg,
        )
        hard_errors.extend(plan_hard)
        soft_warnings.extend(plan_soft)
    if not planned_steps and args.risk_level > 0 and not hard_errors:
        soft_warnings.append("no command steps selected")
    estimated_duration_s = len(planned_steps) * args.action_period_s
    risk_duration_s = float(RISK_LEVELS[args.risk_level]["max_duration_s"])
    if risk_duration_s > 0 and estimated_duration_s > risk_duration_s + 1e-6:
        soft_warnings.append(
            f"estimated chunk duration exceeds risk level budget: {estimated_duration_s:.6f}s > {risk_duration_s:.6f}s"
        )
    if envelope is not None:
        max_session_duration_s = float(envelope.get("max_session_duration_s", estimated_duration_s))
        if estimated_duration_s > max_session_duration_s + 1e-6:
            hard_errors.append(
                f"estimated chunk duration exceeds session envelope: {estimated_duration_s:.6f}s > {max_session_duration_s:.6f}s"
            )

    readbacks: list[dict[str, Any]] = []
    actuator_commands_sent = False
    motion_status = "BLOCKED_FOR_REVIEW"
    exit_code = 0
    if hard_errors:
        motion_status = "BLOCKED_FOR_REVIEW"
        exit_code = 2
    elif soft_warnings and not args.execute:
        motion_status = "PAUSED_SOFT_REVIEW"
    elif soft_warnings and args.execute:
        motion_status = "PAUSED_SOFT_REVIEW"
    elif args.execute:
        try:
            motion_status = "ROLLOUT_SESSION_ACTIVE"
            readbacks, rb_hard, rb_soft = execute_plan(
                planned_steps,
                right_port=args.right_port,
                left_port=args.left_port,
                action_period_s=args.action_period_s,
                selected_features=selected_features,
                readback_soft_error_deg=readback_soft_error_deg,
                readback_hard_error_deg=readback_hard_error_deg,
                arm_readback_soft_error_deg=args.arm_readback_soft_error_deg,
                arm_readback_hard_error_deg=args.arm_readback_hard_error_deg,
                gripper_readback_soft_error_deg=args.gripper_readback_soft_error_deg,
                gripper_readback_hard_error_deg=args.gripper_readback_hard_error_deg,
            )
            actuator_commands_sent = bool(planned_steps)
            hard_errors.extend(rb_hard)
            soft_warnings.extend(rb_soft)
            if hard_errors:
                motion_status = "BLOCKED_FOR_REVIEW"
                exit_code = 2
            elif soft_warnings:
                motion_status = "PAUSED_SOFT_REVIEW"
            else:
                motion_status = "ROLLOUT_SESSION_ACTIVE"
        except Exception as exc:
            hard_errors.append(f"unexpected actuator exception: {exc!r}")
            motion_status = "BLOCKED_FOR_REVIEW"
            exit_code = 2
    elif envelope is not None and args.operator_session_approval_given:
        motion_status = "ARMED_FOR_ROLLOUT_SESSION"
    elif soft_warnings:
        motion_status = "PAUSED_SOFT_REVIEW"

    interpolated_steps = sum(1 for step in planned_steps if step["derived_from_model_action"])
    metrics = build_metrics(planned_steps, readbacks, selected_features=selected_features)
    payload: dict[str, Any] = {
        "schema": "openarm_folding_rollout_trial_chunk_result_v1",
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "rollout_trial_id": trial_id,
        "trial_root": str(args.trial_root),
        "chunk_index": args.chunk_index,
        "risk_level": args.risk_level,
        "risk_level_name": RISK_LEVELS[args.risk_level]["name"],
        "selected_scope": args.selected_scope,
        "proposal_json": str(args.proposal_json),
        "proposal_sha256": proposal_digest,
        "proposal_metadata": {
            "obs_id": proposal.get("obs_id"),
            "snapshot_checksum": proposal.get("snapshot_checksum"),
            "model_id": proposal.get("model_id"),
            "checkpoint_id": proposal.get("checkpoint_id"),
            "robot_config_id": proposal.get("robot_config_id"),
            "action_normalization_id": proposal.get("action_normalization_id"),
            "action_space_version": proposal.get("action_space_version"),
            "joint_order": proposal.get("joint_order"),
            "action_units": proposal.get("action_units"),
            "is_absolute_action": proposal.get("is_absolute_action"),
        },
        "selected_features": selected_features,
        "excluded_features": excluded_features,
        "session_envelope_json": str(args.session_envelope_json) if args.session_envelope_json else None,
        "execute_requested": bool(args.execute),
        "operator_session_approval_given": bool(args.operator_session_approval_given),
        "confirmation_phrase_matched": bool(envelope is not None and args.confirm == envelope.get("approval_phrase")),
        "operator_safety_flags": {
            "operator_at_robot": bool(args.operator_at_robot),
            "power_abort_control_held": bool(args.power_held),
            "abort_ready": bool(args.abort_ready),
            "estop_ready": bool(args.estop_ready),
            "right_arm_workspace_clear": bool(args.right_arm_workspace_clear),
            "left_arm_workspace_clear": bool(args.left_arm_workspace_clear),
            "gripper_workspace_clear": bool(args.gripper_workspace_clear),
            "human_body_clear_of_arm": bool(args.human_body_clear_of_arm),
        },
        "state_freshness_ttl_s": STATE_FRESHNESS_TTL_S,
        "readback_soft_error_deg": readback_soft_error_deg,
        "readback_hard_error_deg": readback_hard_error_deg,
        "arm_readback_soft_error_deg": args.arm_readback_soft_error_deg,
        "arm_readback_hard_error_deg": args.arm_readback_hard_error_deg,
        "gripper_readback_soft_error_deg": args.gripper_readback_soft_error_deg,
        "gripper_readback_hard_error_deg": args.gripper_readback_hard_error_deg,
        "clip_to_delta_cap": bool(args.clip_to_delta_cap),
        "allow_gripper_limit_saturation": bool(args.allow_gripper_limit_saturation),
        "arm_delta_cap_deg": args.arm_delta_cap_deg,
        "gripper_delta_cap_deg": args.gripper_delta_cap_deg,
        "fresh_state_age_s": state_age_s,
        "fresh_current_deg": fresh_current,
        "health_result": health_result,
        "planned_steps": planned_steps,
        "readbacks": readbacks,
        "estimated_duration_s": estimated_duration_s,
        "metrics": metrics,
        "completed_risk_level": args.risk_level if actuator_commands_sent or not hard_errors else None,
        "promotion_recommended": bool(args.execute and not hard_errors and not soft_warnings and args.risk_level < 4),
        "promotion_recommended_to_level": args.risk_level + 1 if args.execute and not hard_errors and not soft_warnings and args.risk_level < 4 else None,
        "actions_executed": len(readbacks),
        "execution_stopped_early": bool(args.execute and len(readbacks) < len(planned_steps)),
        "chunks_executed": 1 if actuator_commands_sent else 0,
        "interpolated_steps": interpolated_steps,
        "rejected_actions": len([warning for warning in soft_warnings if "cap exceeded" in warning]),
        "hard_errors": hard_errors,
        "soft_warnings": soft_warnings,
        "actuator_commands_sent": actuator_commands_sent,
        "motion_status": motion_status,
        "send_allowed": bool(actuator_commands_sent and not hard_errors),
        "motion_allowed": bool(actuator_commands_sent and not hard_errors),
        "command_path": "DamiaoMotorsBus guarded MIT batch" if actuator_commands_sent else "not_run",
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    print(json.dumps({k: v for k, v in payload.items() if k not in {"planned_steps", "readbacks"}}, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
