#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import time
from pathlib import Path
from typing import Any


APPROVED_SNAPSHOT_ID = "snapshot_20260512_171650"
APPROVED_PACKET_SHA256 = "c5411331665ea5b31a9d85de4adf27ce74f0c9596630c4cc8481e6afd58ec259"
APPROVED_DRY_RUN_SHA256 = "ef1501cad3dd3890955701d74c330e3393a1181fcbfbcba47a2a9d6100263fdc"
APPROVED_RUNTIME_PREFLIGHT_SHA256 = "8b3d8df7db88eb8bdfaa9975e08cef3d91e9c0769312312cd2d969666b36d920"
APPROVED_NO_EXECUTE_VALIDATION_SHA256 = "f16c0262cc7f028caa8a6a552015d4ff7e691b9bec57a509b33ef585be4bcd4d"
CONFIRMATION_PHRASE = "SEND_STAGE35_RIGHT_ARM_JOINTS_ONCE_20260512_171650"
RIGHT_PORT = "can1"
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


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


def validate_no_execute_validation(path: Path | None, errors: list[str]) -> dict[str, Any] | None:
    if path is None:
        return None
    digest = sha256(path)
    payload = load_json(path)
    require(digest == APPROVED_NO_EXECUTE_VALIDATION_SHA256, f"no-execute checksum mismatch: {digest}", errors)
    require(payload.get("mode") == "stage35_no_execute_writer_validation", "unexpected no-execute mode", errors)
    require(payload.get("approved_snapshot_id") == APPROVED_SNAPSHOT_ID, "unexpected no-execute snapshot", errors)
    require(payload.get("packet_sha256") == APPROVED_PACKET_SHA256, "unexpected no-execute packet checksum", errors)
    require(payload.get("packet_validation_passed") is True, "no-execute packet validation did not pass", errors)
    require(
        payload.get("fresh_readback_validation_passed") is True,
        "no-execute fresh readback validation did not pass",
        errors,
    )
    require(payload.get("send_allowed") is False, "no-execute send_allowed is not false", errors)
    require(payload.get("motion_allowed") is False, "no-execute motion_allowed is not false", errors)
    require(payload.get("execution_allowed") is False, "no-execute execution_allowed is not false", errors)
    require(payload.get("actuator_commands_sent") is False, "no-execute actuator_commands_sent is not false", errors)
    require(payload.get("execute_path_available") is False, "no-execute unexpectedly exposes execute path", errors)
    return {"sha256": digest, "payload": payload}


def validate_packet(path: Path, *, delta_limit_deg: float) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    digest = sha256(path)
    payload = load_json(path)

    require(digest == APPROVED_PACKET_SHA256, f"packet checksum mismatch: {digest}", errors)
    require(payload.get("mode") == "execution_packet_no_send", f"unexpected mode: {payload.get('mode')!r}", errors)
    require(payload.get("approved_snapshot_id") == APPROVED_SNAPSHOT_ID, "unexpected approved snapshot", errors)
    require(payload.get("send_allowed") is False, "packet send_allowed is not false", errors)
    require(payload.get("motion_allowed") is False, "packet motion_allowed is not false", errors)
    require(payload.get("execution_allowed") is False, "packet execution_allowed is not false", errors)
    require(payload.get("actuator_commands_sent") is False, "packet actuator_commands_sent is not false", errors)
    require(payload.get("motion_status") == "BLOCKED", "packet motion_status is not BLOCKED", errors)
    require(payload.get("first_write_scope") == "right_arm_joints_only", "unexpected first_write_scope", errors)
    require(payload.get("requires_final_operator_motion_gate") is True, "packet final motion gate missing", errors)
    require(payload.get("requires_exact_command_approval") is True, "packet exact command approval missing", errors)
    require(payload.get("blocking_first_write_keys") == [], "packet has blocking first-write keys", errors)
    require(payload.get("source_dry_run_json_sha256") == APPROVED_DRY_RUN_SHA256, "dry-run checksum mismatch", errors)
    require(
        payload.get("source_runtime_preflight_json_sha256") == APPROVED_RUNTIME_PREFLIGHT_SHA256,
        "runtime preflight checksum mismatch",
        errors,
    )

    table = payload.get("target_table")
    require(isinstance(table, list), "target_table is missing or not a list", errors)
    if not isinstance(table, list):
        return {"sha256": digest, "payload": payload}, [], errors

    by_key = {row.get("key"): row for row in table if isinstance(row, dict)}
    missing = [key for key in RIGHT_ARM_FEATURES if key not in by_key]
    require(not missing, f"missing selected right-arm keys: {missing}", errors)

    selected_rows: list[dict[str, Any]] = []
    max_delta = 0.0
    tolerance = 1e-6
    for key in RIGHT_ARM_FEATURES:
        row = by_key.get(key)
        if not isinstance(row, dict):
            continue
        motor = FEATURE_TO_MOTOR[key]
        current = float(row["current_deg"])
        target = float(row["final_target_deg"])
        delta = float(row["final_delta_deg"])
        limit_min = float(row["limit_min_deg"])
        limit_max = float(row["limit_max_deg"])
        max_delta = max(max_delta, abs(delta))
        require(row.get("held") is False, f"{key} is unexpectedly held", errors)
        require(row.get("right_arm_first_write_candidate") is True, f"{key} is not selected", errors)
        require(abs((target - current) - delta) <= tolerance, f"{key} delta mismatch", errors)
        require(abs(delta) <= delta_limit_deg + tolerance, f"{key} delta {delta} exceeds {delta_limit_deg}", errors)
        require(limit_min <= target <= limit_max, f"{key} target outside packet limits", errors)
        selected_rows.append(
            {
                "key": key,
                "motor": motor,
                "packet_current_deg": current,
                "target_deg": target,
                "target_delta_from_packet_deg": delta,
                "limit_min_deg": limit_min,
                "limit_max_deg": limit_max,
            }
        )

    for row in table:
        if not isinstance(row, dict):
            continue
        key = row.get("key")
        if key not in RIGHT_ARM_FEATURES:
            require(
                row.get("right_arm_first_write_candidate") is False,
                f"non-selected row unexpectedly sendable: {key}",
                errors,
            )

    packet_max = float(payload.get("max_abs_right_arm_candidate_delta_deg", -1.0))
    require(abs(packet_max - max_delta) <= tolerance, "packet max delta mismatch", errors)
    require(packet_max <= delta_limit_deg + tolerance, f"packet max delta {packet_max} exceeds {delta_limit_deg}", errors)
    return {"sha256": digest, "payload": payload}, selected_rows, errors


def read_selected(bus: Any, motors: list[str]) -> dict[str, float]:
    states = bus.sync_read_all_states(motors)
    return {motor: float(states[motor]["position"]) for motor in motors}


def build_rows(
    selected_rows: list[dict[str, Any]],
    fresh: dict[str, float],
    *,
    drift_limit_deg: float,
    delta_limit_deg: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    tolerance = 1e-6
    for row in selected_rows:
        motor = str(row["motor"])
        packet_current = float(row["packet_current_deg"])
        fresh_current = float(fresh[motor])
        target = float(row["target_deg"])
        drift = fresh_current - packet_current
        delta = target - fresh_current
        limit_min = float(row["limit_min_deg"])
        limit_max = float(row["limit_max_deg"])
        validated = (
            abs(drift) <= drift_limit_deg + tolerance
            and abs(delta) <= delta_limit_deg + tolerance
            and limit_min <= target <= limit_max
        )
        if not validated:
            errors.append(row["key"])
        rows.append(
            {
                "key": row["key"],
                "motor": motor,
                "packet_current_deg": packet_current,
                "fresh_current_deg": fresh_current,
                "drift_from_packet_current_deg": drift,
                "target_deg": target,
                "target_delta_from_packet_deg": float(row["target_delta_from_packet_deg"]),
                "target_delta_from_fresh_deg": delta,
                "limit_min_deg": limit_min,
                "limit_max_deg": limit_max,
                "drift_limit_deg": drift_limit_deg,
                "delta_limit_deg": delta_limit_deg,
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
        "# Stage 35 Guarded Actual Actuator Write",
        "",
        "## Status",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Execute requested: `{payload['execute_requested']}`",
        f"- Motion approval: `{payload['operator_motion_approval']}`",
        f"- Packet validation passed: `{payload['packet_validation_passed']}`",
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
            f"{row['target_delta_from_fresh_deg']:.6f} | {row['drift_from_packet_current_deg']:.6f} | "
            f"`{row['would_send']}` | `{row['fresh_validated']}` |"
        )
    if payload["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{error}`" for error in payload["errors"])
    lines.extend(["", "## Boundary", ""])
    if payload["actuator_commands_sent"]:
        lines.append("This artifact records the guarded first right-arm actuator write attempt.")
    else:
        lines.append("No actuator command was sent by this run.")
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 35 guarded first actuator writer for snapshot_20260512_171650."
    )
    parser.add_argument("--packet-json", type=Path, required=True)
    parser.add_argument("--no-execute-validation-json", type=Path)
    parser.add_argument("--right-port", default=RIGHT_PORT)
    parser.add_argument("--drift-limit-deg", type=float, default=1.0)
    parser.add_argument("--delta-limit-deg", type=float, default=2.0)
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
    if args.drift_limit_deg <= 0 or args.delta_limit_deg <= 0:
        raise SystemExit("drift and delta limits must be positive")
    if args.hold_seconds < 0:
        raise SystemExit("hold-seconds must be non-negative")
    if args.execute and args.json_out is None:
        raise SystemExit("--json-out is required with --execute")

    pre_errors: list[str] = []
    no_execute = validate_no_execute_validation(args.no_execute_validation_json, pre_errors)
    if args.execute:
        require(no_execute is not None, "--no-execute-validation-json is required with --execute", pre_errors)
        require(args.operator_motion_approval_given, "--operator-motion-approval-given is required", pre_errors)
        require(args.operator_at_robot, "--operator-at-robot is required", pre_errors)
        require(args.power_held, "--power-held is required", pre_errors)
        require(args.abort_ready, "--abort-ready is required", pre_errors)
        require(args.estop_ready, "--estop-ready is required", pre_errors)
        require(args.confirm == CONFIRMATION_PHRASE, f"--confirm must equal {CONFIRMATION_PHRASE}", pre_errors)
    if pre_errors:
        raise SystemExit("; ".join(pre_errors))

    packet, selected_rows, packet_errors = validate_packet(args.packet_json, delta_limit_deg=args.delta_limit_deg)
    selected_motors = [row["motor"] for row in selected_rows]
    bus = make_right_bus(args.right_port)
    connected = False
    payload: dict[str, Any] = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "stage35_guarded_actual_actuator_write",
        "approved_snapshot_id": APPROVED_SNAPSHOT_ID,
        "packet_json": str(args.packet_json),
        "packet_sha256": packet["sha256"],
        "no_execute_validation_json": None if args.no_execute_validation_json is None else str(args.no_execute_validation_json),
        "no_execute_validation_sha256": None if no_execute is None else no_execute["sha256"],
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
        "packet_validation_passed": not packet_errors,
        "fresh_target_validation_passed": False,
        "send_allowed": False,
        "motion_allowed": False,
        "execution_allowed": False,
        "actuator_commands_sent": False,
        "execute_path_available": True,
        "motion_status": "BLOCKED",
        "hold_seconds": args.hold_seconds,
        "drift_limit_deg": args.drift_limit_deg,
        "delta_limit_deg": args.delta_limit_deg,
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no OpenArmFollower.connect()",
        "write_path": "enable selected right-arm joints; one MIT batch; hold/readback; disable selected joints"
        if args.execute
        else "not_run",
        "rows": [],
        "post_write_readback_deg": None,
        "post_hold_readback_deg": None,
        "final_readback_deg": None,
        "errors": packet_errors.copy(),
    }

    exit_code = 0
    torque_enabled = False
    try:
        if packet_errors:
            raise RuntimeError(f"packet validation failed: {packet_errors}")
        bus.connect(handshake=False)
        connected = True
        fresh = read_selected(bus, selected_motors)
        rows, fresh_errors = build_rows(
            selected_rows,
            fresh,
            drift_limit_deg=args.drift_limit_deg,
            delta_limit_deg=args.delta_limit_deg,
        )
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
