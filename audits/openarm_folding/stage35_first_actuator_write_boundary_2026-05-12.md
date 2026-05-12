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

## Missing Before Stage 35

The syhlabtop session reports that these artifacts were created locally:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.md
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.md
```

They are not yet present under the A6000 work root. Stage 35 cannot be approved
until A6000 receives or audits those packet artifacts and records their
checksums.

## Stage 35 Entry Requirements

Stage 35 is actual actuator write. It requires a separate explicit human
approval after all of the following are true:

1. A6000 has the exact Stage 34 runtime preflight JSON/Markdown.
2. A6000 has the exact Stage 34 execution packet JSON/Markdown.
3. The packet checksum is recorded in repo/audit docs.
4. The exact selected joint set is recorded.
5. The exact target table is recorded.
6. The expected maximum delta is recorded.
7. The actuator writer is regenerated or parameterized for the approved
   `snapshot_20260512_171650` packet. The older writer is hardcoded to
   `snapshot_20260511_154554` and must not be reused directly.
8. A no-execute writer validation passes on syhlabtop immediately before any
   motion approval.
9. Operator confirms physical presence, power/abort control, and e-stop
   readiness.

Until these conditions are met:

```text
stage35_actuator_write: BLOCKED
motion_status: BLOCKED
```

## Next Work

Transfer or print the syhlabtop Stage 34 runtime preflight and execution packet
artifacts, then update this boundary with:

```text
runtime_preflight_sha256:
execution_packet_sha256:
exact_selected_joints:
exact_target_table:
expected_max_delta_deg:
stage35_writer_status:
```

Do not run Stage 35 from the A6000 dry-run table alone.
