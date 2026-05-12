# syhlabtop Stage 35 No-Execute Validation Prompt

Date: 2026-05-12

Copy this prompt to the syhlabtop agent only if the operator wants to continue
no-motion Stage 35 preparation.

---

You are the syhlabtop agent for Stage 35 no-execute validation.

This is not actuator execution. Do not move the robot.

## Current Status

```text
snapshot: snapshot_20260512_171650
stage34_runtime_preflight: PASS
stage34_execution_packet_no_send: CREATED
stage35_artifact_handoff_to_a6000: DONE
a6000_checksum_verification: MATCHED
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

## Goal

Run the Stage 35 no-execute validation tool with fresh read-only right-arm CAN
readback. The tool has no execute mode.

## Forbidden

- `OpenArmFollower.connect()`
- torque enable
- zeroing
- calibration write
- goal write
- MIT command
- actuator write
- `send_action`
- rollout
- record
- replay-to-robot
- local PI0.5 model inference on syhlabtop

## Steps

1. Sync repo:

```bash
cd /home/syhlabtop/workspace/lerobot
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
sed -n '1,220p' audits/openarm_folding/stage35_no_execute_writer_validation_2026-05-12.md
```

2. Run no-execute validation only:

```bash
cd /home/syhlabtop/workspace/lerobot
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/stage35_no_execute_writer_validation.py \
  --packet-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json \
  --read-fresh-current \
  --json-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json \
  --md-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.md
```

3. Stop and report:

```text
repo_head:
snapshot:
packet_sha256:
packet_validation_passed:
fresh_readback_validation_passed:
selected_features:
max_abs_right_arm_candidate_delta_deg:
max_abs_fresh_drift_deg:
max_abs_target_delta_from_fresh_deg:
json_out:
md_out:
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
execute_path_available: false
operator_motion_approval: NOT_GIVEN
actual_writer_status: NOT_READY
motion_status: BLOCKED
next_blocker:
```

## Interpretation

If validation fails, do not proceed. Report the blocking row.

If validation passes, motion is still blocked. The next step is only an A6000
audit update and a separate Stage 35 operator approval draft.

Do not run any actuator write from this prompt.
