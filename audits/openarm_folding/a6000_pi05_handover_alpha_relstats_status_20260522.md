# PI0.5 Handover alpha-prime relstats train status

마지막 갱신: 2026-05-22T21:35:44+09:00

## 환경

- host: a6000 (`10.252.205.103`)
- branch start: `audit/openarm-folding-baseline`
- dataset HF repo: `KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- dataset local root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`
- GPU: GPU1 only via `CUDA_VISIBLE_DEVICES=1`
- tmux session: `pi05_handover_alpha_relstats`
- env: `UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- `UV_CACHE_DIR=/tmp/uv-cache`
- torch: `2.11.0+cu128`
- cuDNN: `91900`

## 명령

```bash
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
CUDA_VISIBLE_DEVICES=1 \
HF_HUB_OFFLINE=0 \
TRANSFORMERS_OFFLINE=0 \
uv run --no-sync lerobot-train \
  --policy.path=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model \
  --policy.repo_id=KETI-IRRC/pi05_openarm_handover_v0_alpha_relstats \
  --policy.device=cuda \
  --policy.compile_model=false \
  --policy.optimizer_lr=3.75e-05 \
  --policy.scheduler_warmup_steps=1000 \
  --policy.scheduler_decay_steps=20000 \
  --policy.scheduler_decay_lr=2.5e-06 \
  --policy.use_relative_actions=true \
  --policy.relative_exclude_joints='["gripper"]' \
  --policy.push_to_hub=false \
  --dataset.repo_id=KETI-IRRC/openarm_handover_v0_relstats_chunk30 \
  --dataset.root=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30 \
  --dataset.video_backend=pyav \
  --steps=30000 \
  --save_freq=2000 \
  --eval_freq=20000 \
  --batch_size=4 \
  --log_freq=200 \
  --num_workers=4 \
  --prefetch_factor=4 \
  --persistent_workers=true \
  --seed=1000 \
  --job_name=pi05_handover_v0_alpha_relstats \
  --output_dir=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056 \
  --wandb.enable=false \
  2>&1 | tee /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056.stdout.log
```

## 출력

- configured output_dir: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056`
- stdout log: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056.stdout.log`
- tmux session: `pi05_handover_alpha_relstats`
- GPU process at startup check: PID `3882868`, `/data/.../venv312_torch27_20260515/bin/python3`, GPU1 `39300MiB`

## 학습 설정

- init: level2 corrected `004000`, same as alpha
- dataset: `KETI-IRRC/openarm_handover_v0_relstats_chunk30`, loaded from local root after M2b HF push verification
- steps: `30000`
- save_freq: `2000`; expected checkpoints `002000` through `030000`
- batch_size: `4`
- optimizer lr: `3.75e-05`
- scheduler: warmup `1000`, decay steps `20000`, decay lr `2.5e-06`
- recipe: `use_relative_actions=true`, `relative_exclude_joints=["gripper"]`, PI0.5 `chunk_size=30`
- model push: disabled (`policy.push_to_hub=false`)
- wandb: disabled (`wandb.enable=false`)

## 시작 확인

Startup log reached:

```text
INFO 2026-05-22 21:34:03 ot_train.py:374 Output dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056
INFO 2026-05-22 21:34:03 ot_train.py:381 cfg.steps=30000 (30K)
INFO 2026-05-22 21:34:03 ot_train.py:382 dataset.num_frames=17944 (18K)
INFO 2026-05-22 21:34:03 ot_train.py:383 dataset.num_episodes=20
INFO 2026-05-22 21:34:03 ot_train.py:386 Effective batch size: 4 x 1 = 4
INFO 2026-05-22 21:34:03 ot_train.py:453 Start offline training on a fixed dataset, with effective batch size: 4
```

GPU check at 2026-05-22T21:35 KST:

- GPU0: existing serving/label backend unchanged, about `2454MiB`, compute idle
- GPU1: training active, about `39327MiB`, `100%` utilization
- GPU2/GPU3: no training process

## 초기 실패 기록

First tmux launch at `20260522_212924` exited immediately because plain `uv run --no-sync`
selected the repository `.venv`, where `datasets` was not installed. No training steps ran in that
attempt. The successful run above explicitly pins `UV_PROJECT_ENVIRONMENT` to the D-9 torch 2.11
environment and uses `UV_CACHE_DIR=/tmp/uv-cache`.

Failed-attempt stdout:

- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_212924.stdout.log`

## 모니터링

- log: `tail -f /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056.stdout.log`
- session: `tmux attach -t pi05_handover_alpha_relstats`
- GPU: `nvidia-smi` should show PID `3882868` on GPU1 and no new GPU0 training process
- TensorBoard can be started separately against the run directory after event files appear; existing `tb_pi05_handover` on port 6007 was not changed.

## 예상 종료

Alpha took about `9:36` for 20k steps on one A6000. This 30k run started training at
2026-05-22 21:34 KST, so expected completion is around 2026-05-23 11:45-12:00 KST if throughput
stays near the alpha run.

## 다음

- Let training run to 30k unless an OOM/NaN/traceback appears.
- On completion, add `audits/openarm_folding/a6000_pi05_handover_alpha_relstats_result_<TS>.md`.
- After user TensorBoard review, shortlist checkpoints for M4 replay/gate.
