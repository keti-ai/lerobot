#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import socket
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.damiao import DamiaoMotorsBus
from lerobot.robots.openarm_follower.config_openarm_follower import (
    LEFT_DEFAULT_JOINTS_LIMITS,
    RIGHT_DEFAULT_JOINTS_LIMITS,
    OpenArmFollowerConfigBase,
)


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
    **{f"right_joint_{i}.pos": "right" for i in range(1, 8)},
    "right_gripper.pos": "right",
    **{f"left_joint_{i}.pos": "left" for i in range(1, 8)},
    "left_gripper.pos": "left",
}

FEATURE_LIMITS = {
    **{f"right_{motor}.pos": limits for motor, limits in RIGHT_DEFAULT_JOINTS_LIMITS.items()},
    **{f"left_{motor}.pos": limits for motor, limits in LEFT_DEFAULT_JOINTS_LIMITS.items()},
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


def read_current_state(*, right_port: str, left_port: str) -> dict[str, float]:
    buses = {"right": make_bus(right_port), "left": make_bus(left_port)}
    result: dict[str, float] = {}
    try:
        for bus in buses.values():
            bus.connect(handshake=False)
        for side, bus in buses.items():
            states = bus.sync_read_all_states()
            for key in ACTION_NAMES:
                if FEATURE_SIDE[key] != side:
                    continue
                motor = FEATURE_TO_MOTOR[key]
                result[key] = float(states[motor]["position"])
    finally:
        for bus in buses.values():
            try:
                bus.disconnect(disable_torque=False)
            except Exception:
                pass
    return result


def state_rows(state: dict[str, float] | None) -> list[dict[str, Any]]:
    rows = []
    for key in ACTION_NAMES:
        lo, hi = FEATURE_LIMITS[key]
        value = None if state is None else state.get(key)
        margin_min = None if value is None else value - lo
        margin_max = None if value is None else hi - value
        nearest_margin = None if value is None else min(margin_min, margin_max)
        rows.append(
            {
                "key": key,
                "limit_min_deg": lo,
                "limit_max_deg": hi,
                "current_deg": value,
                "within_limit": None if value is None else lo <= value <= hi,
                "margin_to_min_deg": margin_min,
                "margin_to_max_deg": margin_max,
                "nearest_limit_margin_deg": nearest_margin,
            }
        )
    return rows


def load_events(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            row["_source"] = str(path)
            rows.append(row)
    return rows


def analyze_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actions = [row for row in rows if row.get("event") == "action_executed"]
    chunks = [row for row in rows if row.get("event") == "chunk_accepted"]
    max_commanded_key = Counter(row.get("max_abs_commanded_delta_key") for row in actions)
    max_readback_key = Counter(row.get("max_abs_readback_error_key") for row in actions)
    hard_readback_key = Counter()
    for row in actions:
        for msg in row.get("hard_readback") or []:
            key = msg.split(" readback ", 1)[0]
            hard_readback_key[key] += 1
    return {
        "action_events": len(actions),
        "chunk_events": len(chunks),
        "clipped_features": sum(int(row.get("clipped_features", 0)) for row in actions),
        "gripper_saturated_features": sum(int(row.get("gripper_saturated_features", 0)) for row in actions),
        "joint4_saturated_features": sum(int(row.get("joint4_saturated_features", 0)) for row in actions),
        "joint_limit_saturated_features": sum(int(row.get("joint_limit_saturated_features", 0)) for row in actions),
        "hard_readback_events": sum(1 for row in actions if row.get("hard_readback")),
        "soft_readback_events": sum(1 for row in actions if row.get("soft_readback")),
        "max_commanded_key_counts": max_commanded_key.most_common(),
        "max_readback_key_counts": max_readback_key.most_common(),
        "hard_readback_key_counts": hard_readback_key.most_common(),
        "top_commanded_actions": sorted(
            [
                {
                    "step_index": row.get("step_index"),
                    "key": row.get("max_abs_commanded_delta_key"),
                    "deg": row.get("max_abs_commanded_delta_deg"),
                    "readback_key": row.get("max_abs_readback_error_key"),
                    "readback_deg": row.get("max_abs_readback_error_deg"),
                    "hard_readback": row.get("hard_readback"),
                    "source": row.get("_source"),
                }
                for row in actions
            ],
            key=lambda item: float(item.get("deg") or 0.0),
            reverse=True,
        )[:12],
        "top_readback_actions": sorted(
            [
                {
                    "step_index": row.get("step_index"),
                    "key": row.get("max_abs_readback_error_key"),
                    "deg": row.get("max_abs_readback_error_deg"),
                    "commanded_key": row.get("max_abs_commanded_delta_key"),
                    "commanded_deg": row.get("max_abs_commanded_delta_deg"),
                    "hard_readback": row.get("hard_readback"),
                    "source": row.get("_source"),
                }
                for row in actions
            ],
            key=lambda item: float(item.get("deg") or 0.0),
            reverse=True,
        )[:12],
    }


def write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# OpenArm Limit/Axis Audit",
        "",
        f"timestamp: `{payload['timestamp']}`",
        f"hostname: `{payload['hostname']}`",
        "",
        "## Interpretation",
        "",
        "- Software limits match LeRobot `OpenArmFollowerConfigBase` side-specific defaults.",
        "- This audit does not prove physical hard stops. It checks current readback, log symptoms, and code contracts without actuator writes.",
        "- High saturation near a software limit can mean the policy is pushing to a legitimate boundary, or that zero/axis/sign/assembled range is misaligned.",
        "",
        "## Current Readback vs Software Limits",
        "",
        "| key | current deg | limit min | limit max | within | margin min | margin max |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in payload["state_rows"]:
        current = row["current_deg"]
        lines.append(
            "| `{key}` | {current} | {lo:.3f} | {hi:.3f} | {within} | {mmin} | {mmax} |".format(
                key=row["key"],
                current="n/a" if current is None else f"{current:.3f}",
                lo=row["limit_min_deg"],
                hi=row["limit_max_deg"],
                within="n/a" if row["within_limit"] is None else str(row["within_limit"]).lower(),
                mmin="n/a" if row["margin_to_min_deg"] is None else f"{row['margin_to_min_deg']:.3f}",
                mmax="n/a" if row["margin_to_max_deg"] is None else f"{row['margin_to_max_deg']:.3f}",
            )
        )
    a = payload["event_analysis"]
    lines.extend(
        [
            "",
            "## Rollout Log Symptoms",
            "",
            f"- action_events: `{a['action_events']}`",
            f"- chunk_events: `{a['chunk_events']}`",
            f"- clipped_features: `{a['clipped_features']}`",
            f"- gripper_saturated_features: `{a['gripper_saturated_features']}`",
            f"- joint4_saturated_features: `{a['joint4_saturated_features']}`",
            f"- joint_limit_saturated_features: `{a['joint_limit_saturated_features']}`",
            f"- hard_readback_events: `{a['hard_readback_events']}`",
            "",
            "Most common max commanded delta keys:",
        ]
    )
    for key, count in a["max_commanded_key_counts"][:10]:
        lines.append(f"- `{key}`: `{count}`")
    lines.append("")
    lines.append("Most common max readback error keys:")
    for key, count in a["max_readback_key_counts"][:10]:
        lines.append(f"- `{key}`: `{count}`")
    lines.append("")
    lines.append("Most common hard readback keys:")
    for key, count in a["hard_readback_key_counts"][:10]:
        lines.append(f"- `{key}`: `{count}`")
    lines.extend(
        [
            "",
            "## Recommended Physical Checks",
            "",
            "1. No-write readback check after manually placing each suspicious joint near neutral and near comfortable range edges.",
            "2. Direction check with very small approved pulses, one joint at a time, only after operator approval.",
            "3. For each joint, record visual positive-direction semantics, observed safe min/max, and whether the software sign matches the assembled robot.",
            "4. Do not update training/action contract until left/right order, sign, and zero convention are verified.",
            "",
            "Primary suspicious axes from logs: `left_joint_5.pos`, `left_joint_4.pos`, `left_joint_6.pos`, grippers, and joint4 limit conventions.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="No-write OpenArm limit and axis audit.")
    parser.add_argument("--work-root", type=Path, default=Path("/home/syhlabtop/openarm_folding_20260512"))
    parser.add_argument("--right-port", default="can1")
    parser.add_argument("--left-port", default="can0")
    parser.add_argument("--read-current", action="store_true")
    parser.add_argument("--events", type=Path, nargs="*", default=[])
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    events = args.events or sorted(args.work_root.glob("rollout_trial_*/live_session/events.ndjson"))
    state = read_current_state(right_port=args.right_port, left_port=args.left_port) if args.read_current else None
    payload = {
        "schema": "openarm_limit_axis_audit_v1",
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no torque enable; no actuator command",
        "torque_enabled": False,
        "actuator_commands_sent": False,
        "send_action_called": False,
        "events": [str(path) for path in events],
        "state_rows": state_rows(state),
        "event_analysis": analyze_events(load_events(events)),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_md(args.output_md, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
