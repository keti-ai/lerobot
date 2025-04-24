#!/bin/bash

ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045

echo "🕹️ Starting teleoperation..."
cd ..

python lerobot/scripts/control_robot.py \
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{\"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}}" \
  --control.type=teleoperate \
  --control.display_data=true

echo "✅ Teleoperation ended."
