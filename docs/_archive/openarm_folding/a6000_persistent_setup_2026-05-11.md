# A6000 Persistent Setup Summary

Date: 2026-05-11
Repo: `/home/syh/workspace/lerobot`
Branch: `audit/openarm-folding-baseline`

## Persistent Location

The A6000 folding baseline preparation has been persisted under:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```

Contents:

```text
models/folding_latest/
tools/
audits/
offline_inference_logs/
shadow_replays/
probevenv/
```

The previous `/tmp/lerobot_a6000` copy is now redundant after verification.

## Hugging Face Cache Decision

Use the mounted NAS Hugging Face cache:

```bash
export HF_HOME=/mnt/nas/huggingface
export HF_HUB_CACHE=/mnt/nas/huggingface/hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

Reason:

- `/mnt/nas/huggingface` has large free capacity.
- It already contains `models--google--paligemma-3b-pt-224`.
- The cached PaliGemma tokenizer resolves the previous gated-tokenizer blocker without needing a new login in this session.

Verified cached tokenizer snapshot:

```text
/mnt/nas/huggingface/hub/models--google--paligemma-3b-pt-224/snapshots/35e4f46485b4d07967e7e9935bc3786aad50687c
```

## Verified Commands

Run from the repo root:

```bash
cd /home/syh/workspace/lerobot

export HF_HOME=/mnt/nas/huggingface
export HF_HUB_CACHE=/mnt/nas/huggingface/hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

BASE=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
PY=$BASE/probevenv/bin/python
MODEL=$BASE/models/folding_latest
```

Asset probe:

```bash
$PY $BASE/tools/a6000_policy_asset_probe.py \
  --model-dir $MODEL \
  --report $BASE/audits/2026-05-11_policy_asset_probe_data.json
```

Policy load probe:

```bash
$PY $BASE/tools/a6000_policy_load_probe.py \
  --model-dir $MODEL \
  --device cuda:0 \
  --report $BASE/audits/2026-05-11_policy_load_probe_data_nas_hf.json
```

Synthetic no-robot action probe:

```bash
$PY $BASE/tools/a6000_synthetic_action_probe.py \
  --model-dir $MODEL \
  --device cuda:0 \
  --report $BASE/audits/2026-05-11_synthetic_action_probe_data_nas_hf.json
```

## Verification Results

Completed:

- Required model/config/processor files present under `/data`.
- `model.safetensors` SHA256:
  `9f33d90708cefddba05226cc6c19e77ecac2372f0415de0ddd181500129cc731`
- PI05 policy weights loaded on `cuda:0`.
- All model keys loaded successfully.
- Runtime preprocessor and postprocessor loaded successfully using NAS HF cache.
- Relative action processor is enabled.
- Gripper is excluded from relative conversion.
- Absolute action postprocessor is enabled and paired.
- Synthetic no-robot action probe produced finite action chunk.
- Raw and postprocessed action shapes are both `[1, 30, 16]`.
- `send_allowed=false` in synthetic probe output.

Still not done:

- No syhlabtop robot IO has been tested here.
- No camera/CAN/calibration hardware mapping has been verified here.
- No live shadow snapshot from syhlabtop has been replayed yet.
- No robot command, rollout, replay, recording, training, or dataset shard download was run.

## Persistent Audit Files

Key audit outputs:

```text
$BASE/audits/2026-05-11_policy_asset_probe_data.json
$BASE/audits/2026-05-11_policy_load_probe_data_nas_hf.json
$BASE/audits/2026-05-11_synthetic_action_probe_data_nas_hf.json
```

## Next Work Item

On syhlabtop:

1. Map `left_wrist`, `right_wrist`, `base` cameras.
2. Map left/right CAN interfaces and calibration IDs.
3. Produce a no-send snapshot bundle:

```text
snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

Then replay it on A6000 with:

```bash
$PY $BASE/tools/a6000_snapshot_action_review.py \
  --model-dir $MODEL \
  --snapshot-dir <SNAPSHOT_DIR> \
  --device cuda:0 \
  --csv-out $BASE/shadow_replays/<SNAPSHOT_ID>_action_review.csv \
  --json-out $BASE/shadow_replays/<SNAPSHOT_ID>_action_review.json
```
