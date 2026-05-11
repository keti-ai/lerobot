# Post-Gripper-Zero Snapshot Review

Date: 2026-05-11
Scope: refreshed no-send snapshot and A6000 offline action review after
follower gripper-only zero adjustment.

## Snapshot

The first retry at `snapshot_20260511_154326` was incomplete because the
`right_wrist` D405 serial `230322273311` was not detected. It stopped during
camera capture before CAN state read and before any policy inference.

The successful post-gripper-zero snapshot is:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_154554/
  left_wrist.png
  right_wrist.png
  base.png
  state_16.csv
  metadata.json
```

Tarball:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_154554.tar.gz
sha256: b47804f7e29821fc7c0714cdd6ded02a87f4c8c9b1f2bc184310a2e43931df8b
```

The metadata records the snapshot as a post-gripper-zero no-send snapshot and
includes:

```text
gripper_zero_adjustment.completed: true
gripper_zero_adjustment.scope: follower gripper motors only
gripper_zero_adjustment.motor_id: 008
gripper_zero_adjustment.convention: 0 deg ~= fully closed; negative values open
gripper_zero_adjustment.initial_review_range_deg: [-65, 0]
gripper_zero_adjustment.arm_joint_zero_changed: false
gripper_zero_adjustment.full_arm_zero_position_calibration_run: false
```

No policy output, `send_action`, rollout, record, replay, torque enable, goal
write, or zero write was used while creating the successful snapshot.

## Snapshot State

```text
right_joint_1.pos   -1.126
right_joint_2.pos   -0.295
right_joint_3.pos   13.540
right_joint_4.pos    0.361
right_joint_5.pos   -3.071
right_joint_6.pos   -0.426
right_joint_7.pos    5.978
right_gripper.pos  -23.245
left_joint_1.pos    -1.104
left_joint_2.pos    -1.912
left_joint_3.pos     6.743
left_joint_4.pos    -1.563
left_joint_5.pos   -16.360
left_joint_6.pos    -5.563
left_joint_7.pos    -2.109
left_gripper.pos   -26.611
```

The gripper readbacks are now consistent with the corrected baseline convention:
negative values are slightly open and `0 deg` is closed.

## Transfer

The tarball was transferred to A6000 local storage and NAS:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260511_154554.tar.gz
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/snapshot_20260511_154554.tar.gz
sha256: b47804f7e29821fc7c0714cdd6ded02a87f4c8c9b1f2bc184310a2e43931df8b
```

## A6000 Offline Review

The first A6000 review attempt was blocked because the required Hugging Face
offline cache environment was not set, causing the tokenizer loader to try
accessing the gated `google/paligemma-3b-pt-224` repo.

The review was rerun with:

```text
HF_HOME=/mnt/nas/huggingface
HF_HUB_CACHE=/mnt/nas/huggingface/hub
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

Final A6000 review result:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
```

Artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_154554_action_review.csv
sha256: ae203f49bca1d05ea01f9cd43affec69b45750d843c1809fde2bc7d64f8d1fb6

/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_154554_action_review.json
sha256: 75a2136cb6eba5d3870d4d23a516d9b3050a21d1055871562b8e839142bfb6a1

/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/snapshot_20260511_154554_action_review.csv
/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/snapshot_20260511_154554_action_review.json

/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.csv
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.json
```

## First-Step Action Review

| Key | Current deg | Proposed deg | Clamped deg | Delta deg |
| --- | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -1.126 | -8.406 | -8.406 | -7.280 |
| `right_joint_2.pos` | -0.295 | -9.551 | -9.000 | -9.255 |
| `right_joint_3.pos` | 13.540 | -7.242 | -7.242 | -20.782 |
| `right_joint_4.pos` | 0.361 | -67.569 | 0.000 | -67.930 |
| `right_joint_5.pos` | -3.071 | -31.955 | -31.955 | -28.884 |
| `right_joint_6.pos` | -0.426 | -13.211 | -13.211 | -12.784 |
| `right_joint_7.pos` | 5.978 | 53.284 | 53.284 | 47.306 |
| `right_gripper.pos` | -23.245 | -10.304 | -10.304 | 12.941 |
| `left_joint_1.pos` | -1.104 | 22.894 | 22.894 | 23.998 |
| `left_joint_2.pos` | -1.912 | 22.428 | 9.000 | 24.340 |
| `left_joint_3.pos` | 6.743 | 27.344 | 27.344 | 20.601 |
| `left_joint_4.pos` | -1.563 | -59.939 | 0.000 | -58.376 |
| `left_joint_5.pos` | -16.360 | 7.254 | 7.254 | 23.614 |
| `left_joint_6.pos` | -5.563 | -6.454 | -6.454 | -0.891 |
| `left_joint_7.pos` | -2.109 | -28.198 | -28.198 | -26.089 |
| `left_gripper.pos` | -26.611 | -4.300 | -4.300 | 22.311 |

Summary:

```text
rows: 16
clamped_rows: 4
max_abs_delta: 67.930 deg at right_joint_4.pos
```

Clamped rows:

```text
right_joint_2.pos  proposed -9.551 -> clamped -9.000
right_joint_4.pos  proposed -67.569 -> clamped 0.000
left_joint_2.pos   proposed 22.428 -> clamped 9.000
left_joint_4.pos   proposed -59.939 -> clamped 0.000
```

## Decision

The refreshed post-gripper-zero pipeline is validated through Stage 14:

- syhlabtop captured a complete no-send snapshot from current hardware state;
- the snapshot was transferred to A6000 and NAS;
- A6000 produced a finite PI0.5 action chunk offline;
- review artifacts were copied back to syhlabtop.

The action proposal is not approved as an actuator command.

Motion remains blocked because the first-step proposal still contains large arm
deltas and four clamped rows. Before any command candidate is used, Stage 15
must define a guarded first-motion path with stale-snapshot rejection, one-step
selection, printed raw/clamped/capped targets, explicit operator gate, and small
per-joint delta caps.
