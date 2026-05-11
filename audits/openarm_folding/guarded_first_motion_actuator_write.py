#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.damiao import DamiaoMotorsBus
from lerobot.robots.openarm_follower.config_openarm_follower import (
    OpenArmFollowerConfigBase,
    RIGHT_DEFAULT_JOINTS_LIMITS,
)

from guarded_first_motion_runtime_preflight import sha256


APPROVED_PACKET_SHA256 = "e2627900430cda3aac90739babb35cc0ba7df8b19a89d3704ea8545505187d2f"
APPROVED_SNAPSHOT_ID = "snapshot_20260511_154554"
CONFIRMATION_PHRASE = "SEND_RIGHT_ARM_JOINTS_ONCE_20260511"
RIGHT_PORT = "can1"
SELECTED_FEATURES = [
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
]
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


def validate_packet(path: Path) -> dict:
    digest = sha256(path)
    if digest != APPROVED_PACKET_SHA256:
        raise SystemExit(f"Rejected packet checksum {digest}; expected {APPROVED_PACKET_SHA256}")
    payload = json.loads(path.read_text())
    if payload.get("mode") != "stage17_execution_packet_no_send":
        raise SystemExit(f"Rejected packet mode={payload.get('mode')!r}")
    if payload.get("approved_snapshot_id") != APPROVED_SNAPSHOT_ID:
        raise SystemExit(f"Rejected packet snapshot={payload.get('approved_snapshot_id')!r}")
    if payload.get("send_allowed") is not False:
        raise SystemExit("Rejected packet because send_allowed is not false")
    if payload.get("motion_allowed") is not False:
        raise SystemExit("Rejected packet because motion_allowed is not false")
    if payload.get("execution_allowed") is not False:
        raise SystemExit("Rejected packet because execution_allowed is not false")
    if payload.get("actuator_commands_sent") is not False:
        raise SystemExit("Rejected packet because actuator_commands_sent is not false")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("Rejected packet because rows is missing")
    by_key = {row.get("key"): row for row in rows}
    missing = [key for key in SELECTED_FEATURES if key not in by_key]
    if missing:
        raise SystemExit(f"Rejected packet because selected keys are missing: {missing}")
    forbidden = [
        key
        for key, row in by_key.items()
        if (key and key.startswith("left_")) or key in {"right_gripper.pos", "left_gripper.pos"}
        if row.get("would_send") is not False
    ]
    if forbidden:
        raise SystemExit(f"Rejected packet because forbidden rows are marked sendable: {forbidden}")
    for key, row in by_key.items():
        if row.get("would_send") is not False:
            raise SystemExit(f"Rejected packet row {key}: would_send is not false")
        if row.get("send_block_reason") != "stage17_execution_not_enabled":
            raise SystemExit(f"Rejected packet row {key}: unexpected block reason")
    return {"sha256": digest, "payload": payload, "rows_by_key": by_key}


def read_selected(bus: DamiaoMotorsBus, motors: list[str]) -> dict[str, float]:
    states = bus.sync_read_all_states(motors)
    return {motor: float(states[motor]["position"]) for motor in motors}


def build_selected_targets(packet: dict) -> list[dict]:
    rows_by_key = packet["rows_by_key"]
    selected = []
    for feature in SELECTED_FEATURES:
        motor = feature.removeprefix("right_").removesuffix(".pos")
        row = rows_by_key[feature]
        target = float(row["stage15_target_deg"])
        min_limit, max_limit = RIGHT_DEFAULT_JOINTS_LIMITS[motor]
        if not (min_limit <= target <= max_limit):
            raise SystemExit(f"Target for {feature}={target:.3f} outside [{min_limit}, {max_limit}]")
        selected.append(
            {
                "feature": feature,
                "motor": motor,
                "packet_fresh_deg": float(row["fresh_current_deg"]),
                "target_deg": target,
            }
        )
    return selected


def validate_fresh_targets(
    selected: list[dict],
    fresh: dict[str, float],
    *,
    drift_limit_deg: float,
    delta_limit_deg: float,
) -> list[dict]:
    rows = []
    tolerance = 1e-3
    for item in selected:
        motor = item["motor"]
        current = fresh[motor]
        packet_fresh = item["packet_fresh_deg"]
        target = item["target_deg"]
        drift = current - packet_fresh
        delta = target - current
        min_limit, max_limit = RIGHT_DEFAULT_JOINTS_LIMITS[motor]
        ok = (
            abs(drift) <= drift_limit_deg + tolerance
            and abs(delta) <= delta_limit_deg + tolerance
            and min_limit <= target <= max_limit
        )
        rows.append(
            {
                "feature": item["feature"],
                "motor": motor,
                "packet_fresh_deg": packet_fresh,
                "fresh_current_deg": current,
                "drift_from_packet_deg": drift,
                "target_deg": target,
                "target_delta_from_fresh_deg": delta,
                "drift_limit_deg": drift_limit_deg,
                "delta_limit_deg": delta_limit_deg,
                "limit_min_deg": min_limit,
                "limit_max_deg": max_limit,
                "validated": ok,
            }
        )
    failed = [row["feature"] for row in rows if not row["validated"]]
    if failed:
        raise SystemExit(f"Fresh target validation failed: {failed}")
    return rows


def build_commands(rows: list[dict], config: OpenArmFollowerConfigBase) -> dict[str, tuple[float, float, float, float, float]]:
    commands = {}
    for row in rows:
        motor = row["motor"]
        idx = MOTOR_INDEX[motor]
        kp = config.position_kp[idx] if isinstance(config.position_kp, list) else config.position_kp
        kd = config.position_kd[idx] if isinstance(config.position_kd, list) else config.position_kd
        commands[motor] = (float(kp), float(kd), float(row["target_deg"]), 0.0, 0.0)
    return commands


def print_table(rows: list[dict], *, would_send: bool) -> None:
    columns = [
        ("motor", 9),
        ("fresh", 9),
        ("target", 9),
        ("delta", 9),
        ("drift", 9),
        ("send", 7),
    ]
    print("".join(label.ljust(width) for label, width in columns))
    print("".join("-" * (width - 1) + " " for _, width in columns))
    for row in rows:
        values = {
            "motor": row["motor"],
            "fresh": f"{row['fresh_current_deg']:.3f}",
            "target": f"{row['target_deg']:.3f}",
            "delta": f"{row['target_delta_from_fresh_deg']:.3f}",
            "drift": f"{row['drift_from_packet_deg']:.3f}",
            "send": str(would_send).lower(),
        }
        print("".join(values[label].ljust(width) for label, width in columns))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 18 guarded right-arm actuator writer. Default mode reads and validates only."
    )
    parser.add_argument("--packet-json", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--power-held", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--hold-seconds", type=float, default=1.0)
    parser.add_argument("--drift-limit-deg", type=float, default=1.0)
    parser.add_argument("--delta-limit-deg", type=float, default=2.0)
    args = parser.parse_args()

    if args.hold_seconds < 0:
        raise SystemExit("hold-seconds must be non-negative")
    if args.execute and args.json_out is None:
        raise SystemExit("--json-out is required with --execute")
    if args.execute and not args.power_held:
        raise SystemExit("Refusing execute: pass --power-held while physically holding power/abort control")
    if args.execute and args.confirm != CONFIRMATION_PHRASE:
        raise SystemExit(f"Refusing execute: pass --confirm {CONFIRMATION_PHRASE}")

    packet = validate_packet(args.packet_json)
    selected = build_selected_targets(packet)
    selected_motors = [item["motor"] for item in selected]
    config = OpenArmFollowerConfigBase(port=RIGHT_PORT, side="right")

    payload = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "stage18_guarded_right_arm_write",
        "packet_json": str(args.packet_json),
        "packet_sha256": packet["sha256"],
        "port": RIGHT_PORT,
        "selected_motors": selected_motors,
        "excluded": ["left_arm", "right_gripper", "left_gripper"],
        "execute_requested": bool(args.execute),
        "power_held": bool(args.power_held),
        "confirmation_phrase": CONFIRMATION_PHRASE if args.execute else None,
        "send_allowed": False,
        "motion_allowed": False,
        "actuator_commands_sent": False,
        "hold_seconds": args.hold_seconds,
        "drift_limit_deg": args.drift_limit_deg,
        "delta_limit_deg": args.delta_limit_deg,
        "read_path": "DamiaoMotorsBus.connect(handshake=False); no OpenArmFollower.connect(); no calibration/zero",
        "write_path": "enable selected right-arm joints, one MIT batch, hold/readback, disable selected joints"
        if args.execute
        else "dry-run readback and target validation only",
        "rows": [],
        "post_write_readback_deg": None,
        "post_hold_readback_deg": None,
        "final_readback_deg": None,
        "errors": [],
    }

    bus = make_bus(RIGHT_PORT)
    connected = False
    try:
        bus.connect(handshake=False)
        connected = True
        fresh = read_selected(bus, selected_motors)
        rows = validate_fresh_targets(
            selected,
            fresh,
            drift_limit_deg=args.drift_limit_deg,
            delta_limit_deg=args.delta_limit_deg,
        )
        payload["rows"] = rows
        if args.execute:
            payload["send_allowed"] = True
            payload["motion_allowed"] = True
        print(json.dumps({k: v for k, v in payload.items() if k not in {"rows"}}, indent=2, sort_keys=True))
        print()
        print_table(rows, would_send=args.execute)

        if args.execute:
            commands = build_commands(rows, config)
            bus.enable_torque(selected_motors)
            bus._mit_control_batch(commands)
            payload["actuator_commands_sent"] = True
            payload["post_write_readback_deg"] = read_selected(bus, selected_motors)
            time.sleep(args.hold_seconds)
            payload["post_hold_readback_deg"] = read_selected(bus, selected_motors)
            bus.disable_torque(selected_motors, num_retry=2)
            payload["final_readback_deg"] = read_selected(bus, selected_motors)
        return 0
    except KeyboardInterrupt:
        payload["errors"].append("KeyboardInterrupt")
        raise
    except Exception as exc:
        payload["errors"].append(repr(exc))
        raise
    finally:
        if connected and args.execute:
            try:
                bus.disable_torque(selected_motors, num_retry=2)
            except Exception as exc:
                payload["errors"].append(f"final_disable_failed: {exc!r}")
        if connected:
            try:
                bus.disconnect(disable_torque=False)
            except Exception as exc:
                payload["errors"].append(f"disconnect_failed: {exc!r}")
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
