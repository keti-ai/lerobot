# Stage 32 syhlabtop Snapshot And A6000 Review

Date: 2026-05-12

## Result

Stage 32 passed as a no-send, two-machine snapshot review.

Architecture:

```text
syhlabtop_snapshot__a6000_inference
```

syhlabtop did not load the PI0.5 model and did not receive
`model.safetensors`. syhlabtop captured robot/camera state and transferred the
snapshot bundle to A6000. A6000 loaded the final PI0.5 checkpoint and produced
a no-send action review.

Motion remains blocked.

## syhlabtop Result

```text
repo_head: 388a302df024139eb92548f859fcd48182fdf77d
architecture: syhlabtop_snapshot__a6000_inference
local_model_on_syhlabtop: NO
candidate_checksum: NOT_APPLICABLE_A6000_OWNS_MODEL
camera_mapping: PASS
state_order_check: PASS
snapshot_bundle: CREATED
snapshot_transfer_to_a6000: DONE
motion_status: BLOCKED
```

syhlabtop snapshot:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260512_155652
```

A6000 copy:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260512_155652
```

Snapshot files on A6000:

```text
base.png        294072 bytes
left_wrist.png 1256493 bytes
metadata.json  3065 bytes
right_wrist.png 1386424 bytes
state_16.csv   589 bytes
```

## Snapshot Metadata

Important metadata:

```text
obs_id: snapshot_20260512_155652
timestamp: 2026-05-12T15:56:52+09:00
robot_type: openarms_follower
task: Fold the T-shirt properly
model_owner: A6000
inference_location: A6000_offline_review
policy_computed_on_syhlabtop: false
send_action: false
send_allowed: false
motion_allowed: false
motion_status: BLOCKED
read_path: DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no OpenArmFollower.connect()
```

Camera mapping:

```text
left_wrist:  Intel RealSense D405, serial 315122270766, 1280x720, 15 fps
right_wrist: Intel RealSense D405, serial 230322273311, 1280x720, 15 fps
base:        Intel RealSense D435I, serial 213622075840, 640x480, 30 fps
```

CAN mapping:

```text
left_arm:  can0
right_arm: can1
```

State order:

```text
right_joint_1.pos
right_joint_2.pos
right_joint_3.pos
right_joint_4.pos
right_joint_5.pos
right_joint_6.pos
right_joint_7.pos
right_gripper.pos
left_joint_1.pos
left_joint_2.pos
left_joint_3.pos
left_joint_4.pos
left_joint_5.pos
left_joint_6.pos
left_joint_7.pos
left_gripper.pos
```

## A6000 Review

A6000 review artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.csv
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.json
```

Review JSON:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
```

Largest first-action arm delta:

```text
right_joint_1.pos: -1.3073272705078125 deg
```

Watched joint deltas:

```text
right_joint_4.pos:  0.7648124694824219 deg
left_joint_4.pos:  -0.0755462646484375 deg
right_joint_7.pos:  0.4439506530761719 deg
```

Largest rows by absolute delta:

| Key | Current deg | Proposed deg | Delta deg | Send allowed |
| --- | ---: | ---: | ---: | --- |
| `left_gripper.pos` | -26.589 | -24.334 | 2.255 | false |
| `right_joint_1.pos` | 1.104 | -0.204 | -1.307 | false |
| `left_joint_3.pos` | 6.000 | 4.787 | -1.213 | false |
| `right_gripper.pos` | -23.245 | -24.283 | -1.038 | false |
| `right_joint_6.pos` | -0.448 | 0.353 | 0.801 | false |
| `right_joint_4.pos` | -4.229 | -3.465 | 0.765 | false |
| `left_joint_7.pos` | 0.229 | -0.267 | -0.497 | false |
| `right_joint_7.pos` | -3.792 | -3.348 | 0.444 | false |

No 60-70 degree abnormal delta was observed. The action review is no-send
only and does not authorize robot motion.

## Local syhlabtop Artifacts

```text
/home/syhlabtop/openarm_folding_20260512/audits/stage32_architecture_precheck_2026-05-12.md
/home/syhlabtop/openarm_folding_20260512/audits/stage32_readonly_hardware_preflight_2026-05-12.md
/home/syhlabtop/openarm_folding_20260512/audits/stage32_snapshot_bundle_manifest_2026-05-12.md
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/stage32_no_send_shadow_review_2026-05-12.md
/home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260512_155652/
```

## Safety

No syhlabtop local model inference, rollout, record, replay, zeroing,
calibration write, actuator write, or `send_action` was run.

The next blocker is a separate guarded first-actuator-write gate. It requires
fresh readback validation and explicit human approval of the exact command.
