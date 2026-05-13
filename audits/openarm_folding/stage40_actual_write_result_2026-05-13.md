# Stage 40 Actual Write Result

Date: 2026-05-13

## Status

The operator gave explicit approval for the exact Stage 40 target table and
confirmation phrase in the live session:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage40_target_table: true
approval_phrase: SEND_STAGE40_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_152125
```

The guarded writer validated the A6000 served proposal checksum and fresh
right-arm state, then executed one right-arm joint write for
`snapshot_20260513_152125`.

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

Actual write attempt:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_actual_write.json
sha256: 8ac9711d4577ccdbc2f94067442aed3102e9a64f65e8ddf58086bdb7a8431608

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_actual_write.md
sha256: 0da51cd4b6a1277d281de73ffc462b9f1c256f278376511c9a908aec3b8456e1
```

Post-write read-only validation:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_post_write_no_execute_validation.json
sha256: e802c222282153183d37768809511c9d9866a33ffaf6121b873f314a3e634567

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_post_write_no_execute_validation.md
sha256: 5aefbc3d1f3e361ac542811b93aae499b7a546d6596c9c8396a394fd6fdc8f87
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage40_served_proposal_write/snapshot_20260513_152125/
```

The A6000 copies matched the syhlabtop checksums above.

## Actual Attempt Metrics

```text
max_abs_target_delta_from_fresh_deg: 1.4891547267763565
max_abs_final_target_error_deg: 0.25352870951456685
```

| Key | Fresh current deg | Target deg | Draft delta deg | Post-hold readback deg | Final readback deg | Final target error deg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -3.835893 | -4.051618 | -0.215725 | -4.141890 | -4.141890 | -0.090272 |
| `right_joint_2.pos` | 0.666637 | 1.116878 | 0.450241 | 0.863349 | 0.863349 | -0.253529 |
| `right_joint_3.pos` | 14.676934 | 15.215549 | 0.538614 | 15.114073 | 15.114073 | -0.101475 |
| `right_joint_4.pos` | 6.677295 | 8.166450 | 1.489155 | 6.677295 | 7.988711 | -0.177738 |
| `right_joint_5.pos` | -3.529896 | -3.685856 | -0.155960 | -3.529896 | -3.551753 | 0.134103 |
| `right_joint_6.pos` | 4.863169 | 4.412115 | -0.451054 | 4.863169 | 4.207461 | -0.204654 |
| `right_joint_7.pos` | -1.256774 | -1.373927 | -0.117153 | -1.256774 | -1.453486 | -0.079559 |

## Post-Write Readback

The post-write validation was run without `--execute`; no additional actuator
commands were sent.

Unlike Stage 39, this read-only check still passed the pre-write freshness
gate. That does not authorize reuse of the Stage 40 packet. The exact operator
approval was consumed by the single write above, and any further motion requires
a new explicit approval for a current exact target table.

```text
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
fresh_target_validation_passed: true
errors: []
max_abs_remaining_to_target_deg: 0.7460188057247077
max_abs_drift_from_proposal_current_deg: 0.8524204366372068
```

| Key | Post-write current deg | Target deg | Target delta from current deg | Drift from proposal current deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.163747 | -4.051618 | 0.112129 | -0.327854 |
| `right_joint_2.pos` | 0.797778 | 1.116878 | 0.319100 | 0.131142 |
| `right_joint_3.pos` | 15.092216 | 15.215549 | 0.123332 | 0.415282 |
| `right_joint_4.pos` | 7.420431 | 8.166450 | 0.746019 | 0.743136 |
| `right_joint_5.pos` | -3.529896 | -3.685856 | -0.155960 | -0.000000 |
| `right_joint_6.pos` | 4.010748 | 4.412115 | 0.401367 | -0.852420 |
| `right_joint_7.pos` | -1.453486 | -1.373927 | 0.079559 | -0.196712 |

## Boundary

The Stage 40 served-proposal single write is complete. Further robot motion is
blocked until a fresh review path or a new exact target table, pre-write
validation, and explicit operator approval are produced.

```text
stage40_single_write_attempt: DONE
stage40_post_write_readback: RECORDED_NO_EXECUTE_PASS
stage40_packet_reuse: FORBIDDEN_WITHOUT_NEW_APPROVAL
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
