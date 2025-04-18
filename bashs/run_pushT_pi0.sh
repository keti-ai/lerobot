#!/bin/bash

# 1. 실험 변수 고정
ROBOT_TYPE=so100
CAMERA_SERIAL=918512073045
EXP_NAME=pusht
EXP_NUM=$(date +"%Y%m%d_%H%M%S")
REPO_ID=syhlab/${EXP_NAME}_${EXP_NUM}

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
--control.single_task='pushT_real' \
--control.repo_id=${REPO_ID} \
--control.num_episodes=5 \
--control.push_to_hub=false \
--control.warmup_time_s=2 \
--control.episode_time_s=5 \
--control.reset_time_s=5

# 3. 데이터셋 포맷 변환
python lerobot/scripts/push_dataset_to_hub.py \
--repo_id=${REPO_ID} \
--root=outputs/record \
--local-files-only=true

# 4. PI0 정책 학습
python lerobot/scripts/train.py \

--policy.type=pi0 \
--env.type=pusht \
--train.dataset.repo_id=${REPO_ID} \
--train.num_epochs=100 \
--train.batch_size=64 \
--policy.device=cuda \
--wandb.enable=true \
--policy.prompt="push the green T to the black T outline"

# 5. 평가
CHECKPOINT_DIR=$(ls -d outputs/train/*/${EXP_NAME}_pi0/checkpoints/* | sort | tail -n1)

python lerobot/scripts/eval.py \
--policy.path=${CHECKPOINT_DIR}/pretrained_model \
--env.type=pusht \
--eval.n_episodes=10 \
--policy.device=cuda

echo "✅ Experiment done: ${REPO_ID}"
