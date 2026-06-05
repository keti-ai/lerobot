# PI0.5 Handover v0 clean alpha-double-prime train result

마지막 갱신: 2026-06-05T16:34:01+09:00

## 요약

- run id: `pi05_handover_v0_clean_alpha2prime_20260605_015232`
- status: PASS, 30,000 steps completed
- train start: `2026-06-05 01:56:48 KST`
- train end: `2026-06-05 16:21:02 KST`
- elapsed: about `14:24:14` from train-loop start to end
- output dir: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232`
- stdout log: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232.stdout.log`
- final checkpoint: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232/checkpoints/030000/pretrained_model`

## 환경

- host: a6000 (`10.252.205.103`)
- branch: `audit/openarm-folding-baseline`
- start commit: `d1c60883 ops(a6000): A3 — start pi05 handover_v0 clean α''train (GPU1 30k)`
- env: `UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- `UV_CACHE_DIR=/tmp/uv-cache`
- torch: `2.11.0+cu128`
- cuDNN: `91900`
- GPU: GPU1 only via `CUDA_VISIBLE_DEVICES=1`
- tmux session: `pi05_handover_alpha2prime_clean` ended after training completion

## 입력

- init checkpoint: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- dataset repo id: `KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- dataset local root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30`
- policy repo id in config: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- dataset HF push source: A2b private repo, verified in `audits/openarm_folding/a6000_pi05_handover_v0_clean_alpha2prime_status_20260605_015232.md`

## 학습 설정 확인

Final checkpoint `train_config.json` confirms:

- `dataset.repo_id=KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- `dataset.root=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30`
- `dataset.video_backend=pyav`
- `policy.pretrained_path=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- `policy.use_relative_actions=True`
- `policy.relative_exclude_joints=['gripper']`
- `policy.push_to_hub=False`
- `policy.compile_model=False`
- `policy.optimizer_lr=3.75e-05`
- `policy.scheduler_warmup_steps=1000`
- `policy.scheduler_decay_steps=20000`
- `policy.scheduler_decay_lr=2.5e-06`
- `batch_size=4`
- `steps=30000`
- `save_freq=2000`
- `wandb.enable=False`

## 최종 로그

Startup reached fixed-dataset offline training:

```text
INFO 2026-06-05 01:56:48 ot_train.py:374 Output dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232
INFO 2026-06-05 01:56:48 ot_train.py:381 cfg.steps=30000 (30K)
INFO 2026-06-05 01:56:48 ot_train.py:382 dataset.num_frames=53851 (54K)
INFO 2026-06-05 01:56:48 ot_train.py:383 dataset.num_episodes=60
INFO 2026-06-05 01:56:48 ot_train.py:386 Effective batch size: 4 x 1 = 4
INFO 2026-06-05 01:56:48 ot_train.py:453 Start offline training on a fixed dataset, with effective batch size: 4
```

Final step and completion:

```text
INFO 2026-06-05 16:20:27 ot_train.py:488 step:30K smpl:120K ep:134 epch:2.23 loss:0.019 grdn:0.637 lr:2.5e-06 updt_s:1.697 data_s:0.005
INFO 2026-06-05 16:20:27 ot_train.py:502 Checkpoint policy after step 30000
INFO 2026-06-05 16:21:02 ot_train.py:576 End of training
```

Error scan of stdout found no `Traceback`, `RuntimeError`, `ERROR`, `OOM`, `out of memory`, `NaN`, or `nan` matches.

## Checkpoints

Expected 2k cadence checkpoints are present:

```text
002000
004000
006000
008000
010000
012000
014000
016000
018000
020000
022000
024000
026000
028000
030000
last -> 030000
```

Storage:

- run dir: `343G`
- stdout log: `2.4M`
- final `030000/pretrained_model`: `8.8G`
- final `030000/training_state`: `15G`

Final `030000/pretrained_model` files:

```text
config.json
model.safetensors
policy_postprocessor.json
policy_postprocessor_step_0_unnormalizer_processor.safetensors
policy_preprocessor.json
policy_preprocessor_step_3_normalizer_processor.safetensors
train_config.json
```

## 현재 상태

- Training tmux session `pi05_handover_alpha2prime_clean` is no longer running.
- GPU1 returned to idle state after completion.
- GPU0 still has existing non-A3 processes and was not touched.
- Dataset Hub repo remains private: `https://huggingface.co/datasets/KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`.
- Model checkpoint auto-push was disabled by config (`policy.push_to_hub=False`); no policy artifact was pushed to HF by this run.
- TensorBoard event files were not produced by this `lerobot-train` path with `wandb.enable=False`; progress is available from stdout log and checkpoints.

## 판정

PASS for A3 training completion.

Reasons:

- Run reached `End of training`.
- Final checkpoint `030000` exists with model, processors, config, optimizer, scheduler, RNG, and training step state.
- All expected `save_freq=2000` checkpoints are present through `030000`, and `last` points to `030000`.
- Final metric line is present at step `30K`.
- No crash/OOM/NaN/error signature was found in the stdout log.
- Final config confirms the intended clean relstats dataset, init checkpoint, relative-action recipe, no wandb, and no model-push settings.

This PASS does not select a deployment checkpoint. It only confirms that the clean alpha-double-prime training job completed cleanly.

## 다음

- Run A6 gate/replay shortlist on clean alpha-double-prime checkpoints.
- Compare A3 clean alpha-double-prime against M3 alpha-prime replay/gate results.
- Decide whether any selected policy checkpoint should be pushed to HF after evaluation.
