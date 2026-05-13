# Stage 39 Operator Motion Approval Draft

Date: 2026-05-13

This is a draft only. It is not approval.

## Source

```text
snapshot: snapshot_20260513_150206
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_a6000_served_action_proposal.json
proposal_sha256: e4ef68ec4acb02d05679988ce7c026531e6a697b34ae0724be2bd3b734b06854
no_execute_validation_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_ready_no_send.json
no_execute_validation_sha256: 664488cd2405eb779bea7990d40edd05082b696a1ba7525b47a4418922c46ebe
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
| `right_joint_1.pos` | -4.491601 | -4.036126 | 0.455475 |
| `right_joint_2.pos` | -1.344202 | -0.759507 | 0.584695 |
| `right_joint_3.pos` | 15.048502 | 14.538319 | -0.510184 |
| `right_joint_4.pos` | 8.622562 | 7.540132 | -1.082431 |
| `right_joint_5.pos` | -3.529896 | -3.479749 | 0.050146 |
| `right_joint_6.pos` | -0.251355 | 0.348044 | 0.599399 |
| `right_joint_7.pos` | -1.060062 | -0.832456 | 0.227606 |

Expected maximum draft delta:

```text
1.0824308091758805 deg
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
approval_applies_to_exact_stage39_target_table: true
approval_phrase: SEND_STAGE39_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_150206
```

## Boundary

```text
stage39_no_execute_validation: PASS
stage39_motion_approval: NOT_GIVEN_FOR_EXACT_TABLE
stage39_actual_write: NOT_RUN
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```
