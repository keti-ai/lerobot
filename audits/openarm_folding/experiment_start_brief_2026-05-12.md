# OpenArm Folding Experiment Start Brief

Date: 2026-05-13
Repo head at Stage38 start: `3d28e3d1eb7ddbecaf44fbbcb5f0075ed60d9260`

## Current Position

```text
Stage35 first guarded right-arm write: DONE
Stage36 A6000 no-send serving bridge: PASS
Stage37 A6000 served-proposal right-arm single write: DONE
Stage38 fresh snapshot and no-execute validation: PASS
stage38_actual_write: NOT_RUN
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
next_motion_approval: NOT_GIVEN
```

Completed results only:

- Stage35 wrote one guarded right-arm target and post-write readback passed.
- Stage36 served one no-send A6000 proposal from the corrected checkpoint.
- Stage37 wrote one guarded right-arm served proposal. Final readback max target error was `0.3649835917 deg`.
- Stage37 post-write no-execute readback recorded the new pose and blocked reuse of the old proposal.
- Stage38 captured a fresh snapshot, received a no-send A6000 proposal, and passed final no-execute validation. Actual write has not run.

Do not reuse:

```text
snapshot: snapshot_20260512_194042
proposal_sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da
reason: post-write freshness gate failed after motion, as expected
```

Current Stage38 candidate:

```text
snapshot: snapshot_20260513_130926
proposal_sha256: b8c6843dd3e9fde8e397f2c6f3917cdca512d4dc2c9d151da983c5d73295e182
no_execute_validation: PASS
max_abs_target_delta_from_fresh_deg: 1.9218568483768954
approval_phrase: SEND_STAGE38_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_130926
```

## Fixed Boundaries

Until a new exact target table and explicit operator approval exist:

```text
robot motion: BLOCKED
left_arm: no command
right_gripper: no command
left_gripper: no command
rollout: forbidden
record: forbidden
replay-to-robot: forbidden
send_action: forbidden
zeroing: forbidden
calibration_write: forbidden
```

The next actuator write, if approved, is the Stage38 served-proposal motion
packet. It still requires exact-table operator approval.

## Next Experiment Loop

Run only this loop for the next attempt:

1. Get explicit operator approval for the Stage38 exact target table and phrase.
2. Execute one guarded right-arm write only if fresh validation and approval both pass.
3. Capture post-write readback without `--execute`.
4. Return to `motion_status: BLOCKED_FOR_REVIEW`.

Minimum acceptance before any write:

```text
proposal_all_finite: true
proposal_action_shape: [1, 30, 16]
proposal_send_allowed: false
proposal_motion_allowed: false
proposal_actuator_commands_sent: false
no_execute_validation: PASS
fresh_target_validation_passed: true
max_abs_target_delta_from_fresh_deg: 1.9218568483768954
```

## Working Commands

Use syhlabtop for robot/camera I/O:

```bash
cd /home/syhlabtop/workspace/lerobot

source /home/syhlabtop/workspace/openarm_lerobot/scripts/env_rsusb_py312.sh

PYTHONPATH=/home/syhlabtop/workspace/lerobot/src:${PYTHONPATH} \
/home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/create_no_send_snapshot_trial.py \
  --work-root /home/syhlabtop/openarm_folding_20260512 \
  --base-serial 213622075840
```

Use A6000 only for model serving/proposal generation:

```text
server_url: http://10.252.205.103:8765/predict_snapshot
model_dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
snapshot_root: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots
```

Request a no-send proposal from syhlabtop after copying the fresh snapshot:

```bash
uv run python audits/openarm_folding/syhlabtop_snapshot_policy_client.py \
  --server-url http://10.252.205.103:8765/predict_snapshot \
  --local-snapshot-dir /home/syhlabtop/openarm_folding_20260512/shadow_snapshots/<SNAPSHOT_ID> \
  --a6000-snapshot-dir /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/<SNAPSHOT_ID> \
  --json-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/<SNAPSHOT_ID>_a6000_served_action_proposal.json \
  --md-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/<SNAPSHOT_ID>_a6000_served_action_proposal.md \
  --timeout-s 180
```

Stage38 guarded writer:

```bash
PYTHONPATH=/home/syhlabtop/workspace/lerobot:/home/syhlabtop/workspace/lerobot/src \
/home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/stage38_guarded_served_proposal_write.py \
  --proposal-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_a6000_served_action_proposal.json
```

## Source Pointers

Detailed audit records remain available:

```text
Stage35 result: audits/openarm_folding/stage35_actual_write_result_2026-05-12.md
Stage36 result: audits/openarm_folding/stage36_a6000_serving_bridge_result_2026-05-12.md
Stage37 result: audits/openarm_folding/stage37_served_proposal_actual_write_result_2026-05-12.md
Stage38 readiness: audits/openarm_folding/stage38_no_send_readiness_2026-05-13.md
Stage38 approval draft: audits/openarm_folding/stage38_operator_motion_approval_draft_2026-05-13.md
Full timeline: audits/openarm_folding/timeline_status_2026-05-11.md
```

Runtime artifact roots:

```text
syhlabtop: /home/syhlabtop/openarm_folding_20260512
A6000: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```
