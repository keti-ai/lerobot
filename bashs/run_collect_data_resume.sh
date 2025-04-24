#!/bin/bash

REPO_ID=syhlab/tape_to_box_20250424_162603
DATASET_DIR=/mnt/nas/lerobot_shared/datasets/raw/${REPO_ID}
ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045

echo "📹 Resuming data recording to: ${DATASET_DIR}"
cd ..

python lerobot/scripts/control_robot.py \
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{\"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}}" \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Pick up the circular black object from the left side and insert it into the open box on the right side." \
  --control.repo_id=${REPO_ID} \
  --control.root=${DATASET_DIR} \
  --control.num_episodes=10 \
  --control.push_to_hub=false \
  --control.resume=true \
  --control.warmup_time_s=2 \
  --control.episode_time_s=20 \
  --control.reset_time_s=8 \
  --control.display_data=true

echo "✅ Resume data collection done: ${REPO_ID}"
