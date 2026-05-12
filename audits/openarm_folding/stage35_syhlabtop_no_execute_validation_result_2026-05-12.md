# Stage 35 syhlabtop No-Execute Validation Result

Date: 2026-05-12

## Status

The Stage 35 no-execute validation completed on syhlabtop for the approved
fresh snapshot packet:

```text
snapshot: snapshot_20260512_171650
packet_validation_passed: true
fresh_readback_validation_passed: true
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
execute_path_available: false
operator_motion_approval: NOT_GIVEN
actual_writer_status: NOT_READY
motion_status: BLOCKED
```

This result does not authorize robot motion.

## Inputs

Packet:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json
sha256: c5411331665ea5b31a9d85de4adf27ce74f0c9596630c4cc8481e6afd58ec259
```

Validator:

```text
audits/openarm_folding/stage35_no_execute_writer_validation.py
```

Read path:

```text
DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); disconnect(disable_torque=False); no OpenArmFollower.connect()
```

## Outputs

syhlabtop outputs:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json
sha256: f16c0262cc7f028caa8a6a552015d4ff7e691b9bec57a509b33ef585be4bcd4d

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.md
sha256: 772033040723eb488c58ab6249c022e3e96f7a8479bdf0fde730ad7cb0f8f0d5
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_no_execute_validation/snapshot_20260512_171650/
```

The A6000 copies matched the syhlabtop checksums.

## Validation Metrics

```text
max_abs_right_arm_candidate_delta_deg: 0.5881538391113281
max_abs_fresh_drift_deg: 0.02185693518331755
max_abs_target_delta_from_fresh_deg: 0.5881540488490593
```

Selected features:

```text
right_joint_1.pos
right_joint_2.pos
right_joint_3.pos
right_joint_4.pos
right_joint_5.pos
right_joint_6.pos
right_joint_7.pos
```

| Key | Packet current deg | Fresh current deg | Target deg | Delta from fresh deg | Drift deg | Validated |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `right_joint_1.pos` | -4.469744 | -4.469744 | -5.057898 | -0.588154 | 0.000000 | true |
| `right_joint_2.pos` | -1.868768 | -1.868768 | -1.801383 | 0.067385 | -0.000000 | true |
| `right_joint_3.pos` | 14.611363 | 14.611364 | 15.022029 | 0.410665 | 0.000000 | true |
| `right_joint_4.pos` | 8.272851 | 8.272851 | 8.502065 | 0.229213 | 0.000000 | true |
| `right_joint_5.pos` | -3.092757 | -3.092757 | -2.528544 | 0.564213 | -0.000000 | true |
| `right_joint_6.pos` | -0.469924 | -0.448067 | -0.612096 | -0.164029 | 0.021857 | true |
| `right_joint_7.pos` | -4.229318 | -4.229318 | -3.921798 | 0.307520 | -0.000000 | true |

## Boundary

Stage 35 actual actuator write remains blocked. The next no-motion work is an
A6000 audit update and a separate operator approval draft. That draft must not
be treated as approval, and the actual writer remains not ready.
