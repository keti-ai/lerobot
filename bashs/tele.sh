#!/bin/bash

ROBOT_TYPE=so100
HEAD_CAMERA_SERIAL=918512073045
HAND_CAMERA_SERIAL=218622278274

echo "🕹️ Starting teleoperation..."
#cd ..
#
#python lerobot/scripts/control_robot.py \
#  --robot.type=${ROBOT_TYPE} \
#  --robot.cameras="{
#    \"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
#    \"wrist\": {\"type\": \"intelrealsense\", \"serial_number\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
#  }" \
#  --control.type=teleoperate \
#  --control.display_data=true



sudo chmod 777 /dev/ttyACM1

sudo chmod 777 /dev/ttyACM0

python -m lerobot.teleoperate \
    --robot.type=so100_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.cameras="{
    \"head\": {\"type\": \"intelrealsense\", \"serial_number_or_name\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
    \"wrist\": {\"type\": \"intelrealsense\", \"serial_number_or_name\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
    }" \
    --robot.id=black \
    --teleop.type=so100_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=blue \
    --display_data=true

    echo "✅ Teleoperation ended."
