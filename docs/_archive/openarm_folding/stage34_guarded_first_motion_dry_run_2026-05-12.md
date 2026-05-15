# Stage 34 Guarded First Motion Dry Run

Date: 2026-05-12

## Result

Stage 34 dry-run artifact was generated from the accepted Stage 32 A6000
no-send review for `snapshot_20260512_155652`.

This is still no-motion. No robot IO, torque, zeroing, actuator write, rollout,
replay-to-robot, or `robot.send_action()` was run by this stage.

Stage 35 actuator write remains blocked.

## Inputs

Review CSV:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.csv
sha256: 5b84b9b527419810cfe7568b0c1bea7d545d38ce66187fe0b5388cbb300e8947
```

Review JSON:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.json
sha256: 837bb6c190330ed5399944bdff10d1c9aecd83ec8ac8d425884f5e3e2f876468
```

Dry-run tool:

```text
audits/openarm_folding/guarded_first_motion_dry_run_v2.py
```

## Outputs

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.json
sha256: 896c38e2f4d5bb465e9d04e4e26af113c28dbad8d2f61b788f05b798a3173a7e

/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.md
sha256: 01b4dddeb407a8d982efe04d7abd62b484d7f1285e9350ee3c79c978f64ef132
```

Dry-run summary:

```text
send_allowed: false
motion_allowed: false
stage35_candidate_ready: false
max_abs_final_delta_deg: 2.255420684814453
max_abs_right_arm_candidate_delta_deg: 2.0
blocking_first_write_keys: ["right_joint_4.pos"]
```

## Right-Arm First-Write Candidate Table

| Key | Current deg | Target deg | Delta deg | Review limits deg | Target in limits |
| --- | ---: | ---: | ---: | ---: | --- |
| `right_joint_1.pos` | 1.104 | -0.204 | -1.307 | [-75, 75] | true |
| `right_joint_2.pos` | -1.213 | -1.649 | -0.436 | [-9, 90] | true |
| `right_joint_3.pos` | 14.611 | 14.538 | -0.074 | [-85, 85] | true |
| `right_joint_4.pos` | -4.229 | -2.229 | 2.000 | [0, 135] | false |
| `right_joint_5.pos` | -3.989 | -3.564 | 0.425 | [-85, 85] | true |
| `right_joint_6.pos` | -0.448 | 0.353 | 0.801 | [-40, 40] | true |
| `right_joint_7.pos` | -3.792 | -3.348 | 0.444 | [-80, 80] | true |

## Blocker

`right_joint_4.pos` is the blocker.

The Stage 32 review current value was `-4.229 deg`, while the review limit for
`right_joint_4.pos` is `[0, 135]`. Applying the 2 degree dry-run cap moves the
target toward the valid range, but the target remains outside the review
limits:

```text
current: -4.229 deg
clamped target: 0.000 deg
dry-run capped target: -2.229 deg
target in limits: false
```

Therefore the current dry-run table must not advance to Stage 35 actuator
write.

## Next Options

Before any actuator write:

1. Confirm whether the `right_joint_4.pos` software limit `[0, 135]` is correct
   for the current OpenArm calibration and readback convention.
2. If the limit is correct, decide how to handle a current readback below the
   limit without violating the per-step cap.
3. If the limit is not correct for this robot, update the limit source and
   rerun the dry-run gate.
4. Capture a fresh syhlabtop snapshot if the robot state changes.
5. Regenerate dry-run/preflight/packet artifacts from the accepted fresh
   snapshot.

Motion remains blocked.
