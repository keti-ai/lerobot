#!/bin/bash

# 현재 스크립트가 위치한 디렉토리 절대경로
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 카메라 및 로봇 설정
ROBOT_TYPE=so100
HEAD_CAMERA_SERIAL=918512073045
HAND_CAMERA_SERIAL=218622278274

#find port

# python -m lerobot.find_port

# 포트 권한 설정
sudo chmod 777 /dev/ttyACM0
sudo chmod 777 /dev/ttyACM1

# 텔레오퍼레이션 실행
python -m lerobot.teleoperate \
    --robot.type=so100_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.calibration_dir="${SCRIPT_DIR}/../cali/lerobot/calibration/robots/so100_follower" \
    --robot.cameras="{
    \"head\": {\"type\": \"intelrealsense\", \"serial_number_or_name\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
    \"wrist\": {\"type\": \"intelrealsense\", \"serial_number_or_name\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
    }" \
    --robot.id=black \
    --teleop.type=so100_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.calibration_dir="${SCRIPT_DIR}/../cali/lerobot/calibration/teleoperators/so100_leader" \
    --teleop.id=blue \
    --display_data=true

echo "✅ Teleoperation ended."
