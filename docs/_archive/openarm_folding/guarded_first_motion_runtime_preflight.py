#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import time
from pathlib import Path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.damiao import DamiaoMotorsBus
from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase


APPROVED_DRY_RUN_SHA256 = "ce6c6efb2d6b2d7532500cb7b4ca61273993358ccd1ef437e4ae25781ee2cef3"
APPROVED_SNAPSHOT_ID = "snapshot_20260511_154554"

FEATURE_TO_ARM_MOTOR = {
    "right_joint_1.pos": ("right", "joint_1"),
    "right_joint_2.pos": ("right", "joint_2"),
    "right_joint_3.pos": ("right", "joint_3"),
    "right_joint_4.pos": ("right", "joint_4"),
    "right_joint_5.pos": ("right", "joint_5"),
    "right_joint_6.pos": ("right", "joint_6"),
    "right_joint_7.pos": ("right", "joint_7"),
    "right_gripper.pos": ("right", "gripper"),
    "left_joint_1.pos": ("left", "joint_1"),
    "left_joint_2.pos": ("left", "joint_2"),
    "left_joint_3.pos": ("left", "joint_3"),
    "left_joint_4.pos": ("left", "joint_4"),
    "left_joint_5.pos": ("left", "joint_5"),
    "left_joint_6.pos": ("left", "joint_6"),
    "left_joint_7.pos": ("left", "joint_7"),
    "left_gripper.pos": ("left", "gripper"),
}

ARMS = {
    "right": "can1",
    "left": "can0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def read_arm(port: str) -> dict[str, float]:
    bus = make_bus(port)
    bus.connect(handshake=False)
    try:
        states = bus.sync_read_all_states()
        return {name: float(state["position"]) for name, state in states.items()}
    finally:
        bus.disconnect(disable_torque=False)


def read_current_features() -> dict[str, float]:
    arm_states = {arm: read_arm(port) for arm, port in ARMS.items()}
    return {
        feature: arm_states[arm][motor]
        for feature, (arm, motor) in FEATURE_TO_ARM_MOTOR.items()
    }


def validate_dry_run(path: Path) -> dict:
    digest = sha256(path)
    if digest != APPROVED_DRY_RUN_SHA256:
        raise SystemExit(f"Rejected dry-run checksum {digest}; expected {APPROVED_DRY_RUN_SHA256}")
    payload = json.loads(path.read_text())
    if payload.get("mode") != "dry_run_only":
        raise SystemExit(f"Rejected dry-run mode={payload.get('mode')!r}")
    if payload.get("send_allowed") is not False or payload.get("motion_allowed") is not False:
        raise SystemExit("Rejected dry-run because send_allowed/motion_allowed is not false")
    if payload.get("approved_snapshot_id") != APPROVED_SNAPSHOT_ID:
        raise SystemExit(f"Rejected dry-run snapshot={payload.get('approved_snapshot_id')!r}")
    if payload.get("requires_separate_operator_motion_gate") is not True:
        raise SystemExit("Rejected dry-run because separate operator gate is not required")
    plan = payload.get("plan")
    if not isinstance(plan, list) or len(plan) != len(FEATURE_TO_ARM_MOTOR):
        raise SystemExit("Rejected dry-run because plan is missing or incomplete")
    return {"sha256": digest, "payload": payload}


def compare(plan: list[dict], current: dict[str, float], arm_drift_limit: float, gripper_drift_limit: float) -> list[dict]:
    rows = []
    for item in plan:
        key = item["key"]
        fresh = current[key]
        review_current = float(item["current_deg"])
        target = float(item["final_target_deg"])
        drift = fresh - review_current
        target_delta_from_fresh = target - fresh
        drift_limit = gripper_drift_limit if "gripper" in key else arm_drift_limit
        rows.append(
            {
                "key": key,
                "review_current_deg": review_current,
                "fresh_current_deg": fresh,
                "drift_deg": drift,
                "drift_limit_deg": drift_limit,
                "stage15_target_deg": target,
                "target_delta_from_fresh_deg": target_delta_from_fresh,
                "held": bool(item.get("held", False)),
                "within_drift_limit": abs(drift) <= drift_limit,
            }
        )
    return rows


def print_table(rows: list[dict]) -> None:
    columns = [
        ("key", 18),
        ("review", 9),
        ("fresh", 9),
        ("drift", 8),
        ("limit", 8),
        ("target", 9),
        ("d_fresh", 9),
        ("ok", 5),
    ]
    print("".join(label.ljust(width) for label, width in columns))
    print("".join("-" * (width - 1) + " " for _, width in columns))
    for row in rows:
        values = {
            "key": row["key"],
            "review": f"{row['review_current_deg']:.3f}",
            "fresh": f"{row['fresh_current_deg']:.3f}",
            "drift": f"{row['drift_deg']:.3f}",
            "limit": f"{row['drift_limit_deg']:.3f}",
            "target": f"{row['stage15_target_deg']:.3f}",
            "d_fresh": f"{row['target_delta_from_fresh_deg']:.3f}",
            "ok": str(row["within_drift_limit"]).lower(),
        }
        print("".join(values[label].ljust(width) for label, width in columns))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="No-send runtime preflight for Stage 16. Reads current CAN state only; never sends commands."
    )
    parser.add_argument("--dry-run-json", type=Path, required=True)
    parser.add_argument("--arm-drift-limit-deg", type=float, default=1.0)
    parser.add_argument("--gripper-drift-limit-deg", type=float, default=3.0)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    if args.arm_drift_limit_deg < 0 or args.gripper_drift_limit_deg < 0:
        raise SystemExit("Drift limits must be non-negative")

    validation = validate_dry_run(args.dry_run_json)
    current = read_current_features()
    rows = compare(
        validation["payload"]["plan"],
        current,
        args.arm_drift_limit_deg,
        args.gripper_drift_limit_deg,
    )
    blocking_rows = [row for row in rows if not row["within_drift_limit"]]
    payload = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "runtime_preflight_no_send",
        "send_allowed": False,
        "motion_allowed": False,
        "dry_run_json": str(args.dry_run_json),
        "dry_run_sha256": validation["sha256"],
        "approved_snapshot_id": APPROVED_SNAPSHOT_ID,
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no enable, disable, zero, goal, send_action, rollout, record, or replay",
        "arm_drift_limit_deg": args.arm_drift_limit_deg,
        "gripper_drift_limit_deg": args.gripper_drift_limit_deg,
        "all_within_drift_limit": not blocking_rows,
        "blocking_keys": [row["key"] for row in blocking_rows],
        "requires_separate_operator_motion_gate": True,
        "rows": rows,
    }

    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    print()
    print_table(rows)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    return 0 if payload["all_within_drift_limit"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
