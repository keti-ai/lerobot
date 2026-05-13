# OpenArm Folding Audit Index

Date: 2026-05-13
Branch: `audit/openarm-folding-baseline`
Scope: metadata audit and no-motion/shadow-readiness prep for `lerobot/folding_latest`.

## Current Experiment Entry Point

Use this compact brief first:

```text
experiment_start_brief_2026-05-12.md
```

Current boundary:

```text
Stage35 first guarded right-arm write: DONE
Stage36 A6000 no-send serving bridge: PASS
Stage37 A6000 served-proposal right-arm single write: DONE
Stage38 A6000 served-proposal right-arm single write: DONE
Stage39 A6000 served-proposal right-arm single write: DONE
Stage40 A6000 served-proposal no-execute validation: PASS
Stage40 A6000 served-proposal right-arm single write: DONE
motion_status: BLOCKED_FOR_REVIEW
next_motion_approval: NOT_GIVEN
next_axis: rollout_trial_<timestamp>
new_stage_numbers: forbidden
```

The old Stage37 proposal must not be reused. The Stage38 and Stage39 proposals
must not be reused after their post-write freshness gates failed as expected.
The Stage40 proposal has also been consumed by its single approved write. Its
post-write no-execute readback still passed the freshness gate, so reuse is
forbidden by the consumed one-time approval boundary rather than by a freshness
failure. Any new experiment after Stage40 must start from a fresh snapshot and a
new A6000 no-send proposal. Rollout entry now uses `rollout_trial_<timestamp>/`
artifacts instead of new Stage numbers.

## Read Order

1. `experiment_start_brief_2026-05-12.md`
2. `rollout_trial_progressive_session_2026-05-13.md`
3. `stage40_no_send_readiness_2026-05-13.md`
4. `stage40_actual_write_result_2026-05-13.md`
5. `stage40_operator_motion_approval_draft_2026-05-13.md`
6. `stage39_no_send_readiness_2026-05-13.md`
7. `stage39_actual_write_result_2026-05-13.md`
8. `stage39_operator_motion_approval_draft_2026-05-13.md`
9. `stage38_no_send_readiness_2026-05-13.md`
10. `stage38_actual_write_result_2026-05-13.md`
11. `stage38_operator_motion_approval_draft_2026-05-13.md`
12. `timeline_status_2026-05-11.md`
13. `stage37_served_proposal_actual_write_result_2026-05-12.md`
14. `stage36_a6000_serving_bridge_result_2026-05-12.md`
15. `stage35_actual_write_result_2026-05-12.md`
16. Historical recipe/audit sources as needed:
   `artifact_audit.md`, `body_compat_matrix.md`, `shared_baseline.md`,
   `stage28_to_stage32_recovery_runbook_2026-05-11.md`.

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

Known syhlabtop repo path from the live robot PC session:

```text
/home/syhlabtop/workspace/lerobot
```

Known syhlabtop storage state from the live robot PC session:

```text
/mnt/nas/lerobot_shared: not mounted
/data: not present
/: /dev/nvme0n1p2, 468G total, 131G available
recommended work root: /home/syhlabtop/openarm_folding_20260511
```

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
