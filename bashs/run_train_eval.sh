#!/bin/bash

# 학습 변수
EXP_NAME=move_to_tape
EXP_NUM=20250509_162336  # ← 수집 시와 동일하게 명시
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}
HEAD_CAMERA_SERIAL=918512073045
HAND_CAMERA_SERIAL=218622278274
ROBOT_TYPE=so100
POLICY_TYPE=pi0fast

# 25.04.25
# - chunk_size: 10 (8~10 이상 권장)
# - n_action_steps: 5~50 (50은 긴 시퀀스, 5는 빠른 응답형)
# - proj_width: 1024 (논문 default)
# - max_input_seq_len: 256 (논문 default)
# - tokenizer_max_length: 48~128 (실험적으로 선택)
# - max_decoding_steps: 128 (실시간 용도에 적합)

# NAS 경로
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared

# 자동 생성되는 학습 결과 경로
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${POLICY_TYPE}

echo "🚀 Starting training with dataset: ${REPO_ID}"
cd ..
#echo "🚀 Starting training with dataset: ${REPO_ID}"
#echo "📂 Output directory: ${OUTPUT_DIR}"
#
#
## 1. 학습
#CUDA_VISIBLE_DEVICES=3 python lerobot/scripts/train.py \
#  --policy.type=${POLICY_TYPE} \
#  --policy.device=cuda \
#  --batch_size=8 \
#  --steps=50000 \
#  --dataset.repo_id=${REPO_ID} \
#  --dataset.root=${NAS_MOUNT_PATH}/datasets/raw/${REPO_ID} \
#  --policy.chunk_size=20 \
#  --policy.n_action_steps=20 \
#  --policy.proj_width=1024 \
#  --policy.tokenizer_max_length=64 \
#  --policy.max_input_seq_len=128 \
#  --policy.max_decoding_steps=64 \
#  --policy.freeze_vision_encoder=true \
#  --policy.freeze_lm_head=true \
#  --output_dir=${OUTPUT_DIR}
#
#echo "✅ Training complete: ${REPO_ID}"
#echo "📦 Checkpoints saved to: ${OUTPUT_DIR}/checkpoints/"

# 2 eval param
#
TRAINED_DATE="2025-05-13/17-08-07"
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${TRAINED_DATE}_${POLICY_TYPE}
CHECKPOINT_DIR=${OUTPUT_DIR}/checkpoints/last/pretrained_model
## 2-1. 평가 (sim)

#
##python lerobot/scripts/eval.py \
##  --policy.path=${CHECKPOINT_DIR} \
##  --env.type=pusht \
##  --eval.batch_size=1 \
##  --eval.n_episodes=20 \
##  --policy.device=cuda \
##  --policy.use_amp=false
#
## 2-2. 평가 (real)
## 새로운 평가용 EXP_NUM
NOW=$(date '+%Y%m%d_%H%M%S')
EVAL_EXP_NAME=eval_${EXP_NAME}_${EXP_NUM}_${NOW}
EVAL_DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/syhlab/${EVAL_EXP_NAME}

echo "🤖 Starting real-robot evaluation recording to: ${EVAL_DATASET_DIR}"
echo "🤖 checkpoint path: ${CHECKPOINT_DIR}"

python lerobot/scripts/control_robot.py \
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{
    \"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
    \"wrist\": {\"type\": \"intelrealsense\", \"serial_number\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
  }" \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Move to the tape" \
  --control.repo_id=syhlab/${EVAL_EXP_NAME} \
  --control.root=${EVAL_DATASET_DIR} \
  --control.num_episodes=5 \
  --control.push_to_hub=false \
  --control.warmup_time_s=2 \
  --control.episode_time_s=5 \
  --control.reset_time_s=5 \
  --control.policy.path=${CHECKPOINT_DIR} \
  --control.display_data=false

echo "✅ Real-robot evaluation complete: ${EVAL_EXP_NAME}"
echo "✅ Train & Eval complete: ${REPO_ID}"
