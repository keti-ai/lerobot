# Stage 40 Operator Motion Approval Draft

Date: 2026-05-13

This is a draft only. It is not approval.

## Source

```text
snapshot: snapshot_20260513_152125
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_a6000_served_action_proposal.json
proposal_sha256: b600f8380260c21f101453a499325409a460ad9129c5ca38d986df92af86efab
no_execute_validation_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_ready_no_send.json
no_execute_validation_sha256: faabc718827bb6f27fb4ca961f4077c4de6fd3e59368f11f20f19ca813de95d4
```

## Proposed Scope

```text
right_arm_joints_only
selected joints: right_joint_1.pos through right_joint_7.pos
excluded: left_arm, right_gripper, left_gripper
rollout: forbidden
record: forbidden
replay-to-robot: forbidden
send_action: forbidden
```

## Exact Target Table

| Key | Fresh current deg | Draft target deg | Draft delta from fresh deg |
| --- | ---: | ---: | ---: |
| `right_joint_1.pos` | -3.835893 | -4.051618 | -0.215725 |
| `right_joint_2.pos` | 0.666637 | 1.116878 | 0.450241 |
| `right_joint_3.pos` | 14.676934 | 15.215549 | 0.538614 |
| `right_joint_4.pos` | 6.677295 | 8.166450 | 1.489155 |
| `right_joint_5.pos` | -3.529896 | -3.685856 | -0.155960 |
| `right_joint_6.pos` | 4.863169 | 4.412115 | -0.451054 |
| `right_joint_7.pos` | -1.256774 | -1.373927 | -0.117153 |

Expected maximum draft delta:

```text
1.4891547267763565 deg
```

## Required Confirmation Before Any Write

Before execution, the operator must confirm the exact command generated from
this draft:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage40_target_table: true
approval_phrase: SEND_STAGE40_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_152125
```

## Boundary

```text
stage40_no_execute_validation: PASS
stage40_motion_approval: NOT_GIVEN
stage40_actual_write: NOT_RUN
motion_status: BLOCKED
```
