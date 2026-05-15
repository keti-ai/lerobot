#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.damiao import DamiaoMotorsBus
from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase


WORK_ROOT = Path("/home/syhlabtop/openarm_folding_20260511")

ARMS = {
    "right": "can1",
    "left": "can0",
}

MOTORS = [
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6",
    "joint_7",
    "gripper",
]

LIMITS = {
    "right": {
        "joint_1": (-75.0, 75.0),
        "joint_2": (-9.0, 90.0),
        "joint_3": (-85.0, 85.0),
        "joint_4": (0.0, 135.0),
        "joint_5": (-85.0, 85.0),
        "joint_6": (-40.0, 40.0),
        "joint_7": (-80.0, 80.0),
        "gripper": (-65.0, 0.0),
    },
    "left": {
        "joint_1": (-75.0, 75.0),
        "joint_2": (-90.0, 9.0),
        "joint_3": (-85.0, 85.0),
        "joint_4": (0.0, 135.0),
        "joint_5": (-85.0, 85.0),
        "joint_6": (-40.0, 40.0),
        "joint_7": (-80.0, 80.0),
        "gripper": (-65.0, 0.0),
    },
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


def read_arm(port: str) -> dict[str, float]:
    bus = make_bus(port)
    bus.connect(handshake=False)
    try:
        states = bus.sync_read_all_states()
        return {name: float(state["position"]) for name, state in states.items()}
    finally:
        bus.disconnect(disable_torque=False)


def read_all() -> dict[str, dict[str, float]]:
    return {arm: read_arm(port) for arm, port in ARMS.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="No-send OpenArm manual direction probe.")
    parser.add_argument("--arms", nargs="+", choices=sorted(ARMS), default=["right", "left"])
    parser.add_argument("--motors", nargs="+", choices=MOTORS, default=MOTORS)
    parser.add_argument("--out-dir", type=Path, default=WORK_ROOT / "calibration")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"direction_probe_{stamp}.csv"
    json_path = out_dir / f"direction_probe_{stamp}.json"

    print("NO-SEND DIRECTION PROBE")
    print("This script reads positions only: handshake=False, no enable, no disable, no zero, no goal write.")
    print("For each prompt, gently move the named joint by hand, then press ENTER.")
    print("If anything feels unsafe or the joint resists, press Ctrl-C and stop.\n")

    rows: list[dict[str, object]] = []
    for arm in args.arms:
        for motor in args.motors:
            before_all = read_all()
            before = before_all[arm][motor]
            lo, hi = LIMITS[arm][motor]
            print(f"{arm}_{motor}: before={before:.3f} deg, review_limit=[{lo:.1f}, {hi:.1f}]")
            label = input("Move this joint slightly in the operator-defined positive/check direction, then press ENTER. Note: ")
            after_all = read_all()
            after = after_all[arm][motor]
            delta = after - before
            row = {
                "timestamp": stamp,
                "arm": arm,
                "port": ARMS[arm],
                "motor": motor,
                "feature": f"{arm}_{motor}.pos",
                "before_deg": before,
                "after_deg": after,
                "delta_deg": delta,
                "observed_sign": "positive" if delta > 0 else "negative" if delta < 0 else "zero",
                "limit_min": lo,
                "limit_max": hi,
                "operator_note": label,
                "send_allowed": "false",
                "motion_command_sent": "false",
            }
            rows.append(row)
            print(f"  after={after:.3f} deg, delta={delta:+.3f} deg\n")

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps({"rows": rows}, indent=2) + "\n")

    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
