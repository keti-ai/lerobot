# Stage 37 Served Proposal Motion Approval Draft

Date: 2026-05-12

This is a draft only. It is not approval.

## Source

```text
snapshot: snapshot_20260512_194042
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_a6000_served_action_proposal.json
proposal_sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da
a6000_model_server: http://10.252.205.103:8765/predict_snapshot
```

The source proposal passed:

```text
all_finite: true
action_shape: [1, 30, 16]
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
max_abs_arm_delta_deg: 2.1111412048339844
```

## Proposed Scope

For the next guarded write, keep the same conservative scope as Stage 35:

```text
right_arm_joints_only
selected joints: right_joint_1.pos through right_joint_7.pos
excluded: left_arm, right_gripper, left_gripper
rollout: forbidden
record: forbidden
replay-to-robot: forbidden
send_action: forbidden
```

`right_joint_7.pos` exceeds the 2 degree cap by 0.111141 deg, so the draft
target below caps that joint to 2.0 deg from current. All other selected
right-arm joints use the A6000 proposal directly.

## Draft Target Table

| Key | Current deg | A6000 proposed deg | Proposal delta deg | Draft target deg | Draft delta deg |
| --- | ---: | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -5.081738 | -4.664086 | 0.417652 | -4.664086 | 0.417652 |
| `right_joint_2.pos` | -1.868768 | -1.259376 | 0.609392 | -1.259376 | 0.609392 |
| `right_joint_3.pos` | 14.939218 | 14.926427 | -0.012791 | 14.926427 | -0.012791 |
| `right_joint_4.pos` | 8.294708 | 9.506226 | 1.211517 | 9.506226 | 1.211517 |
| `right_joint_5.pos` | -2.939758 | -3.820436 | -0.880678 | -3.820436 | -0.880678 |
| `right_joint_6.pos` | -0.469924 | 0.397769 | 0.867693 | 0.397769 | 0.867693 |
| `right_joint_7.pos` | -4.032605 | -1.921464 | 2.111141 | -2.032605 | 2.000000 |

Expected maximum draft delta:

```text
2.0 deg
```

## Required Confirmation Before Any Write

Before execution, the operator must confirm the exact command generated from
this draft after a no-execute writer validation passes:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage37_target_table: true
approval_phrase: SEND_STAGE37_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260512_194042
```

## Boundary

```text
stage37_motion_approval: GIVEN_FOR_EXACT_TABLE
stage37_actual_writer: CREATED_AND_EXECUTED_ONCE
stage37_result: audits/openarm_folding/stage37_served_proposal_actual_write_result_2026-05-12.md
motion_status: BLOCKED_FOR_REVIEW
```
