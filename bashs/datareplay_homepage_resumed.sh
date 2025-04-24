#!/bin/bash

# 실험 변수 설정
ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045
EXP_NAME=tape_to_box
EXP_NUM=20250424_162603
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}

# NAS 기준 경로
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared
DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/${REPO_ID}
ROOT_DIR=${NAS_MOUNT_PATH}/datasets/raw

# 날짜 기반 출력 디렉토리 예시 (훈련 출력용, 여기선 미사용)
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${EXP_NAME}

# 실행
cd ..
python lerobot/scripts/visualize_dataset_html.py \
  --repo-id=${REPO_ID} \
  --root=${DATASET_DIR} \
  --host 10.252.216.80 \
  --port 9090
