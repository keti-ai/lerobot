#!/bin/bash

# 학습 변수
EXP_NAME=move_aroundT
EXP_NUM=20250421_162801  # ← 수집 시와 동일하게 명시
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}
CAMERA_SERIAL=918512073045
ROBOT_TYPE=so100
POLICY_TYPE=pi0fast

# NAS 경로
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared

# 자동 생성되는 학습 결과 경로
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${POLICY_TYPE}

echo "🚀 Starting training with dataset: ${REPO_ID} , at ${NOW}"
cd ..

# 1. 학습 (선택)
#python lerobot/scripts/train.py \
# --policy.type=pi0fast \
# --policy.device=cuda \
# --batch_size=8 \
# --steps=50000 \
# --dataset.repo_id=${REPO_ID} \
# --policy.tokenizer_max_length=32 \
# --policy.max_input_seq_len=128 \
# --policy.max_decoding_steps=128 \
# --policy.chunk_size=8 \
# --policy.freeze_vision_encoder=true \
# --policy.freeze_lm_head=true \
# --policy.proj_width=512 \
# --output_dir=${OUTPUT_DIR}


# 2-1. 평가 (sim)
TRAINED_DATE="2025-04-22/18-09-59"
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${TRAINED_DATE}_${POLICY_TYPE}
CHECKPOINT_DIR=${OUTPUT_DIR}/checkpoints/last/pretrained_model
#
#python lerobot/scripts/eval.py \
#  --policy.path=${CHECKPOINT_DIR} \
#  --env.type=pusht \
#  --eval.batch_size=1 \
#  --eval.n_episodes=20 \
#  --policy.device=cuda \
#  --policy.use_amp=false

# 2-2. 평가 (real)
# 새로운 평가용 EXP_NUM
NOW=$(date '+%Y%m%d_%H%M%S')
EVAL_EXP_NAME=eval_${EXP_NAME}_${EXP_NUM}_${NOW}
EVAL_DATASET_DIR=${NAS_MOUNT_PATH}/datasets/raw/syhlab/${EVAL_EXP_NAME}
echo "🤖 Starting real-robot evaluation recording to: ${EVAL_DATASET_DIR}"

python lerobot/scripts/control_robot.py \
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{\"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720, \"force_hardware_reset\":true}}" \
  --control.type=record \
  --control.fps=30 \
  --control.single_task="Move the object around the green T without touching it." \
  --control.repo_id=syhlab/${EVAL_EXP_NAME} \
  --control.root=${EVAL_DATASET_DIR} \
  --control.num_episodes=10 \
  --control.push_to_hub=false \
  --control.warmup_time_s=2 \
  --control.episode_time_s=10 \
  --control.reset_time_s=5 \
  --control.policy.path=${CHECKPOINT_DIR} \
  --control.display_data=false # if no error librealsense

echo "✅ Real-robot evaluation complete: ${EVAL_EXP_NAME}"

echo "✅ Train & Eval complete: ${REPO_ID}"
