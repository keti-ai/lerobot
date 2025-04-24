#!/bin/bash

# 1. 실험 변수 고정
ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045
EXP_NAME=move_aroundT
EXP_NUM=20250421_162801
REPO_ID=syhlab/eval_move_aroundT_20250421_162801_20250423_173110

# NAS 기준 경로 (공유)
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared
DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/${REPO_ID}
CONVERTED_DIR=${NAS_MOUNT_PATH}/datasets/converted/${EXP_NAME}_${EXP_NUM}
CHECKPOINT_BASE=${NAS_MOUNT_PATH}/checkpoints/${EXP_NAME}_${EXP_NUM}
LOG_DIR=${NAS_MOUNT_PATH}/logs/${EXP_NAME}_${EXP_NUM}
ROOT_DIR=${NAS_MOUNT_PATH}/datasets/raw
# 날짜 기반 자동 경로 생성
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${EXP_NAME}_${POLICY_TYPE}

# --control.repo_id=${REPO_ID} \
# --control.root=${DATASET_DIR} \
cd ..
python lerobot/scripts/visualize_dataset_html.py \
  --repo-id=syhlab/eval_move_aroundT_20250421_162801_20250423_173110 \
  --root=${DATASET_DIR} \
  --host 10.252.205.103 \
  --port 9090
