from __future__ import annotations

import argparse
import csv
import json
import socket
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.damiao import DamiaoMotorsBus
from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase


STATE_COLUMNS = [
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


def git_text(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()


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


def read_arm_state(port: str) -> dict[str, float]:
    bus = make_bus(port)
    bus.connect(handshake=False)
    try:
        states = bus.sync_read_all_states()
        return {name: float(state["position"]) for name, state in states.items()}
    finally:
        bus.disconnect(disable_torque=False)


def capture_camera(name: str, serial: str, profiles: list[tuple[int, int, int]], out_dir: Path) -> dict:
    errors: list[str] = []
    for width, height, fps in profiles:
        pipe = rs.pipeline()
        cfg = rs.config()
        cfg.enable_device(serial)
        cfg.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
        started = False
        try:
            profile = pipe.start(cfg)
            started = True
            frame = None
            for _ in range(30):
                frames = pipe.wait_for_frames(2000)
                color = frames.get_color_frame()
                if color:
                    frame = color
            if frame is None:
                raise RuntimeError("no color frame")
            image = np.asanyarray(frame.get_data())
            image_path = out_dir / f"{name}.png"
            if not cv2.imwrite(str(image_path), image):
                raise RuntimeError(f"failed to write {image_path}")
            dev = profile.get_device()
            return {
                "name": name,
                "serial": serial,
                "path": str(image_path),
                "width": int(image.shape[1]),
                "height": int(image.shape[0]),
                "fps": fps,
                "device_name": dev.get_info(rs.camera_info.name),
                "physical_port": dev.get_info(rs.camera_info.physical_port),
                "status": "captured",
            }
        except Exception as exc:
            errors.append(f"{width}x{height}@{fps}: {exc}")
        finally:
            if started:
                pipe.stop()
                time.sleep(0.5)
    raise RuntimeError(f"{name} capture failed: {errors}")


def write_state_csv(path: Path, row: dict[str, float]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=STATE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def parse_profiles(raw: str) -> list[tuple[int, int, int]]:
    profiles = []
    for item in raw.split(","):
        resolution, fps = item.split("@", 1)
        width, height = resolution.split("x", 1)
        profiles.append((int(width), int(height), int(fps)))
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a no-send OpenArm folding trial snapshot with explicit camera serials."
    )
    parser.add_argument("--work-root", type=Path, default=Path("/home/syhlabtop/openarm_folding_20260511"))
    parser.add_argument("--repo-root", type=Path, default=Path("/home/syhlabtop/workspace/lerobot"))
    parser.add_argument("--left-wrist-serial", default="315122270766")
    parser.add_argument("--right-wrist-serial", default="230322273311")
    parser.add_argument("--base-serial", required=True)
    parser.add_argument("--base-source-alias", default="high_overview_trial")
    parser.add_argument("--base-extrinsic-trial", default="high_overview_like_full_folding_25cm_jig")
    parser.add_argument("--scene-note", default="")
    parser.add_argument("--left-port", default="can0")
    parser.add_argument("--right-port", default="can1")
    parser.add_argument("--wrist-profiles", default="1280x720@15,640x480@30")
    parser.add_argument("--base-profiles", default="640x480@30,640x480@15,1280x720@15")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    snapshot_dir = args.work_root / "shadow_snapshots" / f"snapshot_{stamp}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    camera_results = {
        "left_wrist": capture_camera(
            "left_wrist", args.left_wrist_serial, parse_profiles(args.wrist_profiles), snapshot_dir
        ),
        "right_wrist": capture_camera(
            "right_wrist", args.right_wrist_serial, parse_profiles(args.wrist_profiles), snapshot_dir
        ),
        "base": capture_camera("base", args.base_serial, parse_profiles(args.base_profiles), snapshot_dir),
    }
    camera_results["base"]["source_alias"] = args.base_source_alias

    right = read_arm_state(args.right_port)
    left = read_arm_state(args.left_port)
    state = {
        "right_joint_1.pos": right["joint_1"],
        "right_joint_2.pos": right["joint_2"],
        "right_joint_3.pos": right["joint_3"],
        "right_joint_4.pos": right["joint_4"],
        "right_joint_5.pos": right["joint_5"],
        "right_joint_6.pos": right["joint_6"],
        "right_joint_7.pos": right["joint_7"],
        "right_gripper.pos": right["gripper"],
        "left_joint_1.pos": left["joint_1"],
        "left_joint_2.pos": left["joint_2"],
        "left_joint_3.pos": left["joint_3"],
        "left_joint_4.pos": left["joint_4"],
        "left_joint_5.pos": left["joint_5"],
        "left_joint_6.pos": left["joint_6"],
        "left_joint_7.pos": left["joint_7"],
        "left_gripper.pos": left["gripper"],
    }
    write_state_csv(snapshot_dir / "state_16.csv", state)

    metadata = {
        "timestamp": stamp,
        "obs_id": f"snapshot_{stamp}",
        "hostname": socket.gethostname(),
        "repo_path": str(args.repo_root),
        "branch": git_text(args.repo_root, "branch", "--show-current"),
        "commit": git_text(args.repo_root, "rev-parse", "HEAD"),
        "work_root": str(args.work_root),
        "camera_mapping": camera_results,
        "can_mapping": {"left_arm": args.left_port, "right_arm": args.right_port},
        "state_order": STATE_COLUMNS,
        "state_units": "degrees",
        "robot_config_path": None,
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no OpenArmFollower.connect()",
        "send_allowed": False,
        "motion_allowed": False,
        "policy_computed_on_syhlabtop": False,
        "motor_commands_sent": "CAN refresh state reads only; no enable, zero, goal, torque, send_action, rollout, record, or replay",
        "base_extrinsic_trial": args.base_extrinsic_trial,
        "scene_note": args.scene_note,
        "hardware_modification_track": {
            "hf_dataset": "lerobot/openarms-hardware-modifications",
            "local_dir": str(args.work_root / "hardware_modifications"),
            "printed_parts_not_installed_for_this_snapshot": True,
        },
    }
    (snapshot_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    latest = args.work_root / "shadow_snapshots" / "latest_snapshot"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(snapshot_dir, target_is_directory=True)

    print(json.dumps({"snapshot_dir": str(snapshot_dir), "state": state, "metadata": metadata}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
