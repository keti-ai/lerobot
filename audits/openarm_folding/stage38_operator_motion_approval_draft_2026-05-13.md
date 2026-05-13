# Stage 38 Operator Motion Approval Draft

Date: 2026-05-13

This is a draft only. It is not approval.

## Source

```text
snapshot: snapshot_20260513_130926
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_a6000_served_action_proposal.json
proposal_sha256: b8c6843dd3e9fde8e397f2c6f3917cdca512d4dc2c9d151da983c5d73295e182
no_execute_validation_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_ready_no_send.json
no_execute_validation_sha256: a2b4dfa94be31b50602b09f3f32b2d41de62bbff362093aafad76e73c9503ce9
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
| `right_joint_1.pos` | -4.775741 | -4.406299 | 0.369442 |
| `right_joint_2.pos` | -1.344202 | -1.201224 | 0.142978 |
| `right_joint_3.pos` | 14.939218 | 15.165236 | 0.226019 |
| `right_joint_4.pos` | 8.622562 | 8.816860 | 0.194298 |
| `right_joint_5.pos` | -3.988891 | -3.415500 | 0.573391 |
| `right_joint_6.pos` | -0.251355 | -0.134647 | 0.116708 |
| `right_joint_7.pos` | -2.546333 | -0.624477 | 1.921857 |

Expected maximum draft delta:

```text
1.9218568483768954 deg
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
approval_applies_to_exact_stage38_target_table: true
approval_phrase: SEND_STAGE38_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_130926
```

## Boundary

```text
stage38_no_execute_validation: PASS
stage38_motion_approval: NOT_GIVEN_FOR_EXACT_TABLE
stage38_actual_write: NOT_RUN
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```
