#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import time
from pathlib import Path
from typing import Any


APPROVED_SNAPSHOT_ID = "snapshot_20260512_194042"
APPROVED_PROPOSAL_SHA256 = "498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da"
CONFIRMATION_PHRASE = "SEND_STAGE37_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260512_194042"
RIGHT_PORT = "can1"
DRIFT_LIMIT_DEG = 1.0
DELTA_LIMIT_DEG = 2.0
RIGHT_ARM_FEATURES = [
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
]
FEATURE_TO_MOTOR = {
    "right_joint_1.pos": "joint_1",
    "right_joint_2.pos": "joint_2",
    "right_joint_3.pos": "joint_3",
    "right_joint_4.pos": "joint_4",
    "right_joint_5.pos": "joint_5",
    "right_joint_6.pos": "joint_6",
    "right_joint_7.pos": "joint_7",
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
RIGHT_LIMITS = {
    "right_joint_1.pos": (-75.0, 75.0),
    "right_joint_2.pos": (-9.0, 90.0),
    "right_joint_3.pos": (-85.0, 85.0),
    "right_joint_4.pos": (0.0, 135.0),
    "right_joint_5.pos": (-85.0, 85.0),
    "right_joint_6.pos": (-40.0, 40.0),
    "right_joint_7.pos": (-80.0, 80.0),
}
TARGET_TABLE = [
    {
        "key": "right_joint_1.pos",
        "proposal_current_deg": -5.081738,
        "proposal_deg": -4.664086,
        "proposal_delta_deg": 0.417652,
        "target_deg": -4.664086,
        "target_delta_from_proposal_current_deg": 0.417652,
    },
    {
        "key": "right_joint_2.pos",
        "proposal_current_deg": -1.868768,
        "proposal_deg": -1.259376,
        "proposal_delta_deg": 0.609392,
        "target_deg": -1.259376,
        "target_delta_from_proposal_current_deg": 0.609392,
    },
    {
        "key": "right_joint_3.pos",
        "proposal_current_deg": 14.939218,
        "proposal_deg": 14.926427,
        "proposal_delta_deg": -0.012791,
        "target_deg": 14.926427,
        "target_delta_from_proposal_current_deg": -0.012791,
    },
    {
        "key": "right_joint_4.pos",
        "proposal_current_deg": 8.294708,
        "proposal_deg": 9.506226,
        "proposal_delta_deg": 1.211517,
        "target_deg": 9.506226,
        "target_delta_from_proposal_current_deg": 1.211517,
    },
    {
        "key": "right_joint_5.pos",
        "proposal_current_deg": -2.939758,
        "proposal_deg": -3.820436,
        "proposal_delta_deg": -0.880678,
        "target_deg": -3.820436,
        "target_delta_from_proposal_current_deg": -0.880678,
    },
    {
        "key": "right_joint_6.pos",
        "proposal_current_deg": -0.469924,
        "proposal_deg": 0.397769,
        "proposal_delta_deg": 0.867693,
        "target_deg": 0.397769,
        "target_delta_from_proposal_current_deg": 0.867693,
    },
    {
        "key": "right_joint_7.pos",
        "proposal_current_deg": -4.032605,
        "proposal_deg": -1.921464,
        "proposal_delta_deg": 2.111141,
        "target_deg": -2.032605,
        "target_delta_from_proposal_current_deg": 2.0,
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def make_right_bus(port: str):
    from lerobot.motors import Motor, MotorNormMode
    from lerobot.motors.damiao import DamiaoMotorsBus
    from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase

    motors = {}
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


def validate_proposal(path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    digest = sha256(path)
    payload = json.loads(path.read_text())
    proposal = payload.get("proposal", {})

    require(digest == APPROVED_PROPOSAL_SHA256, f"proposal checksum mismatch: {digest}", errors)
    require(payload.get("schema") == "openarm_folding_remote_proposal_client_result_v1", "unexpected client schema", errors)
    require(proposal.get("schema") == "openarm_folding_action_proposal_v1", "unexpected proposal schema", errors)
    require(proposal.get("obs_id") == APPROVED_SNAPSHOT_ID, f"unexpected obs_id: {proposal.get('obs_id')!r}", errors)
    require(proposal.get("action_shape") == [1, 30, 16], "unexpected action_shape", errors)
    require(proposal.get("all_finite") is True, "proposal is not all_finite", errors)
    require(proposal.get("send_allowed") is False, "proposal send_allowed is not false", errors)
    require(proposal.get("motion_allowed") is False, "proposal motion_allowed is not false", errors)
    require(proposal.get("actuator_commands_sent") is False, "proposal actuator_commands_sent is not false", errors)

    proposal_rows = {row.get("key"): row for row in proposal.get("rows", []) if isinstance(row, dict)}
    tolerance = 1e-3
    for target in TARGET_TABLE:
        key = target["key"]
        row = proposal_rows.get(key)
        require(row is not None, f"proposal missing {key}", errors)
        if row is None:
            continue
        require(
            abs(float(row["current_deg"]) - float(target["proposal_current_deg"])) <= tolerance,
            f"{key} current mismatch",
            errors,
        )
        require(
            abs(float(row["proposed_deg"]) - float(target["proposal_deg"])) <= tolerance,
            f"{key} proposal mismatch",
            errors,
        )
        require(
            abs(float(row["delta_deg"]) - float(target["proposal_delta_deg"])) <= tolerance,
            f"{key} delta mismatch",
            errors,
        )
    return {"sha256": digest, "payload": payload}, errors


def read_selected(bus: Any, motors: list[str]) -> dict[str, float]:
    states = bus.sync_read_all_states(motors)
    return {motor: float(states[motor]["position"]) for motor in motors}


def build_rows(fresh: dict[str, float]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    tolerance = 1e-6
    for target in TARGET_TABLE:
        key = target["key"]
        motor = FEATURE_TO_MOTOR[key]
        fresh_current = float(fresh[motor])
        target_deg = float(target["target_deg"])
        proposal_current = float(target["proposal_current_deg"])
        drift = fresh_current - proposal_current
        delta_from_fresh = target_deg - fresh_current
        limit_min, limit_max = RIGHT_LIMITS[key]
        validated = (
            abs(drift) <= DRIFT_LIMIT_DEG + tolerance
            and abs(delta_from_fresh) <= DELTA_LIMIT_DEG + tolerance
            and limit_min <= target_deg <= limit_max
        )
        if not validated:
            errors.append(key)
        rows.append(
            {
                "key": key,
                "motor": motor,
                "proposal_current_deg": proposal_current,
                "proposal_deg": float(target["proposal_deg"]),
                "proposal_delta_deg": float(target["proposal_delta_deg"]),
                "target_deg": target_deg,
                "target_delta_from_proposal_current_deg": float(target["target_delta_from_proposal_current_deg"]),
                "fresh_current_deg": fresh_current,
                "drift_from_proposal_current_deg": drift,
                "target_delta_from_fresh_deg": delta_from_fresh,
                "limit_min_deg": limit_min,
                "limit_max_deg": limit_max,
                "fresh_validated": validated,
                "would_send": False,
            }
        )
    return rows, errors


def build_commands(rows: list[dict[str, Any]]) -> dict[str, tuple[float, float, float, float, float]]:
    from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase

    config = OpenArmFollowerConfigBase(port=RIGHT_PORT, side="right")
    commands = {}
    for row in rows:
        motor = str(row["motor"])
        idx = MOTOR_INDEX[motor]
        kp = config.position_kp[idx] if isinstance(config.position_kp, list) else config.position_kp
        kd = config.position_kd[idx] if isinstance(config.position_kd, list) else config.position_kd
        commands[motor] = (float(kp), float(kd), float(row["target_deg"]), 0.0, 0.0)
    return commands


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 37 Guarded Served Proposal Write",
        "",
        "## Status",
        "",
        f"- Execute requested: `{payload['execute_requested']}`",
        f"- Motion approval: `{payload['operator_motion_approval']}`",
        f"- Proposal validation passed: `{payload['proposal_validation_passed']}`",
        f"- Fresh target validation passed: `{payload['fresh_target_validation_passed']}`",
        f"- Actuator commands sent: `{payload['actuator_commands_sent']}`",
        f"- Motion status: `{payload['motion_status']}`",
        "",
        "## Rows",
        "",
        "| Key | Fresh current deg | Target deg | Delta from fresh deg | Drift deg | Would send | Validated |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['key']}` | {row['fresh_current_deg']:.6f} | {row['target_deg']:.6f} | "
            f"{row['target_delta_from_fresh_deg']:.6f} | {row['drift_from_proposal_current_deg']:.6f} | "
            f"`{row['would_send']}` | `{row['fresh_validated']}` |"
        )
    if payload["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{error}`" for error in payload["errors"])
    lines.extend(["", "## Boundary", ""])
    lines.append("This artifact records a Stage 37 write attempt." if payload["actuator_commands_sent"] else "No actuator command was sent by this run.")
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 37 guarded write from A6000 served proposal.")
    parser.add_argument("--proposal-json", type=Path, required=True)
    parser.add_argument("--right-port", default=RIGHT_PORT)
    parser.add_argument("--hold-seconds", type=float, default=1.0)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--operator-motion-approval-given", action="store_true")
    parser.add_argument("--operator-at-robot", action="store_true")
    parser.add_argument("--power-held", action="store_true")
    parser.add_argument("--abort-ready", action="store_true")
    parser.add_argument("--estop-ready", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hold_seconds < 0:
        raise SystemExit("hold-seconds must be non-negative")
    if args.execute and args.json_out is None:
        raise SystemExit("--json-out is required with --execute")

    pre_errors: list[str] = []
    if args.execute:
        require(args.operator_motion_approval_given, "--operator-motion-approval-given is required", pre_errors)
        require(args.operator_at_robot, "--operator-at-robot is required", pre_errors)
        require(args.power_held, "--power-held is required", pre_errors)
        require(args.abort_ready, "--abort-ready is required", pre_errors)
        require(args.estop_ready, "--estop-ready is required", pre_errors)
        require(args.confirm == CONFIRMATION_PHRASE, f"--confirm must equal {CONFIRMATION_PHRASE}", pre_errors)
    if pre_errors:
        raise SystemExit("; ".join(pre_errors))

    proposal, proposal_errors = validate_proposal(args.proposal_json)
    selected_motors = [FEATURE_TO_MOTOR[key] for key in RIGHT_ARM_FEATURES]
    payload: dict[str, Any] = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "stage37_guarded_served_proposal_write",
        "approved_snapshot_id": APPROVED_SNAPSHOT_ID,
        "proposal_json": str(args.proposal_json),
        "proposal_sha256": proposal["sha256"],
        "right_port": args.right_port,
        "selected_features": RIGHT_ARM_FEATURES,
        "selected_motors": selected_motors,
        "excluded": ["left_arm", "right_gripper", "left_gripper"],
        "execute_requested": bool(args.execute),
        "operator_motion_approval": "GIVEN" if args.operator_motion_approval_given else "NOT_GIVEN",
        "operator_at_robot": bool(args.operator_at_robot),
        "power_held": bool(args.power_held),
        "abort_ready": bool(args.abort_ready),
        "estop_ready": bool(args.estop_ready),
        "confirmation_phrase_matched": args.confirm == CONFIRMATION_PHRASE,
        "proposal_validation_passed": not proposal_errors,
        "fresh_target_validation_passed": False,
        "send_allowed": False,
        "motion_allowed": False,
        "execution_allowed": False,
        "actuator_commands_sent": False,
        "motion_status": "BLOCKED",
        "hold_seconds": args.hold_seconds,
        "drift_limit_deg": DRIFT_LIMIT_DEG,
        "delta_limit_deg": DELTA_LIMIT_DEG,
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no OpenArmFollower.connect()",
        "write_path": "enable selected right-arm joints; one MIT batch; hold/readback; disable selected joints"
        if args.execute
        else "not_run",
        "rows": [],
        "post_write_readback_deg": None,
        "post_hold_readback_deg": None,
        "final_readback_deg": None,
        "errors": proposal_errors.copy(),
    }

    bus = make_right_bus(args.right_port)
    connected = False
    torque_enabled = False
    exit_code = 0
    try:
        if proposal_errors:
            raise RuntimeError(f"proposal validation failed: {proposal_errors}")
        bus.connect(handshake=False)
        connected = True
        rows, fresh_errors = build_rows(read_selected(bus, selected_motors))
        payload["rows"] = rows
        payload["fresh_target_validation_passed"] = not fresh_errors
        if fresh_errors:
            payload["errors"].append(f"fresh_target_validation_failed: {fresh_errors}")
            exit_code = 2
        elif args.execute:
            payload["send_allowed"] = True
            payload["motion_allowed"] = True
            payload["execution_allowed"] = True
            payload["motion_status"] = "APPROVED_FOR_SINGLE_WRITE"
            commands = build_commands(rows)
            for row in rows:
                row["would_send"] = True
            bus.enable_torque(selected_motors)
            torque_enabled = True
            bus._mit_control_batch(commands)
            payload["actuator_commands_sent"] = True
            payload["post_write_readback_deg"] = read_selected(bus, selected_motors)
            time.sleep(args.hold_seconds)
            payload["post_hold_readback_deg"] = read_selected(bus, selected_motors)
            bus.disable_torque(selected_motors, num_retry=2)
            torque_enabled = False
            payload["final_readback_deg"] = read_selected(bus, selected_motors)
            payload["motion_status"] = "SINGLE_WRITE_ATTEMPTED"
        print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    except Exception as exc:
        payload["errors"].append(repr(exc))
        exit_code = 2
        print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    finally:
        if connected and torque_enabled:
            try:
                bus.disable_torque(selected_motors, num_retry=2)
            except Exception as exc:
                payload["errors"].append(f"final_disable_failed: {exc!r}")
                exit_code = 2
        if connected:
            try:
                bus.disconnect(disable_torque=False)
            except Exception as exc:
                payload["errors"].append(f"disconnect_failed: {exc!r}")
                exit_code = 2
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        if args.md_out is not None:
            args.md_out.parent.mkdir(parents=True, exist_ok=True)
            write_markdown(args.md_out, payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
