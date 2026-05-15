# Stage 38 Actual Write Result

Date: 2026-05-13

## Status

The operator gave explicit approval for the exact Stage 38 target table and
confirmation phrase in the live session:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage38_target_table: true
approval_phrase: SEND_STAGE38_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_130926
```

The guarded writer validated the A6000 served proposal checksum and fresh
right-arm state, then executed one right-arm joint write for
`snapshot_20260513_130926`.

```text
proposal_validation_passed: true
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

No rollout, recording, replay-to-robot, `send_action`, local PI0.5 inference,
zeroing, calibration write, left-arm command, or gripper command was run.

## Artifacts

Pre-approval refresh validation:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_pre_approval_refresh_no_send.json
sha256: 4864dcd7b93520c7ef0750df129ee431420bb3272013e5abf6cc6db63fa3bd22

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_pre_approval_refresh_no_send.md
sha256: 68e35171dc13f9a78e1aeb80548db039605d3bae6c4f8f01942763de08a6c579
```

Actual write attempt:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_actual_write_attempt.json
sha256: ceb18602cd735941b151a3330613a73116568612ad65854499927b1c76e70827

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_actual_write_attempt.md
sha256: 57cb5a5168303a07626759c6fd25decc0dde8ced480638a3cb40454cf2ea44b7
```

Post-write read-only readback:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_post_write_readback.json
sha256: 2974824af12cea6f8103ffae6d56fd89ad22bc17ef8dbe15d39591137dfa78cb

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_130926_stage38_post_write_readback.md
sha256: ff0c8ced8736e59360fc4af61f7da5429dc821f0b63a9b740a730c7ebc9b246a
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage38_served_proposal_write/snapshot_20260513_130926/
```

The A6000 copies matched the syhlabtop checksums above.

## Actual Attempt Metrics

```text
max_abs_target_delta_from_fresh_deg: 1.9218568483768954
max_abs_final_target_error_deg: 0.21701561772899525
```

| Key | Fresh current deg | Target deg | Final readback deg | Final target error deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.775741 | -4.406299 | -4.491601 | -0.085302 |
| `right_joint_2.pos` | -1.344202 | -1.201224 | -1.322345 | -0.121121 |
| `right_joint_3.pos` | 14.939218 | 15.165236 | 15.048502 | -0.116734 |
| `right_joint_4.pos` | 8.622562 | 8.816860 | 8.622562 | -0.194298 |
| `right_joint_5.pos` | -3.988891 | -3.415500 | -3.508039 | -0.092538 |
| `right_joint_6.pos` | -0.251355 | -0.134647 | -0.229498 | -0.094851 |
| `right_joint_7.pos` | -2.546333 | -0.624477 | -0.841492 | -0.217016 |

## Post-Write Readback

The post-write readback was run without `--execute`; no additional actuator
commands were sent.

The same script uses a pre-write freshness gate. After Stage 38 motion, that
gate failed for `right_joint_7.pos` because it had moved more than 1 degree
from the proposal-current pose. This blocks reuse of the same proposal and is
not a second actuator write.

```text
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
fresh_target_validation_passed: false
errors: ["fresh_target_validation_failed: ['right_joint_7.pos']"]
max_abs_remaining_to_target_deg: 0.43558500627359775
max_abs_drift_from_proposal_current_deg: 1.4644149937264022
```

| Key | Post-write current deg | Target deg | Target delta from current deg | Drift from proposal current deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.491601 | -4.406299 | 0.085302 | 0.284140 |
| `right_joint_2.pos` | -1.344202 | -1.201224 | 0.142978 | -0.000000 |
| `right_joint_3.pos` | 15.048502 | 15.165236 | 0.116734 | 0.109285 |
| `right_joint_4.pos` | 8.622562 | 8.816860 | 0.194298 | -0.000000 |
| `right_joint_5.pos` | -3.529896 | -3.415500 | 0.114395 | 0.458996 |
| `right_joint_6.pos` | -0.251355 | -0.134647 | 0.116708 | -0.000000 |
| `right_joint_7.pos` | -1.060062 | -0.624477 | 0.435585 | 1.464415 |

## Boundary

The Stage 38 served-proposal single write is complete. Further robot motion is
blocked until a fresh snapshot, A6000 no-send proposal, exact target table,
pre-write validation, and explicit operator approval are produced.

```text
stage38_single_write_attempt: DONE
stage38_post_write_readback: RECORDED_PREWRITE_GATE_EXPECTED_FAIL
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
