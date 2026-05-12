# Stage 35 Operator Motion Approval Draft

Date: 2026-05-12

This is a draft only. It is not approval.

## Current Gate

```text
snapshot: snapshot_20260512_171650
stage35_no_execute_validator: PASS
stage35_actual_writer: PREPARED_NOT_EXECUTED
stage35_actual_writer_ready_no_send: PASS
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

Writer readiness artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.json
sha256: 4812a9f5479ca3ae9c043a1927b299ef3a776f8ef2f4c6bed2bd0dda6a64b7c2

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.md
sha256: fca9c238457bb7d307fd17e7cd131fcb1cc1e34127a8feed3cf7bc2f3118d3d8
```

## Scope

Single guarded actuator-write test:

```text
right_arm_joints_only
selected joints: right_joint_1.pos through right_joint_7.pos
excluded: left_arm, right_gripper, left_gripper
rollout: forbidden
record: forbidden
replay-to-robot: forbidden
send_action: forbidden
```

## Exact Execute Command

Do not run unless the operator explicitly approves this exact command.

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

## Required Operator Confirmation

Before execution, the operator must confirm all of the following in the current
session:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_command_above: true
approval_phrase: SEND_STAGE35_RIGHT_ARM_JOINTS_ONCE_20260512_171650
```

## Exact Target Table

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

## Stop Conditions

Do not execute if any of these are true:

```text
fresh readback validation fails
operator is not physically at robot
power/abort control is not held
e-stop is not ready
workspace is not clear
approval phrase is missing or different
any command differs from the exact command above
```
