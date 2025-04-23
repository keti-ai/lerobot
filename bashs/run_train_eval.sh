#!/bin/bash

# 학습 변수
EXP_NAME=move_aroundT
EXP_NUM=20250422_172000  # ← 수집 시와 동일하게 명시
POLICY_TYPE=pi0fast
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}

# NAS 경로
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared

# 자동 생성되는 학습 결과 경로
NOW=$(date '+%Y-%m-%d/%H-%M-%S')
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${NOW}_${POLICY_TYPE}

echo "🚀 Starting training with dataset: ${REPO_ID}"
cd ..

# 1. 학습 (선택)
# python lerobot/scripts/train.py \
#   --policy.type=${POLICY_TYPE} \
#   --policy.device=cuda \
#   --batch_size=8 \
#   --steps=50000 \
#   --dataset.repo_id=${REPO_ID} \
#   --policy.tokenizer_max_length=32 \
#   --policy.max_input_seq_len=128 \
#   --policy.max_decoding_steps=128 \
#   --policy.chunk_size=8 \
#   --policy.freeze_vision_encoder=true \
#   --policy.freeze_lm_head=true \
#   --policy.proj_width=512 \
#   --output_dir=${OUTPUT_DIR}

# 2. 평가
TRAINED_DATE="2025-04-22/18-09-59"
OUTPUT_DIR=${NAS_MOUNT_PATH}/outputs/train/${TRAINED_DATE}_${POLICY_TYPE}
CHECKPOINT_DIR=${OUTPUT_DIR}/checkpoints/last/pretrained_model

python lerobot/scripts/eval.py \
  --policy.path=${CHECKPOINT_DIR} \
  --env.type=pusht \
  --eval.batch_size=1 \
  --eval.n_episodes=20 \
  --policy.device=cuda \
  --policy.use_amp=false

echo "✅ Train & Eval complete: ${REPO_ID}"
