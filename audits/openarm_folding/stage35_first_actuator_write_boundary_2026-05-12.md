# Stage 35 First Actuator Write Boundary

Date: 2026-05-12

## Status

Stage 34 no-send gates have reached the first actuator-write boundary for the
fresh snapshot:

```text
snapshot: snapshot_20260512_171650
stage32_a6000_review: PASS
stage34_dry_run: PASS_FOR_NO_SEND
stage34_runtime_preflight: PASS
stage34_execution_packet_no_send: CREATED
motion_status: BLOCKED
```

No robot motion is authorized by this document.

The latest syhlabtop report says:

```text
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
```

Forbidden paths remain forbidden unless a separate Stage 35 motion approval is
given:

```text
OpenArmFollower.connect()
torque enable
zeroing
calibration write
actuator write
send_action
rollout
record
replay-to-robot
```

## Accepted Fresh Snapshot Review

A6000 snapshot:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260512_171650/
```

Review outputs:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_171650_action_review.csv
sha256: 91ae54f5c28ba8fe761d76a0ed4c7f496119a1f1f76a24a56343386f1ffd6e83

/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_171650_action_review.json
sha256: 5a14b572d3f8e4508527edab4b3f01cd6655e832d43bfa5db751e9aafcb86ec2
```

Review summary:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
```

## Stage 34 Dry-Run

Dry-run outputs:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_171650_guarded_first_motion_dry_run.json
sha256: ef1501cad3dd3890955701d74c330e3393a1181fcbfbcba47a2a9d6100263fdc

/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_171650_guarded_first_motion_dry_run.md
sha256: 710c708bce81dad564d1da544f0dfbeb5d852e1074bae69cda8475d14a3f0ed6
```

Dry-run result:

```text
max_abs_right_arm_candidate_delta_deg: 0.588154
right_arm_candidate_targets_within_review_limits: true
send_allowed: false
motion_allowed: false
```

Right-arm candidate table from the A6000 dry-run:

| Key | Current deg | Target deg | Delta deg | Limits deg | Target in limits |
| --- | ---: | ---: | ---: | ---: | --- |
| `right_joint_1.pos` | -4.470 | -5.058 | -0.588 | [-75, 75] | true |
| `right_joint_2.pos` | -1.869 | -1.801 | 0.067 | [-9, 90] | true |
| `right_joint_3.pos` | 14.611 | 15.022 | 0.411 | [-85, 85] | true |
| `right_joint_4.pos` | 8.273 | 8.502 | 0.229 | [0, 135] | true |
| `right_joint_5.pos` | -3.093 | -2.529 | 0.564 | [-85, 85] | true |
| `right_joint_6.pos` | -0.470 | -0.612 | -0.142 | [-40, 40] | true |
| `right_joint_7.pos` | -4.229 | -3.922 | 0.308 | [-80, 80] | true |

## Artifact Handoff

The syhlabtop Stage 34 packet artifacts were transferred to A6000 and their
checksums matched the syhlabtop report.

A6000 packet root:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage34_packets/snapshot_20260512_171650/
```

Checksums:

```text
runtime_preflight_json_sha256: 8b3d8df7db88eb8bdfaa9975e08cef3d91e9c0769312312cd2d969666b36d920
runtime_preflight_md_sha256: 1858e09841a6b62f9d58ccba15f59ed913eb3339fe67939d14da000f972a6c59
execution_packet_json_sha256: c5411331665ea5b31a9d85de4adf27ce74f0c9596630c4cc8481e6afd58ec259
execution_packet_md_sha256: 43c4ec4464caaaf31b0c6a92e0e4d7446f8edd0fb56c6596c509de2fd2aaa6ee
```

The execution packet still says:

```text
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

## Exact Stage 35 Candidate

Selected joints:

```text
right_joint_1.pos
right_joint_2.pos
right_joint_3.pos
right_joint_4.pos
right_joint_5.pos
right_joint_6.pos
right_joint_7.pos
```

Expected max delta:

```text
0.5881538391113281 deg
```

Exact right-arm target table:

| Key | Current deg | Target deg | Delta deg |
| --- | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.469744 | -5.057898 | -0.588154 |
| `right_joint_2.pos` | -1.868768 | -1.801383 | 0.067385 |
| `right_joint_3.pos` | 14.611363 | 15.022029 | 0.410666 |
| `right_joint_4.pos` | 8.272851 | 8.502065 | 0.229214 |
| `right_joint_5.pos` | -3.092757 | -2.528544 | 0.564213 |
| `right_joint_6.pos` | -0.469924 | -0.612096 | -0.142172 |
| `right_joint_7.pos` | -4.229318 | -3.921798 | 0.307520 |

## Stage 35 Writer Status

```text
stage35_no_execute_validator: READY
stage35_a6000_packet_only_validation: PASS
stage35_syhlabtop_fresh_no_execute_validation: PASS
stage35_syhlabtop_no_execute_validation_handoff_to_a6000: DONE
stage35_actual_writer: NOT_READY
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

Use:

```text
audits/openarm_folding/stage35_no_execute_writer_validation.py
audits/openarm_folding/stage35_no_execute_writer_validation_2026-05-12.md
audits/openarm_folding/syhlabtop_stage35_no_execute_validation_prompt_2026-05-12.md
```

A6000 packet-only validation output:

```text
/tmp/snapshot_20260512_171650_stage35_no_execute_packet_only.json
/tmp/snapshot_20260512_171650_stage35_no_execute_packet_only.md
```

Result:

```text
packet_validation_passed: true
fresh_readback_validation_passed: null
execute_path_available: false
actual_writer_status: NOT_READY
```

The validator also rejected an intentionally wrong packet checksum with
non-zero exit status.

syhlabtop fresh readback validation output:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json
sha256: f16c0262cc7f028caa8a6a552015d4ff7e691b9bec57a509b33ef585be4bcd4d

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.md
sha256: 772033040723eb488c58ab6249c022e3e96f7a8479bdf0fde730ad7cb0f8f0d5
```

Result:

```text
packet_validation_passed: true
fresh_readback_validation_passed: true
max_abs_fresh_drift_deg: 0.02185693518331755
max_abs_target_delta_from_fresh_deg: 0.5881540488490593
execute_path_available: false
actual_writer_status: NOT_READY
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_no_execute_validation/snapshot_20260512_171650/
```

The A6000 copies matched the syhlabtop checksums.

## Stage 35 Entry Requirements

Stage 35 is actual actuator write. It requires a separate explicit human
approval after all of the following are true:

1. A no-execute writer validation passes on syhlabtop immediately before any
   motion approval. The latest run passed for `snapshot_20260512_171650`, but
   it must be considered stale if the robot state changes before approval.
2. The actual actuator writer is regenerated or parameterized for the approved
   `snapshot_20260512_171650` packet. The older writer is hardcoded to
   `snapshot_20260511_154554` and must not be reused directly.
3. A Stage 35 operator approval draft records the exact command and target
   table.
4. Operator confirms physical presence, power/abort control, and e-stop
   readiness.

Until these conditions are met:

```text
stage35_actuator_write: BLOCKED
motion_status: BLOCKED
```

## Next Work

A6000 may update the audit record and draft a separate Stage 35 operator
approval document. The draft must record the exact command, selected joints,
target table, expected maximum delta, physical operator readiness,
power/abort procedure, and e-stop readiness.

Do not run Stage 35 actual actuator write from this boundary document.
