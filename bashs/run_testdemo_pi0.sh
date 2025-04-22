#!/bin/bash

# 1. 실험 변수 고정
NAS_MOUNT_PATH=/mnt/nas/lerobot_shared

ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045
EXP_NAME=justmove
EXP_NUM=$(date +"%Y%m%d_%H%M%S")
#EXP_NUM=20250421_102543
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}
DATASET_DIR=outputs/record/${REPO_ID}
CONVERTED_DIR=outputs/converted/${EXP_NAME}_${EXP_NUM}

echo "🚀 Starting experiment: ${REPO_ID}"
cd ..

# 2. 데이터 수집 (record)
python lerobot/scripts/control_robot.py \
--robot.type=${ROBOT_TYPE} \
--robot.cameras="{
  \"head\": {
    \"type\": \"intelrealsense\",
    \"serial_number\": ${CAMERA_SERIAL},
    \"fps\": 30,
    \"width\": 1280,
    \"height\": 720
  }
}" \
--control.type=record \
--control.fps=30 \
--control.single_task='testdemo' \
--control.repo_id=${REPO_ID} \
--control.num_episodes=5 \
--control.push_to_hub=false \
--control.warmup_time_s=2 \
--control.episode_time_s=5 \
--control.reset_time_s=5
#
## 3. 데이터셋 포맷 변환
#python lerobot/scripts/push_dataset_to_hub.py \
#--raw-dir ${DATASET_DIR} \
#--out-dir ${CONVERTED_DIR} \
#--repo-id ${REPO_ID} \
#--raw-format pusht_zarr

# 4. PI0 정책 학습
#python lerobot/scripts/train.py \
#--policy.type=pi0fast \
#--policy.use_amp=true \
#--policy.device=cuda \
#--batch_size=2 \
#--steps=1000 \
#--dataset.repo_id=syhlab/testdemo_20250421_102543 \
#--policy.tokenizer_max_length=32 \
#--policy.max_input_seq_len=128 \
#--policy.max_decoding_steps=128 \
#--policy.chunk_size=8 \
#--policy.freeze_vision_encoder=true \
#--policy.freeze_lm_head=true \
#--policy.proj_width=512
#
#
#
## 5. 체크포인트 경로 탐색
#CHECKPOINT_DIR=$(find outputs/train -type d -path "*/checkpoints/*" | sort | tail -n1)
#if [[ -z "$CHECKPOINT_DIR" ]]; then
#  echo "❌ No checkpoint found."
#  exit 1
#fi
#
## 6. 평가
#python lerobot/scripts/eval.py \
#--policy.path=${CHECKPOINT_DIR}/pretrained_model \
#--env.type=pusht \
#--eval.n_episodes=10 \
#--eval.batch_size=10 \
#--policy.device=cuda

echo "✅ Experiment done: ${REPO_ID}"
