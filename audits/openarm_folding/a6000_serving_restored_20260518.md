# a6000 serving 복구 기록

## 복구 시각

- 2026-05-18T11:28:29+09:00

## 원인

- 8766/8765 `/health` 가 모두 connection refused 상태였다.
- 학습 종료 후 GPU는 idle 상태였고 OOM으로 남은 프로세스는 확인되지 않았다.
- 기존 policy server 프로세스가 종료된 상태로 판단했다.

## 복구 명령

- live server: tmux session `a6000_live_8766`
- snapshot server: tmux session `a6000_snapshot_8765`
- HF offline env:
  - `HF_HOME=/mnt/nas/huggingface`
  - `HF_HUB_CACHE=/mnt/nas/huggingface/hub`
  - `HF_HUB_OFFLINE=1`
  - `TRANSFORMERS_OFFLINE=1`
- uv env: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`

## PID

- 8766 live: `2148580`
- 8765 snapshot: `2148581`

## Checkpoint

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`

## Health

### 8766 live

```json
{
  "status": "ok",
  "mode": "live",
  "checkpoint_id": "004000",
  "model_id": "pi05:pretrained_model",
  "device": "cuda:0",
  "send_allowed": false,
  "motion_allowed": false,
  "robot_config_id": "openarms_follower:16d:3cam:v1",
  "action_space_version": "openarm_folding_abs_16d_deg_v1",
  "action_normalization_id": "processor_sha256:94f781979263ad3f6d85df772d790d3d6909e6379ee47aa8e38491056082c67f"
}
```

### 8765 snapshot

```json
{
  "status": "ok",
  "device": "cuda:1",
  "send_allowed": false,
  "motion_allowed": false
}
```

## 로그

- `/tmp/a6000_serving_8766.log`
- `/tmp/a6000_serving_8765.log`

## 판정

syhlabtop Track A 는 8766 `/health` 확인 후 draft envelope 생성을 재시도할 수 있다.
