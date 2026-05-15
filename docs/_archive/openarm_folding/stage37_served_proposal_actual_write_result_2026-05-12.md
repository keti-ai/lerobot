# Stage 37 Served Proposal Actual Write Result

Date: 2026-05-12

## Status

The operator gave explicit approval for the exact Stage 37 target table and
confirmation phrase in the live session:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage37_target_table: true
approval_phrase: SEND_STAGE37_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260512_194042
```

The guarded writer validated the A6000 served proposal checksum and fresh
right-arm state, then executed one right-arm joint write for
`snapshot_20260512_194042`.

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

## Source Proposal

```text
snapshot: snapshot_20260512_194042
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_a6000_served_action_proposal.json
proposal_sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da
a6000_model_server: http://10.252.205.103:8765/predict_snapshot
```

## Artifacts

No-execute readiness validation:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_ready_no_send.json
sha256: f34a0a1d9c4f805b8aeb0c702678f3a24738f5513545cbebc0dae3f0d41ff5f8

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_ready_no_send.md
sha256: 9d7ecac19267274b2123ba0f674e07ac232e35168e74031601fdca189263d0db
```

Actual write attempt:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_actual_write_attempt.json
sha256: f30e19372e6195cb2b0cee36f8c7eddb4e457098968a7cb2e1f436530e8e20b0

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_actual_write_attempt.md
sha256: 122900b1a3e5e721970fd63119f8221a589f646c506619728e5af025155adf59
```

Post-write read-only readback:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_post_write_readback.json
sha256: 138114716c25002c23cb18cdf39ce54b40140995b41e311dd16c5ff12ace09f6

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_post_write_readback.md
sha256: 2c979a76f100d9c07c28dce2d057c229c78b27e97ab54a88243d824a6b954407
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage37_served_proposal_write/snapshot_20260512_194042/
```

The A6000 copies matched the syhlabtop checksums above.

## Actual Attempt Metrics

```text
max_abs_target_delta_from_fresh_deg: 2.0
max_abs_final_target_error_deg: 0.36498359171830963
```

| Key | Fresh current deg | Target deg | Final readback deg | Final target error deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -5.081738 | -4.664086 | -4.753884 | -0.089798 |
| `right_joint_2.pos` | -1.868768 | -1.259376 | -1.344202 | -0.084826 |
| `right_joint_3.pos` | 14.939218 | 14.926427 | 14.939218 | 0.012791 |
| `right_joint_4.pos` | 8.294708 | 9.506226 | 9.343841 | -0.162385 |
| `right_joint_5.pos` | -2.939758 | -3.820436 | -3.967034 | -0.146598 |
| `right_joint_6.pos` | -0.469924 | 0.397769 | 0.032785 | -0.364984 |
| `right_joint_7.pos` | -4.032605 | -2.032605 | -2.305907 | -0.273302 |

The immediate `post_write_readback_deg` and `post_hold_readback_deg` fields in
the actual write artifact still reported the pre-write pose for most joints.
The final readback after torque disable showed the motion above, so an
independent no-execute readback was captured next.

## Post-Write Readback

The post-write readback was run without `--execute`; no additional actuator
commands were sent.

The same script uses a pre-write freshness gate. After Stage 37 motion, that
gate failed for `right_joint_5.pos` and `right_joint_7.pos` because those joints
had moved more than 1 degree from the proposal-current pose. This blocks reuse
of the same proposal and is not a second actuator write.

```text
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
fresh_target_validation_passed: false
errors: ["fresh_target_validation_failed: ['right_joint_5.pos', 'right_joint_7.pos']"]
max_abs_remaining_to_target_deg: 0.8836636219154279
max_abs_drift_from_proposal_current_deg: 1.48627162345538
```

| Key | Post-write current deg | Target deg | Target delta from current deg | Drift from proposal current deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.775741 | -4.664086 | 0.111655 | 0.305997 |
| `right_joint_2.pos` | -1.344202 | -1.259376 | 0.084826 | 0.524566 |
| `right_joint_3.pos` | 14.939218 | 14.926427 | -0.012791 | -0.000000 |
| `right_joint_4.pos` | 8.622562 | 9.506226 | 0.883664 | 0.327854 |
| `right_joint_5.pos` | -3.988891 | -3.820436 | 0.168455 | -1.049133 |
| `right_joint_6.pos` | -0.251355 | 0.397769 | 0.649124 | 0.218569 |
| `right_joint_7.pos` | -2.546333 | -2.032605 | 0.513728 | 1.486272 |

## Boundary

The Stage 37 served-proposal single write is complete. Further robot motion is
blocked until a fresh snapshot, A6000 no-send proposal, exact target table,
pre-write validation, and explicit operator approval are produced.

```text
stage37_single_write_attempt: DONE
stage37_post_write_readback: RECORDED_PREWRITE_GATE_EXPECTED_FAIL
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
