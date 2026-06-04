# PI0.5 Handover v0 clean alpha-double-prime 학습 시작

마지막 갱신: 2026-06-05T01:58:00+09:00

## A2b HF Push

- repo: `https://huggingface.co/datasets/KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- upload source: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30`
- upload command: `huggingface-cli upload KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30 <target_root> --repo-type=dataset --private`
- commit message: `initial upload — clean (60 ep) relstats variant`
- HF whoami: `syh4661`
- org access: `KETI-IRRC`

Hub verification:

- `private=True`
- file count: `42`
- `.relstats_complete` in repo files: `True`
- `meta/stats.json` in repo files: `True`
- `action.mean[:4]=[-0.4048439860343933, 0.7029255628585815, 0.3244377672672272, 0.5263494849205017]`
- `action.q01[:4]=[-42.884531908215216, -20.018216276168822, -28.99037908713023, -60.71202855791364]`
- `action.q99[:4]=[36.48783746802285, 29.808138561248754, 33.463866707130656, 55.97401901245114]`
- converted action mean abs max: `1.4375325441360474`
- converted action q01/q99 abs max: `60.71202855791364`

A2b 판정: PASS. Dataset HF push completed as private, and marker/stats were verified from the Hub.

## 환경

- host: a6000 (`10.252.205.103`)
- branch start: `audit/openarm-folding-baseline`
- start commit: `79c4d3a7 docs(status): A2 verification PASS — mean_abs_max=1.44 (+81% vs M2 multi-object 효과)`
- dataset HF repo: `KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- dataset local root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30`
- GPU: GPU1 only via `CUDA_VISIBLE_DEVICES=1`
- GPU 선택 사유: start check에서 GPU1/GPU2/GPU3 모두 `48262 MiB` free, `0%` util. 이전 M3와 같은 안정 경로를 유지하기 위해 GPU1 선택.
- tmux session: `pi05_handover_alpha2prime_clean`
- train script: `/tmp/a3_train_20260605_015232.sh`
- env: `UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- `UV_CACHE_DIR=/tmp/uv-cache`
- torch: `2.11.0+cu128`
- cuDNN: `91900`

## 명령

```bash
#!/bin/bash
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
CUDA_VISIBLE_DEVICES=1 \
HF_HUB_OFFLINE=0 \
TRANSFORMERS_OFFLINE=0 \
uv run --no-sync lerobot-train \
  --policy.path=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model \
  --policy.repo_id=KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime \
  --policy.device=cuda \
  --policy.compile_model=false \
  --policy.optimizer_lr=3.75e-05 \
  --policy.scheduler_warmup_steps=1000 \
  --policy.scheduler_decay_steps=20000 \
  --policy.scheduler_decay_lr=2.5e-06 \
  --policy.use_relative_actions=true \
  --policy.relative_exclude_joints='["gripper"]' \
  --policy.push_to_hub=false \
  --dataset.repo_id=KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30 \
  --dataset.root=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30 \
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
  --job_name=pi05_handover_v0_clean_alpha2prime \
  --output_dir=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232 \
  --wandb.enable=false \
  2>&1 | tee /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232.stdout.log
```

Launch:

```bash
tmux new-session -d -s pi05_handover_alpha2prime_clean /tmp/a3_train_20260605_015232.sh
```

## 출력 path

- output_dir: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232`
- stdout log: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232.stdout.log`
- tmux session: `pi05_handover_alpha2prime_clean`
- GPU process at startup check: PID `2903732`, `/data/.../venv312_torch27_20260515/bin/python3`, GPU1 `39300MiB`

## 학습 설정 요약

- init: level2 corrected `004000`, same init lineage as alpha and alpha-prime
- dataset: clean 60 ep relstats variant, `KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- local dataset root: A2 target root under `/data/keti/syh/.../datasets/openarm_handover_v0_clean_relstats_chunk30`
- steps: `30000`
- save_freq: `2000`; expected checkpoints `002000` through `030000`
- eval_freq: `20000`
- batch_size: `4`
- optimizer lr: `3.75e-05`
- scheduler: warmup `1000`, decay steps `20000`, decay lr `2.5e-06`
- recipe: `use_relative_actions=true`, `relative_exclude_joints=["gripper"]`, PI0.5 `chunk_size=30`
- model push: disabled (`policy.push_to_hub=false`)
- wandb: disabled (`wandb.enable=false`)

## 시작 확인

Startup log reached:

```text
INFO 2026-06-05 01:56:48 ot_train.py:374 Output dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232
INFO 2026-06-05 01:56:48 ot_train.py:381 cfg.steps=30000 (30K)
INFO 2026-06-05 01:56:48 ot_train.py:382 dataset.num_frames=53851 (54K)
INFO 2026-06-05 01:56:48 ot_train.py:383 dataset.num_episodes=60
INFO 2026-06-05 01:56:48 ot_train.py:386 Effective batch size: 4 x 1 = 4
INFO 2026-06-05 01:56:48 ot_train.py:453 Start offline training on a fixed dataset, with effective batch size: 4
Training: 0%|          | 31/30000 [01:08<14:01:01,  1.68s/step]
```

Startup note:

- Policy loading took about three minutes before CUDA memory appeared.
- No immediate traceback/OOM/NaN appeared in the first startup window.
- `use_relative_actions=true` warning appeared and the trainer rebuilt processors from current policy config, matching the intended relative-action recipe.

## GPU check 결과

Initial free-GPU check before launch:

| GPU | memory.free MiB | utilization % | decision |
| ---: | ---: | ---: | --- |
| 0 | 37772 | 98 | occupied; left untouched |
| 1 | 48262 | 0 | selected |
| 2 | 48262 | 0 | free, unused |
| 3 | 48262 | 0 | free, unused |

Startup check after train loop:

| GPU | memory.used MiB | memory.free MiB | utilization % |
| ---: | ---: | ---: | ---: |
| 0 | 10779 | 37772 | 100 |
| 1 | 39594 | 8957 | 100 |
| 2 | 289 | 48262 | 0 |
| 3 | 289 | 48262 | 0 |

GPU1 process:

```text
GPU1 PID 2903732 .../venv312_torch27_20260515/bin/python3 39300MiB
```

## 모니터링

- log: `tail -f /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232.stdout.log`
- session: `tmux attach -t pi05_handover_alpha2prime_clean`
- GPU: `nvidia-smi` should show PID `2903732` on GPU1 and no new GPU0 training process
- TensorBoard can be started separately against the run directory after event files appear. Existing `tb_pi05_handover` was not changed.

## 예상 종료

Alpha-prime M3 took about `14h17m` for 30k steps. This run entered the train loop at
2026-06-05 01:56:48 KST, so expected completion is around 2026-06-05 16:14 KST if throughput
stays similar.

## 다음

- Let training run to 30k unless an OOM/NaN/traceback appears.
- On completion, add `audits/openarm_folding/a6000_pi05_handover_v0_clean_alpha2prime_result_<TS>.md`.
- A4/A5/D-41 follow-up prompts can proceed while A3 runs.
- After completion, run A6 gate/replay shortlist on clean alpha-double-prime checkpoints.
