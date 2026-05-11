# OpenArm Folding Audit Index

Date: 2026-05-11
Branch: `audit/openarm-folding-baseline`
Scope: metadata audit and no-motion/shadow-readiness prep for `lerobot/folding_latest`.

## Read Order

1. `artifact_audit.md`
2. `body_compat_matrix.md`
3. `shared_baseline.md`
4. `two_machine_pipeline_2026-05-11.md`
5. `robot_test_work_spec_2026-05-11.md`
6. `a6000_persistent_setup_2026-05-11.md`
7. `syhlabtop_work_prompt_2026-05-11.md`

## Storage Policy

Keep source-controlled docs in this directory.

Keep large runtime assets out of the repo:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```

This path is A6000-local persistent storage. Do not assume `syhlabtop` can write to it directly.

Use the mounted NAS Hugging Face cache for tokenizer/model dependency cache:

```bash
export HF_HOME=/mnt/nas/huggingface
export HF_HUB_CACHE=/mnt/nas/huggingface/hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

Do not use `/tmp` as the canonical location for tomorrow's work. `/tmp` is scratch only.

For cross-machine exchange, prefer the NAS share only after confirming it is mounted on both machines:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511
```

Current NAS share copy:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511/audits/
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/
/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/
```

Until the syhlabtop mount is confirmed, write syhlabtop artifacts under a local `<syhlabtop-work-root>` and transfer snapshots to A6000 with `rsync`, `scp`, or the mounted NAS share.

## Current A6000 Status

Verified from the persistent `/data` setup:

- Required `lerobot/folding_latest` config, model, and processor files are present.
- PI05 weights load on `cuda:0`.
- Runtime preprocessor and postprocessor load using NAS HF cache.
- Synthetic no-robot action probe returns finite `[1, 30, 16]` actions.
- `send_allowed=false` is recorded in the synthetic probe output.

Not performed:

- No robot IO.
- No rollout/replay/record command.
- No training.
- No full dataset or video shard download.

## Canonical A6000 Commands

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

## Next Syhlabtop Item

Use `syhlabtop` only for robot IO and sensor snapshots. The next required artifact is a no-send snapshot bundle:

```text
snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

Transfer that snapshot to the A6000 side, then review it with:

```bash
$PY $BASE/tools/a6000_snapshot_action_review.py \
  --model-dir $MODEL \
  --snapshot-dir <SNAPSHOT_DIR> \
  --device cuda:0 \
  --csv-out $BASE/shadow_replays/<SNAPSHOT_ID>_action_review.csv \
  --json-out $BASE/shadow_replays/<SNAPSHOT_ID>_action_review.json
```

The output remains an action proposal for review only. It is not an actuator command.
