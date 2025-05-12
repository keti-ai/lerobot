#!/bin/bash

# 기존 실험 정보 (수정 필요)
REPO_ID=syhlab/move_to_tape_20250509_162336  # <- 여기를 이전 수집 실험의 REPO_ID로 바꿔주세요
DATASET_DIR=/mnt/nas/lerobot_shared/datasets/raw/${REPO_ID}
ROBOT_TYPE=so100
HEAD_CAMERA_SERIAL=918512073045
HAND_CAMERA_SERIAL=218622278274

echo "📹 Resuming data recording to: ${DATASET_DIR}"
cd ..

python lerobot/scripts/control_robot.py \
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{
    \"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
    \"wrist\": {\"type\": \"intelrealsense\", \"serial_number\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
  }" \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Move to the tape" \
  --control.repo_id=${REPO_ID} \
  --control.root=${DATASET_DIR} \
  --control.num_episodes=30 \
  --control.push_to_hub=false \
  --control.resume=true \
  --control.warmup_time_s=2 \
  --control.episode_time_s=5 \
  --control.reset_time_s=3 \
  --control.display_data=true

echo "✅ Resume data collection done: ${REPO_ID}"
