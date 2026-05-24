# PI0.5 Handover alpha-prime relstats train result

마지막 갱신: 2026-05-25T04:45:19+09:00

## 요약

- run id: `pi05_handover_v0_alpha_relstats_20260522_213056`
- status: PASS, 30,000 steps completed
- train start: `2026-05-22 21:34:03 KST`
- train end: `2026-05-23 11:50:56 KST`
- elapsed: about `14:16:53` from train start to end
- output dir: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056`
- stdout log: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056.stdout.log`
- final checkpoint: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056/checkpoints/030000/pretrained_model`

## 환경

- host: a6000 (`10.252.205.103`)
- branch: `audit/openarm-folding-baseline`
- env: `UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- `UV_CACHE_DIR=/tmp/uv-cache`
- torch: `2.11.0+cu128`
- cuDNN: `91900`
- GPU: GPU1 only via `CUDA_VISIBLE_DEVICES=1`
- tmux session: `pi05_handover_alpha_relstats` ended after training completion

## 입력

- init checkpoint: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- dataset repo id: `KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- dataset local root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`
- policy repo id in config: `KETI-IRRC/pi05_openarm_handover_v0_alpha_relstats`
- dataset HF push source: M2b private repo, verified in `audits/openarm_folding/a6000_handover_v0_relstats_transform_20260522.md`

## 학습 설정 확인

Final checkpoint `train_config.json` confirms:

- `dataset.repo_id=KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- `dataset.root=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`
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
INFO 2026-05-22 21:34:03 ot_train.py:374 Output dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056
INFO 2026-05-22 21:34:03 ot_train.py:381 cfg.steps=30000 (30K)
INFO 2026-05-22 21:34:03 ot_train.py:382 dataset.num_frames=17944 (18K)
INFO 2026-05-22 21:34:03 ot_train.py:383 dataset.num_episodes=20
INFO 2026-05-22 21:34:03 ot_train.py:386 Effective batch size: 4 x 1 = 4
INFO 2026-05-22 21:34:03 ot_train.py:453 Start offline training on a fixed dataset, with effective batch size: 4
```

Final step and completion:

```text
INFO 2026-05-23 11:50:30 ot_train.py:488 step:30K smpl:120K ep:134 epch:6.69 loss:0.012 grdn:0.449 lr:2.5e-06 updt_s:1.691 data_s:0.005
INFO 2026-05-23 11:50:30 ot_train.py:502 Checkpoint policy after step 30000
INFO 2026-05-23 11:50:56 ot_train.py:576 End of training
```

Error scan of stdout found no `Traceback`, `RuntimeError`, `ERROR`, `OOM`, `out of memory`, `NaN`, `nan`, `KeyboardInterrupt`, or `Exception` matches.

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
last
```

Storage:

- run dir: `343G`
- stdout log: `2.4M`
- final `030000/pretrained_model`: `8.8G`
- final `030000/training_state`: `15G`

Final `030000` files:

```text
pretrained_model/config.json
pretrained_model/model.safetensors
pretrained_model/policy_postprocessor.json
pretrained_model/policy_postprocessor_step_0_unnormalizer_processor.safetensors
pretrained_model/policy_preprocessor.json
pretrained_model/policy_preprocessor_step_3_normalizer_processor.safetensors
pretrained_model/train_config.json
training_state/optimizer_param_groups.json
training_state/optimizer_state.safetensors
training_state/rng_state.safetensors
training_state/scheduler_state.json
training_state/training_step.json
```

## 현재 상태

- Training tmux session `pi05_handover_alpha_relstats` is no longer running.
- GPU1 is idle except Xorg-level display allocation.
- GPU0 still has the existing serving/label backend process; it was not touched.
- Dataset Hub repo remains private: `https://huggingface.co/datasets/KETI-IRRC/openarm_handover_v0_relstats_chunk30`.
- Model checkpoint auto-push was disabled by config (`policy.push_to_hub=False`); no policy artifact was pushed to HF by this run.

## 판정

PASS for M3 training completion.

Reasons:

- Run reached `End of training`.
- Final checkpoint `030000` exists with model, processor, config, optimizer, scheduler, RNG, and training step state.
- All expected `save_freq=2000` checkpoints are present through `030000`.
- Final metric line is present at step `30K`.
- No crash/OOM/NaN/error signature was found in the stdout log.
- Final config confirms the intended relstats dataset, init checkpoint, relative-action recipe, and no wandb/model-push settings.

This PASS does not select a deployment checkpoint. It only confirms that the overnight alpha-prime relstats training job completed cleanly.

## 다음

- Review TensorBoard curves for this run.
- Shortlist candidate checkpoints for M4 replay/gate.
- Decide whether to push any selected policy checkpoint to HF after evaluation.
