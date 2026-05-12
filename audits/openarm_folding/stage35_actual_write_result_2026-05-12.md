# Stage 35 Actual Write Result

Date: 2026-05-12

## Status

The operator gave explicit approval for the exact Stage 35 command and
confirmation phrase in the live session. The guarded writer executed one
right-arm joint write for `snapshot_20260512_171650`.

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

No rollout, recording, replay-to-robot, `send_action`, local PI0.5 inference,
zeroing, or calibration write was run.

## Artifacts

Actual write attempt:

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

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_actual_write_attempt/snapshot_20260512_171650/
```

The A6000 copies matched the syhlabtop checksums.

## Actual Attempt Metrics

```text
max_abs_target_delta_from_fresh_deg: 0.5881540488490593
max_abs_final_target_error_deg: 0.36750044908878676
```

| Key | Fresh current deg | Target deg | Final readback deg | Final target error deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.469744 | -5.057898 | -5.081738 | -0.023840 |
| `right_joint_2.pos` | -1.868768 | -1.801383 | -1.868768 | -0.067385 |
| `right_joint_3.pos` | 14.611364 | 15.022029 | 14.939218 | -0.082811 |
| `right_joint_4.pos` | 8.272851 | 8.502065 | 8.338422 | -0.163643 |
| `right_joint_5.pos` | -3.092757 | -2.528544 | -2.896044 | -0.367500 |
| `right_joint_6.pos` | -0.469924 | -0.612096 | -0.513638 | 0.098458 |
| `right_joint_7.pos` | -4.229318 | -3.921798 | -4.010748 | -0.088951 |

## Post-Write Readback

The post-write readback was run without `--execute`; no additional actuator
commands were sent.

```text
packet_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_drift_from_packet_current_deg: 0.6119940781871565
max_abs_target_delta_from_current_deg: 0.38935738794324726
```

| Key | Post-write current deg | Target deg | Target delta from current deg |
| --- | ---: | ---: | ---: |
| `right_joint_1.pos` | -5.081738 | -5.057898 | 0.023840 |
| `right_joint_2.pos` | -1.868768 | -1.801383 | 0.067385 |
| `right_joint_3.pos` | 14.939218 | 15.022029 | 0.082811 |
| `right_joint_4.pos` | 8.294708 | 8.502065 | 0.207356 |
| `right_joint_5.pos` | -2.917901 | -2.528544 | 0.389357 |
| `right_joint_6.pos` | -0.469924 | -0.612096 | -0.142172 |
| `right_joint_7.pos` | -4.032605 | -3.921798 | 0.110807 |

## Boundary

The Stage 35 single write is complete. Further robot motion is blocked until
the actual write result and post-write readback are reviewed.

```text
stage35_single_write_attempt: DONE
stage35_post_write_readback: PASS
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
