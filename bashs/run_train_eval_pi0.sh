#!/bin/bash

# ===== 학습 변수 =====
EXP_NAME=move_to_tape
EXP_NUM=20250509_162336  # ← 수집 시와 동일하게 명시
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}
HEAD_CAMERA_SERIAL=918512073045
HAND_CAMERA_SERIAL=218622278274
ROBOT_TYPE=so100
POLICY_TYPE=pi0
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared

# ===== 학습 경로 =====
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${POLICY_TYPE}
cd ..

echo "🚀 Starting training with dataset: ${REPO_ID}"
echo "📂 Output directory: ${OUTPUT_DIR}"

# ===== 학습 실행 =====
CUDA_VISIBLE_DEVICES=1 python lerobot/scripts/train.py \
  --policy.type=${POLICY_TYPE} \
  --policy.device=cuda \
  --batch_size=8 \
  --steps=50000 \
  --dataset.repo_id=${REPO_ID} \
  --dataset.root=${NAS_MOUNT_PATH}/datasets/raw/${REPO_ID} \
  --policy.input_features='{"observation.images.head":{"type":"VISUAL","shape":[3,720,1280]},"observation.images.wrist":{"type":"VISUAL","shape":[3,720,1280]},"observation.state":{"type":"STATE","shape":[6]}}' \
  --policy.output_features='{"action":{"type":"ACTION","shape":[6]}}' \
  --policy.train_state_proj=true \
  --policy.chunk_size=50 \
  --policy.n_action_steps=50 \
  --policy.tokenizer_max_length=128 \
  --policy.proj_width=1024 \
  --policy.freeze_vision_encoder=true \
  --output_dir=${OUTPUT_DIR}

echo "✅ Training complete: ${REPO_ID}"
echo "📦 Checkpoints saved to: ${OUTPUT_DIR}/checkpoints/"

# ===== 평가 설정 =====
# 사용 시 아래 항목 주석 해제 및 TRAINED_DATE만 변경

# TRAINED_DATE="2025-05-13/16-40-22"  # ← 변경 지점
# OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${TRAINED_DATE}_${POLICY_TYPE}
# CHECKPOINT_DIR=${OUTPUT_DIR}/checkpoints/last/pretrained_model
# NOW_EVAL=$(date '+%Y%m%d_%H%M%S')
# EVAL_EXP_NAME=eval_${EXP_NAME}_${EXP_NUM}_${NOW_EVAL}
# EVAL_DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/syhlab/${EVAL_EXP_NAME}

# ==========================
# 🚀 2-1. 평가 (sim)
# ==========================
# python lerobot/scripts/eval.py \
#   --policy.path=${CHECKPOINT_DIR} \
#   --env.type=pusht \
#   --eval.batch_size=1 \
#   --eval.n_episodes=20 \
#   --policy.device=cuda \
#   --policy.use_amp=false \
#   --policy.input_features='{"observation.images.head":{"type":"VISUAL","shape":[3,720,1280]},"observation.images.wrist":{"type":"VISUAL","shape":[3,720,1280]},"observation.state":{"type":"STATE","shape":[6]}}' \
#   --policy.output_features='{"action":{"type":"ACTION","shape":[6]}}' \
#   --policy.chunk_size=10 \
#   --policy.n_action_steps=50 \
#   --policy.tokenizer_max_length=128 \
#   --policy.train_state_proj=true \
#   --policy.proj_width=1024

# ==========================
# 🤖 2-2. 평가 (real robot)
# ==========================
# echo "🤖 Starting real-robot evaluation recording to: ${EVAL_DATASET_DIR}"
# echo "🤖 checkpoint path: ${CHECKPOINT_DIR}"

# python lerobot/scripts/control_robot.py \
#   --robot.type=${ROBOT_TYPE} \
#   --robot.cameras="{
#     \"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
#     \"wrist\": {\"type\": \"intelrealsense\", \"serial_number\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
#   }" \
#   --control.type=record \
#   --control.fps=30 \
#   --control.single_task="Move to the tape" \
#   --control.repo_id=syhlab/${EVAL_EXP_NAME} \
#   --control.root=${EVAL_DATASET_DIR} \
#   --control.num_episodes=10 \
#   --control.push_to_hub=false \
#   --control.warmup_time_s=2 \
#   --control.episode_time_s=10 \
#   --control.reset_time_s=5 \
#   --control.policy.path=${CHECKPOINT_DIR} \
#   --control.policy.input_features='{"observation.images.head":{"type":"VISUAL","shape":[3,720,1280]},"observation.images.wrist":{"type":"VISUAL","shape":[3,720,1280]},"observation.state":{"type":"STATE","shape":[6]}}' \
#   --control.policy.output_features='{"action":{"type":"ACTION","shape":[6]}}' \
#   --control.policy.chunk_size=10 \
#   --control.policy.n_action_steps=50 \
#   --control.policy.tokenizer_max_length=128 \
#   --control.policy.train_state_proj=true \
#   --control.policy.proj_width=1024 \
#   --control.display_data=false

# echo "✅ Real-robot evaluation complete: ${EVAL_EXP_NAME}"
# echo "✅ Train & Eval complete: ${REPO_ID}"
