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
Stage40 A6000 served-proposal right-arm single write: DONE
stage40_post_write_readback: RECORDED_NO_EXECUTE_PASS
motion_status: BLOCKED_FOR_REVIEW
next_motion_approval: NOT_GIVEN
next_axis: rollout_trial_<timestamp>
new_stage_numbers: forbidden
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
- Stage40 wrote one guarded right-arm served proposal. Final readback max target error was `0.2535287095 deg`.
- Stage40 post-write no-execute readback remained within the freshness gate; Stage40 packet reuse is still forbidden because the one-time operator approval was consumed.

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

Do not reuse:

```text
snapshot: snapshot_20260513_152125
proposal_sha256: b600f8380260c21f101453a499325409a460ad9129c5ca38d986df92af86efab
reason: Stage40 single approved write is complete; post-write no-execute still passed, so reuse is blocked by the consumed one-time approval boundary
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

Any next actuator write must use a fresh snapshot, fresh A6000 proposal,
no-execute validation, and operator approval. For rollout entry, that work must
be recorded as `rollout_trial_<timestamp>/` rather than a new Stage number.

## Next Rollout Trial Loop

Run only this loop for the next attempt:

1. Create `rollout_trial_<timestamp>/`.
2. Capture a fresh syhlabtop snapshot and transfer it to A6000.
3. Request an A6000 no-send full-chunk proposal.
4. Run no-execute chunk validation and write the session envelope draft.
5. Get explicit operator approval for the rollout session envelope.
6. Execute guarded right-arm-only chunks inside the approved envelope.
7. Promote risk level only when readback and health checks remain stable.
8. Pause for soft recoverable issues or block for hard safety/integrity violations.

Minimum acceptance before any write:

```text
proposal_all_finite: true
proposal_action_shape: [1, 30, 16]
proposal_send_allowed: false
proposal_motion_allowed: false
proposal_actuator_commands_sent: false
no_execute_validation: PASS
fresh_target_validation_passed: true
metadata_sanity: PASS
right_arm_only: true
session_envelope_approval: GIVEN
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

For rollout entry, use `audits/openarm_folding/rollout_trial_guarded_session.py`.
Do not reuse Stage40's hardcoded snapshot ID, proposal checksum, target table,
or confirmation phrase.

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
Stage40 result: audits/openarm_folding/stage40_actual_write_result_2026-05-13.md
Rollout trial plan: audits/openarm_folding/rollout_trial_progressive_session_2026-05-13.md
Full timeline: audits/openarm_folding/timeline_status_2026-05-11.md
```

Runtime artifact roots:

```text
syhlabtop: /home/syhlabtop/openarm_folding_20260512
A6000: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```
