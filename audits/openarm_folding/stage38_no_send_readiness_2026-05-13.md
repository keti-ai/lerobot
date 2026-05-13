# Stage 38 No-Send Readiness

Date: 2026-05-13

## Status

```text
stage38_fresh_snapshot: DONE
stage38_a6000_no_send_proposal: PASS
stage38_initial_no_execute_validation: EXPECTED_FAIL_RIGHT_JOINT_7_CAP
stage38_final_no_execute_validation: PASS
stage38_actual_write: NOT_RUN
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```

No rollout, recording, replay-to-robot, `send_action`, local PI0.5 inference,
zeroing, calibration write, left-arm command, gripper command, torque enable,
or actuator write was run.

## Snapshot

```text
snapshot: snapshot_20260513_130926
local_path: /home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260513_130926/
a6000_path: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260513_130926/
```

The snapshot capture reported one right gripper packet drop and used the last
known gripper state. Arm joint state and all three images were recorded.

Snapshot checksums:

```text
state_16.csv: 67f6b79d336951feb05e2d28b2ad2803ab6ee67e2ad3aadd7547a744407c0caf
left_wrist.png: 4f8e02cce757dddf38027fe3b36b57714a7181173f36c4bb644ef6cb38000967
right_wrist.png: 6eb48383086bd320d2522bd44878ad971db908ef992b99c4e33ce4a520832687
base.png: 44f8188eb9331ee90ab854eb5b63775e67bc23a4e423ac4319874aed4d37d65c
metadata.json: b9adf9c0d578d3c7f08dfeaee508005a60ea8d1f55be8fe028c9283a6d405a36
```

## A6000 Proposal

```text
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_a6000_served_action_proposal.json
proposal_sha256: b8c6843dd3e9fde8e397f2c6f3917cdca512d4dc2c9d151da983c5d73295e182
proposal_md_sha256: bdcb45aedc4a8055074f5ceb02a6848b1927c3ecb9cf628a667e2fddfa90d356
```

```text
all_finite: true
action_shape: [1, 30, 16]
max_abs_arm_delta_deg: 2.0491809844970703
right_joint_4_delta_deg: 0.19429779052734375
right_joint_7_delta_deg: 2.0491809844970703
left_joint_4_delta_deg: -0.6191062927246094
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
```

`right_joint_7.pos` exceeded the 2 degree cap by `0.0491809844970703 deg`.
The final Stage 38 target table caps it more conservatively to `1.9 deg` from
proposal current so fresh-current validation has margin.

## No-Execute Validation

Initial no-execute validation failed because `right_joint_7.pos` had drifted
`-0.0218568483768955 deg` from the proposal-current pose, making a strict
2 degree target cap become `2.0218568483768955 deg` from fresh current.

Initial failure artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_ready_no_send_initial_fail.json
sha256: 61fe9c6e4bd678b12bdaf9a3dab4c9df5b1882880999bcada19ec7f53e34b5d2

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_ready_no_send_initial_fail.md
sha256: 14ec87a0b04f98d3c7f0ff97b9c36eb2c9671abd3c8cf86aade65ee94f21d5b9
```

Final no-execute validation:

```text
proposal_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_target_delta_from_fresh_deg: 1.9218568483768954
max_abs_drift_from_proposal_current_deg: 0.0218568483768955
```

Final readiness artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_ready_no_send.json
sha256: a2b4dfa94be31b50602b09f3f32b2d41de62bbff362093aafad76e73c9503ce9

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_ready_no_send.md
sha256: 232ea9e7ea47efc4bfdb1ce57f07d859e495a65d4629d6f053ef0751cdf02636
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage38_served_proposal_write/snapshot_20260513_130926/
```

The A6000 copies matched the syhlabtop checksums.

## Final Target Table

| Key | Fresh current deg | A6000 proposed deg | Proposal delta deg | Draft target deg | Draft delta from fresh deg |
| --- | ---: | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.775741 | -4.406299 | 0.369442 | -4.406299 | 0.369442 |
| `right_joint_2.pos` | -1.344202 | -1.201224 | 0.142978 | -1.201224 | 0.142978 |
| `right_joint_3.pos` | 14.939218 | 15.165236 | 0.226019 | 15.165236 | 0.226019 |
| `right_joint_4.pos` | 8.622562 | 8.816860 | 0.194298 | 8.816860 | 0.194298 |
| `right_joint_5.pos` | -3.988891 | -3.415500 | 0.573391 | -3.415500 | 0.573391 |
| `right_joint_6.pos` | -0.251355 | -0.134647 | 0.116708 | -0.134647 | 0.116708 |
| `right_joint_7.pos` | -2.546333 | -0.475296 | 2.049181 | -0.624477 | 1.921857 |

## Boundary

```text
stage38_no_execute_validation: PASS
stage38_actual_write: NOT_RUN
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```
