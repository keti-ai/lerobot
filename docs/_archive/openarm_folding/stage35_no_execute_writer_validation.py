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


def validate_packet(
    path: Path,
    *,
    expected_packet_sha256: str,
    approved_snapshot_id: str,
    expected_dry_run_sha256: str,
    expected_runtime_preflight_sha256: str,
    delta_limit_deg: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    digest = sha256(path)
    require(digest == expected_packet_sha256, f"packet checksum mismatch: {digest}", errors)

    payload = load_json(path)
    require(payload.get("mode") == "execution_packet_no_send", f"unexpected mode: {payload.get('mode')!r}", errors)
    require(
        payload.get("approved_snapshot_id") == approved_snapshot_id,
        f"unexpected approved_snapshot_id: {payload.get('approved_snapshot_id')!r}",
        errors,
    )
    require(payload.get("send_allowed") is False, "send_allowed is not false", errors)
    require(payload.get("motion_allowed") is False, "motion_allowed is not false", errors)
    require(payload.get("execution_allowed") is False, "execution_allowed is not false", errors)
    require(payload.get("actuator_commands_sent") is False, "actuator_commands_sent is not false", errors)
    require(payload.get("motion_status") == "BLOCKED", f"motion_status is {payload.get('motion_status')!r}", errors)
    require(payload.get("first_write_scope") == "right_arm_joints_only", "first_write_scope is not right_arm_joints_only", errors)
    require(payload.get("requires_final_operator_motion_gate") is True, "final operator gate is not required", errors)
    require(payload.get("requires_exact_command_approval") is True, "exact command approval is not required", errors)
    require(payload.get("blocking_first_write_keys") == [], f"blocking_first_write_keys={payload.get('blocking_first_write_keys')!r}", errors)
    require(
        payload.get("source_dry_run_json_sha256") == expected_dry_run_sha256,
        f"dry-run checksum mismatch: {payload.get('source_dry_run_json_sha256')!r}",
        errors,
    )
    require(
        payload.get("source_runtime_preflight_json_sha256") == expected_runtime_preflight_sha256,
        f"runtime preflight checksum mismatch: {payload.get('source_runtime_preflight_json_sha256')!r}",
        errors,
    )

    table = payload.get("target_table")
    require(isinstance(table, list), "target_table is missing or not a list", errors)
    if not isinstance(table, list):
        return {"sha256": digest, "payload": payload}, [], errors

    by_key = {row.get("key"): row for row in table if isinstance(row, dict)}
    selected = [by_key.get(key) for key in RIGHT_ARM_FEATURES]
    missing = [key for key, row in zip(RIGHT_ARM_FEATURES, selected, strict=True) if row is None]
    require(not missing, f"missing selected right-arm rows: {missing}", errors)
    selected_rows = [row for row in selected if row is not None]

    extra_send_candidates = [
        row.get("key")
        for row in table
        if isinstance(row, dict)
        and row.get("right_arm_first_write_candidate") is True
        and row.get("key") not in RIGHT_ARM_FEATURES
    ]
    require(not extra_send_candidates, f"unexpected first-write candidate rows: {extra_send_candidates}", errors)

    computed_max_delta = 0.0
    tolerance = 1e-6
    for row in selected_rows:
        key = row["key"]
        current = float(row["current_deg"])
        target = float(row["final_target_deg"])
        delta = float(row["final_delta_deg"])
        limit_min = float(row["limit_min_deg"])
        limit_max = float(row["limit_max_deg"])
        computed = target - current
        computed_max_delta = max(computed_max_delta, abs(delta))
        require(row.get("held") is False, f"{key} is unexpectedly held", errors)
        require(row.get("right_arm_first_write_candidate") is True, f"{key} is not marked as first-write candidate", errors)
        require(abs(computed - delta) <= tolerance, f"{key} delta mismatch: row={delta}, computed={computed}", errors)
        require(abs(delta) <= delta_limit_deg + tolerance, f"{key} delta {delta} exceeds {delta_limit_deg}", errors)
        require(limit_min <= target <= limit_max, f"{key} target {target} outside [{limit_min}, {limit_max}]", errors)

    packet_max_delta = float(payload.get("max_abs_right_arm_candidate_delta_deg", -1.0))
    require(
        abs(packet_max_delta - computed_max_delta) <= tolerance,
        f"max delta mismatch: packet={packet_max_delta}, computed={computed_max_delta}",
        errors,
    )
    require(packet_max_delta <= delta_limit_deg + tolerance, f"packet max delta {packet_max_delta} exceeds {delta_limit_deg}", errors)

    return {"sha256": digest, "payload": payload}, selected_rows, errors


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


def read_fresh_right_arm(port: str) -> dict[str, float]:
    selected_motors = [FEATURE_TO_MOTOR[key] for key in RIGHT_ARM_FEATURES]
    bus = make_right_bus(port)
    connected = False
    try:
        bus.connect(handshake=False)
        connected = True
        states = bus.sync_read_all_states(selected_motors)
        return {
            key: float(states[FEATURE_TO_MOTOR[key]]["position"])
            for key in RIGHT_ARM_FEATURES
        }
    finally:
        if connected:
            bus.disconnect(disable_torque=False)


def build_rows(
    selected_rows: list[dict[str, Any]],
    *,
    fresh: dict[str, float] | None,
    drift_limit_deg: float,
    delta_limit_deg: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    errors = []
    tolerance = 1e-6
    for row in selected_rows:
        key = str(row["key"])
        packet_current = float(row["current_deg"])
        target = float(row["final_target_deg"])
        delta_from_packet = float(row["final_delta_deg"])
        limit_min = float(row["limit_min_deg"])
        limit_max = float(row["limit_max_deg"])
        fresh_current = None if fresh is None else float(fresh[key])
        drift = None if fresh_current is None else fresh_current - packet_current
        delta_from_fresh = None if fresh_current is None else target - fresh_current
        fresh_validated = None
        if fresh_current is not None:
            fresh_validated = (
                abs(drift) <= drift_limit_deg + tolerance
                and abs(delta_from_fresh) <= delta_limit_deg + tolerance
                and limit_min <= target <= limit_max
            )
            if not fresh_validated:
                errors.append(f"{key} fresh validation failed")
        rows.append(
            {
                "key": key,
                "motor": FEATURE_TO_MOTOR[key],
                "packet_current_deg": packet_current,
                "fresh_current_deg": fresh_current,
                "drift_from_packet_current_deg": drift,
                "target_deg": target,
                "target_delta_from_packet_deg": delta_from_packet,
                "target_delta_from_fresh_deg": delta_from_fresh,
                "limit_min_deg": limit_min,
                "limit_max_deg": limit_max,
                "drift_limit_deg": drift_limit_deg,
                "delta_limit_deg": delta_limit_deg,
                "fresh_validated": fresh_validated,
                "would_send": False,
            }
        )
    return rows, errors


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 35 No-Execute Writer Validation",
        "",
        "## Status",
        "",
        f"- Packet validation passed: `{str(payload['packet_validation_passed']).lower()}`",
        f"- Fresh readback validation passed: `{payload['fresh_readback_validation_passed']}`",
        "- Send allowed: `false`",
        "- Motion allowed: `false`",
        "- Execution allowed: `false`",
        "- Actuator commands sent: `false`",
        "- Execute path available: `false`",
        f"- Actual writer status: `{payload['actual_writer_status']}`",
        "",
        "This artifact does not authorize robot motion.",
        "",
        "## Rows",
        "",
        "| Key | Packet current deg | Fresh current deg | Target deg | Delta from fresh deg | Drift deg | Validated |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["rows"]:
        fresh = "N/A" if row["fresh_current_deg"] is None else f"{row['fresh_current_deg']:.6f}"
        delta = "N/A" if row["target_delta_from_fresh_deg"] is None else f"{row['target_delta_from_fresh_deg']:.6f}"
        drift = "N/A" if row["drift_from_packet_current_deg"] is None else f"{row['drift_from_packet_current_deg']:.6f}"
        lines.append(
            f"| `{row['key']}` | {row['packet_current_deg']:.6f} | {fresh} | "
            f"{row['target_deg']:.6f} | {delta} | {drift} | `{row['fresh_validated']}` |"
        )
    if payload["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{error}`" for error in payload["errors"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Stage 35 actual actuator write remains blocked until a separate explicit human approval.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 35 no-execute validation for the approved OpenArm first-write packet. No execute option exists."
    )
    parser.add_argument("--packet-json", type=Path, required=True)
    parser.add_argument("--expected-packet-sha256", default=APPROVED_PACKET_SHA256)
    parser.add_argument("--approved-snapshot-id", default=APPROVED_SNAPSHOT_ID)
    parser.add_argument("--expected-dry-run-sha256", default=APPROVED_DRY_RUN_SHA256)
    parser.add_argument("--expected-runtime-preflight-sha256", default=APPROVED_RUNTIME_PREFLIGHT_SHA256)
    parser.add_argument("--read-fresh-current", action="store_true")
    parser.add_argument("--right-port", default=RIGHT_PORT)
    parser.add_argument("--drift-limit-deg", type=float, default=1.0)
    parser.add_argument("--delta-limit-deg", type=float, default=2.0)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    args = parser.parse_args()

    if args.drift_limit_deg <= 0 or args.delta_limit_deg <= 0:
        raise SystemExit("drift and delta limits must be positive")

    packet, selected_rows, errors = validate_packet(
        args.packet_json,
        expected_packet_sha256=args.expected_packet_sha256,
        approved_snapshot_id=args.approved_snapshot_id,
        expected_dry_run_sha256=args.expected_dry_run_sha256,
        expected_runtime_preflight_sha256=args.expected_runtime_preflight_sha256,
        delta_limit_deg=args.delta_limit_deg,
    )
    fresh = read_fresh_right_arm(args.right_port) if args.read_fresh_current else None
    rows, fresh_errors = build_rows(
        selected_rows,
        fresh=fresh,
        drift_limit_deg=args.drift_limit_deg,
        delta_limit_deg=args.delta_limit_deg,
    )
    errors.extend(fresh_errors)
    packet_validation_passed = not [error for error in errors if "fresh validation failed" not in error]
    fresh_readback_validation_passed: bool | None
    if not args.read_fresh_current:
        fresh_readback_validation_passed = None
    else:
        fresh_readback_validation_passed = not fresh_errors

    payload = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "stage35_no_execute_writer_validation",
        "approved_snapshot_id": args.approved_snapshot_id,
        "packet_json": str(args.packet_json),
        "packet_sha256": packet["sha256"],
        "expected_packet_sha256": args.expected_packet_sha256,
        "source_dry_run_sha256": packet["payload"].get("source_dry_run_json_sha256"),
        "source_runtime_preflight_sha256": packet["payload"].get("source_runtime_preflight_json_sha256"),
        "read_fresh_current": bool(args.read_fresh_current),
        "right_port": args.right_port,
        "first_write_scope": "right_arm_joints_only",
        "selected_features": RIGHT_ARM_FEATURES,
        "max_abs_right_arm_candidate_delta_deg": packet["payload"].get("max_abs_right_arm_candidate_delta_deg"),
        "packet_validation_passed": packet_validation_passed,
        "fresh_readback_validation_passed": fresh_readback_validation_passed,
        "send_allowed": False,
        "motion_allowed": False,
        "execution_allowed": False,
        "actuator_commands_sent": False,
        "execute_path_available": False,
        "operator_motion_approval": "NOT_GIVEN",
        "actual_writer_status": "NOT_READY",
        "requires_separate_operator_motion_gate": True,
        "requires_abort_power_procedure": True,
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); disconnect(disable_torque=False); no OpenArmFollower.connect()"
        if args.read_fresh_current
        else "not_run_packet_only_validation",
        "errors": errors,
        "rows": rows,
    }

    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.md_out is not None:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(args.md_out, payload)

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
