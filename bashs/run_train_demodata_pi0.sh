#!/bin/bash

# 1. 실험 변수 고정
ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045
EXP_NAME=move_aroundT
EXP_NUM=20250421_162801
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}

# NAS 기준 경로 (공유)
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared
DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/${REPO_ID}
CONVERTED_DIR=${NAS_MOUNT_PATH}/datasets/converted/${EXP_NAME}_${EXP_NUM}
CHECKPOINT_BASE=${NAS_MOUNT_PATH}/checkpoints/${EXP_NAME}_${EXP_NUM}
LOG_DIR=${NAS_MOUNT_PATH}/logs/${EXP_NAME}_${EXP_NUM}

# 날짜 기반 자동 경로 생성
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${EXP_NAME}_${POLICY_TYPE}

echo "🚀 Starting experiment: ${REPO_ID}"
cd ..

## 2. 데이터 수집 (로컬 PC)
# python lerobot/scripts/control_robot.py \
# --robot.type=${ROBOT_TYPE} \
# --robot.cameras="{\"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}}" \
# --control.type=record \
# --control.fps=30 \
# --control.single_task="Move the object around the green T without touching it." \
# --control.repo_id=${REPO_ID} \
# --control.root=${DATASET_DIR} \
# --control.num_episodes=10 \
# --control.push_to_hub=false \
# --control.warmup_time_s=2 \
# --control.episode_time_s=10 \
# --control.reset_time_s=5 \
# --control.display_data=true

## 3. 데이터셋 포맷 변환
# python lerobot/scripts/push_dataset_to_hub.py \
# --raw-dir ${DATASET_DIR} \
# --out-dir ${CONVERTED_DIR} \
# --repo-id ${REPO_ID} \
# --raw-format pusht_zarr

## 4. 정책 학습 (서버에서 실행)
POLICY_TYPE=pi0fast

python lerobot/scripts/train.py \
  --policy.type=pi0fast \
  --policy.use_amp=true \
  --policy.device=cuda \
  --batch_size=8 \
  --steps=50000 \
  --dataset.repo_id=${REPO_ID} \
  --policy.tokenizer_max_length=32 \
  --policy.max_input_seq_len=128 \
  --policy.max_decoding_steps=128 \
  --policy.chunk_size=8 \
  --policy.freeze_vision_encoder=true \
  --policy.freeze_lm_head=true \
  --policy.proj_width=512 \
  --output_dir=${OUTPUT_DIR}
#
### 5. 체크포인트 경로 설정 (평가 시)
#CHECKPOINT_DIR=${OUTPUT_DIR}/checkpoints/last/pretrained_model
#
### 6. 평가 (로컬 실행)
#python lerobot/scripts/eval.py \
#  --policy.path=${CHECKPOINT_DIR} \
#  --env.type=pusht \
#  --eval.batch_size=10 \
#  --eval.n_episodes=20 \
#  --policy.device=cuda \
#  --policy.use_amp=false

echo "✅ Experiment done: ${REPO_ID}"
