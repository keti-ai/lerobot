# Stage 35 Guarded Actual Actuator Write

Date: 2026-05-12

## Purpose

Prepare the actual Stage 35 single right-arm actuator-write path for
`snapshot_20260512_171650`.

This document does not approve motion. The writer has an execute path, but it
must not be run with `--execute` unless the operator gives a separate explicit
motion approval and confirms the physical safety checklist.

## Tool

```text
audits/openarm_folding/stage35_guarded_actual_actuator_write.py
```

The tool is fixed to:

```text
approved_snapshot_id: snapshot_20260512_171650
packet_sha256: c5411331665ea5b31a9d85de4adf27ce74f0c9596630c4cc8481e6afd58ec259
no_execute_validation_sha256: f16c0262cc7f028caa8a6a552015d4ff7e691b9bec57a509b33ef585be4bcd4d
dry_run_sha256: ef1501cad3dd3890955701d74c330e3393a1181fcbfbcba47a2a9d6100263fdc
runtime_preflight_sha256: 8b3d8df7db88eb8bdfaa9975e08cef3d91e9c0769312312cd2d969666b36d920
right_port: can1
```

Forbidden in all modes:

```text
OpenArmFollower.connect()
zeroing
calibration write
send_action
rollout
record
replay-to-robot
local PI0.5 inference on syhlabtop
```

## Non-Execute Readiness Command

This command validates the packet and performs fresh right-arm readback without
enabling torque or sending actuator commands:

```bash
cd /home/syhlabtop/workspace/lerobot
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/stage35_guarded_actual_actuator_write.py \
  --packet-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json \
  --no-execute-validation-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json \
  --json-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.json \
  --md-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.md
```

Expected non-execute result:

```text
packet_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
operator_motion_approval: NOT_GIVEN
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

## Execute Command Template

Do not run this command unless the operator gives separate explicit motion
approval for this exact command and target table.

```bash
cd /home/syhlabtop/workspace/lerobot
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/stage35_guarded_actual_actuator_write.py \
  --packet-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json \
  --no-execute-validation-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json \
  --json-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_write_attempt.json \
  --md-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_write_attempt.md \
  --execute \
  --operator-motion-approval-given \
  --operator-at-robot \
  --power-held \
  --abort-ready \
  --estop-ready \
  --confirm SEND_STAGE35_RIGHT_ARM_JOINTS_ONCE_20260512_171650
```

## Target Table

Only these right-arm joints are selected. Grippers and the left arm are
excluded.

| Key | Packet current deg | Target deg | Delta deg |
| --- | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.469744 | -5.057898 | -0.588154 |
| `right_joint_2.pos` | -1.868768 | -1.801383 | 0.067385 |
| `right_joint_3.pos` | 14.611363 | 15.022029 | 0.410666 |
| `right_joint_4.pos` | 8.272851 | 8.502065 | 0.229214 |
| `right_joint_5.pos` | -3.092757 | -2.528544 | 0.564213 |
| `right_joint_6.pos` | -0.469924 | -0.612096 | -0.142172 |
| `right_joint_7.pos` | -4.229318 | -3.921798 | 0.307520 |

Expected maximum target delta:

```text
0.5881538391113281 deg
```

## Boundary

```text
stage35_actual_writer: PREPARED_NOT_EXECUTED
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

## 2026-05-12 Non-Execute Readiness Result

syhlabtop ran the guarded actual writer without `--execute`. This validated the
packet and fresh targets, but did not enable torque and did not send actuator
commands.

Outputs:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.json
sha256: 4812a9f5479ca3ae9c043a1927b299ef3a776f8ef2f4c6bed2bd0dda6a64b7c2

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.md
sha256: fca9c238457bb7d307fd17e7cd131fcb1cc1e34127a8feed3cf7bc2f3118d3d8
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_actual_writer_ready/snapshot_20260512_171650/
```

The A6000 copies matched the syhlabtop checksums.

Result:

```text
packet_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
operator_motion_approval: NOT_GIVEN
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_fresh_drift_deg: 0.0000003661177974123575
max_abs_target_delta_from_fresh_deg: 0.5881540488490593
```

Negative execute-gate check:

```text
--operator-motion-approval-given is required
--operator-at-robot is required
--power-held is required
--abort-ready is required
--estop-ready is required
--confirm must equal SEND_STAGE35_RIGHT_ARM_JOINTS_ONCE_20260512_171650
```

The execute path remains blocked until the operator explicitly approves the
exact command in `stage35_operator_motion_approval_draft_2026-05-12.md`.

## 2026-05-12 Actual Write Result

The operator gave explicit approval in the live session for the exact command
and confirmation phrase. The guarded writer executed one right-arm joint write.

Result:

```text
packet_validation_passed: true
fresh_target_validation_passed: true
execute_requested: true
operator_motion_approval: GIVEN
send_allowed: true
motion_allowed: true
execution_allowed: true
actuator_commands_sent: true
motion_status: SINGLE_WRITE_ATTEMPTED
errors: []
```

Artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_write_attempt.json
sha256: 2b48d21086fa69da9b5d7828668b9575c7a3e12786c31716965add6982065154

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_write_attempt.md
sha256: fcb0fd677ffb9321ed5c0b6953dff42509eecae5d7ad4c67c003d370d24c0619
```

Post-write read-only readback:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_post_write_readback.json
sha256: cc59ed768aaa055ba885b3d2b2a3a50f7bfbd1548e554829fbcfcf0d9b5ca4d5

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_post_write_readback.md
sha256: 1d35caa17a17dcf24fa581726cd36eaf18277da6c7881122cf811be32a06bfed
```

The artifacts were transferred to A6000 and checksums matched:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_actual_write_attempt/snapshot_20260512_171650/
```

The post-write readback passed without additional actuator commands. Further
motion is blocked pending review.
