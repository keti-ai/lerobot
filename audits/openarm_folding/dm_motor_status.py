"""Damiao motor status viewer & fault recovery.

사용법:
  uv run python audits/openarm_folding/dm_motor_status.py          # 상태 출력
  uv run python audits/openarm_folding/dm_motor_status.py --reset  # disable→enable 리셋
  uv run python audits/openarm_folding/dm_motor_status.py --port can0  # 왼팔
"""

from __future__ import annotations

import argparse
import time

from lerobot.robots import openarm_follower  # noqa: F401
from lerobot.robots.openarm_follower import OpenArmFollower, OpenArmFollowerConfig

JOINTS = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7", "gripper"]


def connect(port: str, side: str):
    config = OpenArmFollowerConfig(
        id=f"openarm_{side}_status",
        port=port,
        side=side,
        max_relative_target=None,
        cameras={},
    )
    robot = OpenArmFollower(config)
    robot.connect()
    return robot


def print_states(robot, label: str = ""):
    bus = robot.bus
    # enable_torque → refresh → read states
    bus.enable_torque()
    time.sleep(0.05)

    states = bus._last_known_states  # noqa: SLF001
    print(f"\n{'='*60}")
    if label:
        print(f"  {label}")
    print(f"  {'joint':>10}  {'pos(°)':>8}  {'vel(°/s)':>9}  {'torque':>8}  {'T_mos':>7}  {'T_rotor':>8}")
    print(f"  {'-'*60}")
    for j in JOINTS:
        s = states.get(j, {})
        pos   = s.get("position",    float("nan"))
        vel   = s.get("velocity",    float("nan"))
        tau   = s.get("torque",      float("nan"))
        t_mos = s.get("temp_mos",    float("nan"))
        t_rot = s.get("temp_rotor",  float("nan"))
        flag = ""
        if t_mos > 70 or t_rot > 80:
            flag = " ⚠️ HOT"
        if abs(tau) > 25:
            flag = " ⚠️ HIGH_TORQUE"
        print(f"  {j:>10}  {pos:>8.2f}  {vel:>9.2f}  {tau:>8.3f}  {t_mos:>7.1f}  {t_rot:>8.1f}{flag}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="can1")
    parser.add_argument("--side", default="right", choices=["left", "right"])
    parser.add_argument("--reset", action="store_true",
                        help="disable → 0.5s → enable (fault 리셋)")
    args = parser.parse_args()

    robot = connect(args.port, args.side)

    print_states(robot, "현재 모터 상태")

    if args.reset:
        print("  [RESET] disable_torque ...")
        robot.bus.disable_torque()
        time.sleep(0.5)
        print("  [RESET] enable_torque ...")
        robot.bus.enable_torque()
        time.sleep(0.1)
        print_states(robot, "리셋 후 모터 상태")
        print("  리셋 완료. 관절이 응답하면 정상입니다.")

    robot.disconnect()


if __name__ == "__main__":
    main()
