# OpenArm Folding Experiment Start Brief

Date: 2026-05-13
Repo head before Stage40 readiness commit: `dbab4fa2975b2be7f8aa159975556dde51cb462b`

## Current Position

```text
Stage35 first guarded right-arm write: DONE
Stage36 A6000 no-send serving bridge: PASS
Stage37 A6000 served-proposal right-arm single write: DONE
Stage38 A6000 served-proposal right-arm single write: DONE
Stage39 A6000 served-proposal right-arm single write: DONE
stage39_post_write_readback: RECORDED_PREWRITE_GATE_EXPECTED_FAIL
Stage40 A6000 served-proposal no-execute validation: PASS
Stage40 A6000 served-proposal right-arm single write: NOT_RUN
motion_status: BLOCKED
next_motion_approval: NOT_GIVEN
```

Completed results only:

- Stage35 wrote one guarded right-arm target and post-write readback passed.
- Stage36 served one no-send A6000 proposal from the corrected checkpoint.
- Stage37 wrote one guarded right-arm served proposal. Final readback max target error was `0.3649835917 deg`.
- Stage37 post-write no-execute readback recorded the new pose and blocked reuse of the old proposal.
- Stage38 wrote one guarded right-arm served proposal. Final readback max target error was `0.2170156177 deg`.
- Stage38 post-write no-execute readback recorded the new pose and blocked reuse of the old proposal.
- Stage39 wrote one guarded right-arm served proposal. Final readback max target error was `0.3152584209 deg`.
- Stage39 post-write no-execute readback recorded the new pose and blocked reuse of the old proposal.
- Stage40 captured a fresh snapshot and received an A6000 no-send served proposal.
- Stage40 no-execute validation passed with max draft delta `1.4891547268 deg`; no actuator command was sent.

Do not reuse:

```text
snapshot: snapshot_20260513_150206
proposal_sha256: e4ef68ec4acb02d05679988ce7c026531e6a697b34ae0724be2bd3b734b06854
reason: post-write freshness gate failed after motion, as expected
```

Do not reuse:

```text
snapshot: snapshot_20260513_130926
proposal_sha256: b8c6843dd3e9fde8e397f2c6f3917cdca512d4dc2c9d151da983c5d73295e182
reason: post-write freshness gate failed after motion, as expected
```

Do not reuse:

```text
snapshot: snapshot_20260512_194042
proposal_sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da
reason: post-write freshness gate failed after motion, as expected
```

Current no-execute validated draft, not approved for motion:

```text
snapshot: snapshot_20260513_152125
proposal_sha256: b600f8380260c21f101453a499325409a460ad9129c5ca38d986df92af86efab
approval_phrase: SEND_STAGE40_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_152125
status: stage40_no_execute_validation PASS, stage40_actual_write NOT_RUN
```

## Fixed Boundaries

Until explicit operator approval exists for the Stage40 exact target table:

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

The next actuator write may only be the Stage40 exact target table if the
operator gives the exact approval phrase recorded below. Otherwise, start a new
stage with a fresh snapshot, fresh A6000 proposal, new exact target table,
no-execute validation, and operator approval.

## Next Experiment Loop

Run this loop for any new attempt after Stage40:

1. Capture a fresh syhlabtop snapshot.
2. Transfer the snapshot to A6000.
3. Request an A6000 no-send proposal.
4. Build a new exact target table from that proposal.
5. Run no-execute validation against fresh current state.
6. Get explicit operator approval for that exact table and phrase.
7. Execute one guarded right-arm write only if validation and approval both pass.
8. Capture post-write readback without `--execute`.
9. Return to `motion_status: BLOCKED_FOR_REVIEW`.

Minimum acceptance before any write:

```text
proposal_all_finite: true
proposal_action_shape: [1, 30, 16]
proposal_send_allowed: false
proposal_motion_allowed: false
proposal_actuator_commands_sent: false
no_execute_validation: PASS
fresh_target_validation_passed: true
max_abs_target_delta_from_fresh_deg: <= 2.0
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

For any new actuator packet after Stage40, copy the latest guarded writer
pattern but do not reuse Stage40's hardcoded snapshot ID, proposal checksum,
target table, or confirmation phrase.

## Source Pointers

Detailed audit records remain available:

```text
Stage35 result: audits/openarm_folding/stage35_actual_write_result_2026-05-12.md
Stage36 result: audits/openarm_folding/stage36_a6000_serving_bridge_result_2026-05-12.md
Stage37 result: audits/openarm_folding/stage37_served_proposal_actual_write_result_2026-05-12.md
Stage38 readiness: audits/openarm_folding/stage38_no_send_readiness_2026-05-13.md
Stage38 approval draft: audits/openarm_folding/stage38_operator_motion_approval_draft_2026-05-13.md
Stage38 result: audits/openarm_folding/stage38_actual_write_result_2026-05-13.md
Stage39 readiness: audits/openarm_folding/stage39_no_send_readiness_2026-05-13.md
Stage39 approval draft: audits/openarm_folding/stage39_operator_motion_approval_draft_2026-05-13.md
Stage39 result: audits/openarm_folding/stage39_actual_write_result_2026-05-13.md
Stage40 readiness: audits/openarm_folding/stage40_no_send_readiness_2026-05-13.md
Stage40 approval draft: audits/openarm_folding/stage40_operator_motion_approval_draft_2026-05-13.md
Full timeline: audits/openarm_folding/timeline_status_2026-05-11.md
```

Runtime artifact roots:

```text
syhlabtop: /home/syhlabtop/openarm_folding_20260512
A6000: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```
