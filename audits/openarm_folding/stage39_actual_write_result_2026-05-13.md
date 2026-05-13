# Stage 39 Actual Write Result

Date: 2026-05-13

## Status

The operator gave explicit approval for the exact Stage 39 target table and
confirmation phrase in the live session:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage39_target_table: true
approval_phrase: SEND_STAGE39_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_150206
```

The guarded writer validated the A6000 served proposal checksum and fresh
right-arm state, then executed one right-arm joint write for
`snapshot_20260513_150206`.

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
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_pre_approval_refresh_no_send.json
sha256: c5e432ae1755ca717b83c9a024adabc61ca8cdadc67dbd47548741a63ebfd6b4

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_pre_approval_refresh_no_send.md
sha256: d41a2406e91a91749c42a900266d6bfea8d5ebf0e99e9baa3ad4a7d63759d2cf
```

Actual write attempt:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_actual_write_attempt.json
sha256: c46021dbc22554650bf9cb5d68a5c5e2c8e73c5055e46247b079f257d71acc2c

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_actual_write_attempt.md
sha256: 5914f742ebe5c18b1375c0791ea9c4f8c1bcc3d5f54197dded7f3407e00b76b8
```

Post-write read-only readback:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_post_write_readback.json
sha256: aa347da44cb7574dde34fab947db80a1dbb8600ac4876e57f87a242397562b21

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_post_write_readback.md
sha256: ca31d69a0b9fcd1ffcc3ca9b1e2399e7838b5fffe3e7bd6fb5cce89af83d4252
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage39_served_proposal_write/snapshot_20260513_150206/
```

The A6000 copies matched the syhlabtop checksums above.

## Actual Attempt Metrics

```text
max_abs_target_delta_from_fresh_deg: 1.0824308091758805
max_abs_final_target_error_deg: 0.31525842092096157
```

| Key | Fresh current deg | Target deg | Final readback deg | Final target error deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.491601 | -4.036126 | -4.163747 | -0.127621 |
| `right_joint_2.pos` | -1.344202 | -0.759507 | -0.950777 | -0.191270 |
| `right_joint_3.pos` | 15.048502 | 14.538319 | 14.502079 | -0.036240 |
| `right_joint_4.pos` | 8.622562 | 7.540132 | 7.420431 | -0.119701 |
| `right_joint_5.pos` | -3.529896 | -3.479749 | -3.529896 | -0.050146 |
| `right_joint_6.pos` | -0.251355 | 0.348044 | 0.032785 | -0.315258 |
| `right_joint_7.pos` | -1.060062 | -0.832456 | -1.038205 | -0.205749 |

## Post-Write Readback

The post-write readback was run without `--execute`; no additional actuator
commands were sent.

The same script uses a pre-write freshness gate. After Stage 39 motion, that
gate failed for `right_joint_4.pos` because it had moved more than 1 degree
from the proposal-current pose. This blocks reuse of the same proposal and is
not a second actuator write.

```text
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
fresh_target_validation_passed: false
errors: ["fresh_target_validation_failed: ['right_joint_4.pos']"]
max_abs_remaining_to_target_deg: 0.599398626028945
max_abs_drift_from_proposal_current_deg: 1.1802744057002936
```

| Key | Post-write current deg | Target deg | Target delta from current deg | Drift from proposal current deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.163747 | -4.036126 | 0.127621 | 0.327854 |
| `right_joint_2.pos` | -1.060062 | -0.759507 | 0.300555 | 0.284140 |
| `right_joint_3.pos` | 14.502079 | 14.538319 | 0.036240 | -0.546423 |
| `right_joint_4.pos` | 7.420431 | 7.540132 | 0.119701 | -1.180274 |
| `right_joint_5.pos` | -3.508039 | -3.479749 | 0.028289 | 0.021857 |
| `right_joint_6.pos` | -0.251355 | 0.348044 | 0.599399 | -0.000000 |
| `right_joint_7.pos` | -1.060062 | -0.832456 | 0.227606 | 0.000000 |

## Boundary

The Stage 39 served-proposal single write is complete. Further robot motion is
blocked until a fresh snapshot, A6000 no-send proposal, exact target table,
pre-write validation, and explicit operator approval are produced.

```text
stage39_single_write_attempt: DONE
stage39_post_write_readback: RECORDED_PREWRITE_GATE_EXPECTED_FAIL
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
