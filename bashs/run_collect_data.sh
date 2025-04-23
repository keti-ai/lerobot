#!/bin/bash

# 항상 새로운 시간 기반 EXP_NUM
EXP_NAME=move_aroundT
NOW=$(date '+%Y%m%d_%H%M%S')
EXP_NUM=${NOW}
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}
ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045

# NAS 경로
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared
DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/${REPO_ID}

echo "📹 Starting data recording to: ${DATASET_DIR}"
cd ..

python lerobot/scripts/control_robot.py \
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{\"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}}" \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Move the object around the green T without touching it." \
  --control.repo_id=${REPO_ID} \
  --control.output_dir=${DATASET_DIR} \
  --control.num_episodes=10 \
  --control.push_to_hub=false \
  --control.warmup_time_s=2 \
  --control.episode_time_s=10 \
  --control.reset_time_s=5 \
  --control.display_data=true

echo "✅ Data collection done: ${REPO_ID}"
