# Stage 32 syhlabtop Candidate Transfer Precheck

Date: 2026-05-12

## Result

Stage 32 started on syhlabtop and stopped safely before model loading.

This exposed a planning correction: the baseline two-machine plan does not
require transferring the A6000 final candidate or `model.safetensors` to
syhlabtop. syhlabtop should remain the robot/camera snapshot producer, while
A6000 remains the model/inference owner.

Therefore, the missing local model is not a blocker for the baseline path. It
is only a blocker for a fallback "run model locally on syhlabtop" path, which is
not the current plan.

## syhlabtop Observed State

Repo status:

```text
repo_head: a687521ce83acdb1a5eee69ba5b8fe162bae9860
required history includes: 50078e4dff69e66acd12864b3990d954f24d6288
```

Work root:

```text
/home/syhlabtop/openarm_folding_20260512
```

Local model paths checked on syhlabtop:

```text
/home/syhlabtop/openarm_folding_20260512/models/pi05_openarm_relstats_full_004000/pretrained_model
/home/syhlabtop/openarm_folding_20260512/manifests
```

Search result:

- No transferred `pretrained_model.sha256` found under `/home/syhlabtop`.
- No transferred `model.safetensors` found under `/home/syhlabtop`.
- `/mnt/nas`, `/mnt/nas/lerobot_shared`, and `/data` were not available on
  syhlabtop.

Interpretation:

- This is acceptable for the A6000-served/offline-review path.
- syhlabtop must next create a read-only snapshot bundle and transfer that
  snapshot to A6000.
- Do not download or copy `model.safetensors` to syhlabtop unless the operator
  explicitly changes the architecture.

Stage 32 status:

```text
candidate_checksum: NOT_APPLICABLE_A6000_OWNS_MODEL
metadata_candidate_check: A6000_DONE
camera_mapping: NOT_RUN
state_order_check: NOT_RUN
snapshot_bundle: NOT_RUN
motion_status: BLOCKED
```

Safety:

- No robot IO was run.
- No camera capture was run.
- No model load was run.
- No torque/write/send path was run.

## A6000 Candidate Availability

A6000 final checkpoint remains available at:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
```

A6000 transfer packet and checksums remain available at:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/
```

Files in the transfer packet:

```text
pretrained_model.sha256
audit_artifacts.sha256
transfer_packet.md
```

The checkpoint directory contains:

```text
config.json
train_config.json
policy_preprocessor.json
policy_postprocessor.json
policy_preprocessor_step_3_normalizer_processor.safetensors
policy_postprocessor_step_0_unnormalizer_processor.safetensors
model.safetensors
```

## Corrected Next Required Step

Create a syhlabtop read-only snapshot bundle and transfer that bundle to A6000.
Do not download a replacement model on syhlabtop.

Use the updated syhlabtop prompt:

```text
audits/openarm_folding/syhlabtop_a6000_served_snapshot_handoff_prompt_2026-05-12.md
```

Expected syhlabtop snapshot layout:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

A6000 then reviews the snapshot with:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/tools/a6000_snapshot_action_review.py
```

## Blocker

The only current blocker is read-only snapshot capture on syhlabtop and
transfer of that snapshot bundle to A6000.

Robot motion remains blocked. This precheck does not authorize torque enable,
zeroing, actuator writes, rollout, replay-to-robot, or `robot.send_action()`.
