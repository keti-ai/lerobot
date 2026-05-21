# PI0.5 handover alpha overnight train status

마지막 갱신: 2026-05-22T00:43:41+09:00
머신: ketiserver (a6000)
세션 시작: 20260522_002624

## 학습 config

- dataset: `KETI-IRRC/openarm_handover_v0_20260521_202117`
- dataset 검증: 20 episodes, 17,944 frames, 30fps, 3 cameras, 16D state/action
- policy: PI0.5 fine-tune from level2 corrected 004000
- init ckpt: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- batch_size: 4
- steps: 20000
- scheduler_decay_steps: 20000
- save_freq: 2000
- compile_model: false
- wandb: false
- output_dir: `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624`
- train log: `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624.train.log`
- push_repo: `KETI-IRRC/pi05_openarm_handover_v0_alpha`

## 환경

- HF token: `lerobot` token login confirmed; `KETI-IRRC/openarm_handover_v0_20260521_202117` refs access PASS
- D-9 update: torch `2.11.0+cu128`, cuDNN `91900` accepted for this run after no-sync Conv2d forward/backward multi-shape smoke PASS
- Python execution: `uv run --no-sync`
- video_backend: `pyav`

## GPU / serving

- `a6000_live_8766` and `a6000_snapshot_8765` were temporarily stopped before training.
- Actual training process uses GPU0 only via plain `lerobot-train`.
- Reason: the launched command is single-process `uv run --no-sync lerobot-train --policy.device=cuda`; it does not use `accelerate launch`/DDP, so CUDA defaults to GPU0.
- Impact: this preserves the requested `batch_size=4` condition. A 4-GPU restart would need a separate decision because effective batch/optimizer behavior may change.
- Current GPU sample: GPU0 97% util / 41759 MiB, GPU1-3 idle.
- Note: GPU0 also has an unrelated `trung` label backend holding about 2.4 GiB but compute idle before training start.

## TensorBoard

- Current run TensorBoard: `http://10.252.205.103:6007`
- Reason for port 6007: existing long-lived `tensorboard` session owns port 6006 for `/home/syh/workspace/lerobot/outputs/train`, but localhost 6006 probe returned no useful response for this run.
- Tmux session: `tb_pi05_handover`

## Tmux sessions

- `pi05_handover_alpha` (train)
- `tb_pi05_handover` (TensorBoard, port 6007)

## 진행 상태

- Dataset access: PASS
- 100 step check: PASS
- Current latest logged metric:
  - `step:400 smpl:2K ep:2 epch:0.09 loss:0.111 grdn:2.438 lr:1.1e-05 updt_s:1.708 data_s:0.005`
- Estimated runtime from tqdm: about 9.3 hours remaining at roughly 1.7 sec/step.
- No OOM, NaN, or traceback after training loop start.

## 초기 실패 기록

The current successful run is `20260522_002624`. Earlier attempts did not start training:

- `20260522_000625`: failed parser validation because `--policy.path` and `--policy.type` were both provided.
- `20260522_000955`: failed parser validation because `--policy.compile=false` was ambiguous.
- `20260522_001142`: failed validation because `output_dir` was pre-created while `resume=false`.

## 다음 확인

- Next manual ping: 1-2 hours later or after training finishes.
- First checkpoint expected at step 2000.
- Do not restart 8766/8765 while training is running unless the user explicitly stops training.
