# Stage 15 Guarded First-Motion Spec

Date: 2026-05-11
Scope: dry-run planning only. This stage does not approve actuator motion.

## Input Artifact

The only accepted review artifact for the first guarded dry run is the refreshed
post-gripper-zero A6000 review:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.csv
sha256: ae203f49bca1d05ea01f9cd43affec69b45750d843c1809fde2bc7d64f8d1fb6

/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.json
sha256: 75a2136cb6eba5d3870d4d23a516d9b3050a21d1055871562b8e839142bfb6a1
```

The old `snapshot_20260511_135634` review is rejected because it was captured
before the gripper-only zero adjustment.

## Dry-Run Tool

Tool:

```text
audits/openarm_folding/guarded_first_motion_dry_run.py
```

This tool reads only CSV/JSON review artifacts. It does not import robot drivers,
open CAN sockets, enable torque, write goals, call `send_action`, record, replay,
or run a policy.

Required validation:

- `obs_id` must be `snapshot_20260511_154554`;
- CSV sha256 must match the accepted post-gripper-zero review;
- JSON sha256 must match the accepted post-gripper-zero review when provided;
- JSON must report `action_shape=[1, 30, 16]`;
- JSON must report `all_finite=true`;
- CSV and JSON must keep `send_allowed=false`;
- only `action_id=0` is accepted for the first dry-run plan.

Default caps:

```text
arm joints: <= 2 deg from review current value
grippers:   <= 5 deg from review current value
```

Default hold:

```text
left_joint_7.pos
```

Reason: `left_joint_7` wrist-flap direction/range is mirrored and still needs
explicit acceptance before any wrist command candidate.

## Dry-Run Command

```bash
uv run python audits/openarm_folding/guarded_first_motion_dry_run.py \
  --review-csv /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.csv \
  --review-json /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.json \
  --json-out /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_guarded_first_motion_dry_run.json
```

## Motion Status

This stage creates a capped target table only. It is still not a motion gate.

## Verification

The dry-run tool was executed against the accepted post-gripper-zero artifacts:

```text
mode: dry_run_only
send_allowed: false
motion_allowed: false
approved_snapshot_id: snapshot_20260511_154554
arm_cap_deg: 2.0
gripper_cap_deg: 5.0
hold_keys: [left_joint_7.pos]
max_abs_final_delta_deg: 5.0
```

Dry-run output:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_guarded_first_motion_dry_run.json
sha256: ce6c6efb2d6b2d7532500cb7b4ca61273993358ccd1ef437e4ae25781ee2cef3
```

The stale pre-gripper-zero review was tested and rejected:

```text
Rejected stale or unexpected obs_id set: ['snapshot_20260511_135634']
```

Dry-run final target table:

| Key | Current deg | Clamped deg | Final target deg | Final delta deg | Reason |
| --- | ---: | ---: | ---: | ---: | --- |
| `right_joint_1.pos` | -1.126 | -8.406 | -3.126 | -2.000 | capped |
| `right_joint_2.pos` | -0.295 | -9.000 | -2.295 | -2.000 | capped |
| `right_joint_3.pos` | 13.540 | -7.242 | 11.540 | -2.000 | capped |
| `right_joint_4.pos` | 0.361 | 0.000 | 0.000 | -0.361 | within cap |
| `right_joint_5.pos` | -3.071 | -31.955 | -5.071 | -2.000 | capped |
| `right_joint_6.pos` | -0.426 | -13.211 | -2.426 | -2.000 | capped |
| `right_joint_7.pos` | 5.978 | 53.284 | 7.978 | 2.000 | capped |
| `right_gripper.pos` | -23.245 | -10.304 | -18.245 | 5.000 | capped |
| `left_joint_1.pos` | -1.104 | 22.894 | 0.896 | 2.000 | capped |
| `left_joint_2.pos` | -1.912 | 9.000 | 0.088 | 2.000 | capped |
| `left_joint_3.pos` | 6.743 | 27.344 | 8.743 | 2.000 | capped |
| `left_joint_4.pos` | -1.563 | 0.000 | 0.000 | 1.563 | within cap |
| `left_joint_5.pos` | -16.360 | 7.254 | -14.360 | 2.000 | capped |
| `left_joint_6.pos` | -5.563 | -6.454 | -6.454 | -0.891 | within cap |
| `left_joint_7.pos` | -2.109 | -28.198 | -2.109 | 0.000 | held |
| `left_gripper.pos` | -26.611 | -4.300 | -21.611 | 5.000 | capped |

Before any actuator command can be considered, a later stage must add all of the
following:

- fresh current readback immediately before command;
- comparison between fresh readback and review current values;
- explicit operator approval of the exact target table;
- a separate runtime flag that is absent by default;
- log of every target actually sent and every readback after send;
- a hard stop path and operator hold/abort procedure.

Until those exist, motion remains blocked.
