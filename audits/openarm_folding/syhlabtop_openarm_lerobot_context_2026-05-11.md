# Syhlabtop OpenArm LeRobot Context

Date: 2026-05-11
Source repo read: `/home/syhlabtop/workspace/openarm_lerobot`
Source commit: `2367514 docs(leader): handoff plan for joint_4 elbow gravity feedforward`
Target repo: `/home/syhlabtop/workspace/lerobot`
Target branch: `audit/openarm-folding-baseline`

## Purpose

This note imports the latest real-robot context from the sibling `openarm_lerobot`
project into the LeRobot OpenArm folding audit. The sibling repo contains the most
recent syhlabtop-specific hardware mapping, camera serials, calibration namespace,
and safe wrapper details.

No robot motion, rollout, record, replay, policy inference, or `send_action()` was
run while creating this note.

## Hard Safety Carryover

From `openarm_lerobot/docs/codex_handoff_pi05_plan.md`:

- Do not bypass handshake or torque-disable safeties.
- Do not delete or rewrite existing calibration JSON under
  `~/.cache/huggingface/lerobot/calibration/`.
- No live run is allowed until the preceding no-send gate passes and the operator
  explicitly approves the next live phase.
- If a calibration prompt appears, stop and ask the operator. Do not auto-answer.
- Earlier live tests had unsafe coordinate/IK behavior; no-send validation is the
  required next gate before any live movement.

For the current folding baseline, the stronger LeRobot audit rule still applies:
no motion and no `send_action()` until a separate motion gate is explicitly approved.

## CAN Mapping

`/tmp/bus_arm_mapping.md` and `/tmp/bus_arm_decision.md` record a direct
LED ENABLE/DISABLE mapping test from 2026-05-08:

| CAN bus | Physical arm | Evidence |
| --- | --- | --- |
| `can0` | left arm | all left-arm motor LEDs enabled, then disabled |
| `can1` | right arm | all right-arm motor LEDs enabled, then disabled |

Both arms share motor IDs `0x01..0x08`; arm identity comes from CAN bus isolation,
not unique motor IDs.

The bimanual follower config in `openarm_lerobot/configs/record_full.json` uses:

```text
left_arm_config.port=can0
right_arm_config.port=can1
```

`can2` and `can3` are used by the bimanual leader in that config, not by the
follower:

```text
teleop.left_arm_config.port=can3
teleop.right_arm_config.port=can2
```

The current folding no-motion snapshot work should treat `can0=left`,
`can1=right` as the best available syhlabtop hardware fact, while still requiring
operator confirmation before any powered robot IO.

## Camera Mapping

Latest `openarm_lerobot` camera mapping:

| Folding policy key | Existing OpenArm key | Model | Serial | Existing role |
| --- | --- | --- | --- | --- |
| `left_wrist` | `left_wrist` | D405 | `315122270766` | physical left wrist |
| `right_wrist` | `right_wrist` | D405 | `230322273311` | physical right wrist |
| `base` | `chest` | D435 | `234322070493` | chest/base overview |

Important difference:

- The folding policy expects `observation.images.base`.
- Existing `openarm_lerobot` configs use camera key `chest`.
- For folding, use `base` as the LeRobot camera key or provide a reviewed
  `rename_map` from `chest` to `base` before A6000 replay.

RSUSB enumeration on 2026-05-11, with real USB access, observed:

| Model | Serial | Physical port | Notes |
| --- | --- | --- | --- |
| D415 | `211622062255` | `1-1.4-8` | situation/workspace recording camera; auxiliary only, not a folding policy input |
| D435 | `234322070493` | `5-1.1.3.1-26` | expected chest/base camera |
| D405 | `230322273311` | `5-1.1.3.3.1.2-32` | expected right wrist |
| D405 | `315122270766` | `6-1.4.3.2.1-18` | expected left wrist |

V4L2 `/dev/video*` nodes were absent in the sandboxed check. The sibling
runbook states syhlabtop should use the RSUSB-built RealSense runtime from:

```text
/home/syhlabtop/src/librealsense/build/Release
```

and not apt-installed librealsense tools.

## Calibration Context

`openarm_lerobot/docs/codex_handoff_pi05_plan.md` lists these existing calibration
paths:

```text
~/.cache/huggingface/lerobot/calibration/robots/openarm_follower/openarm_right_follower.json
~/.cache/huggingface/lerobot/calibration/robots/openarm_follower/openarm_bimanual_follower_left.json
~/.cache/huggingface/lerobot/calibration/robots/openarm_follower/openarm_bimanual_follower_right.json
~/.cache/huggingface/lerobot/calibration/teleoperators/openarm_leader/...
```

A live file inventory on 2026-05-11 found:

```text
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/openarm_follower/my_bimanual_follower_left.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/openarm_follower/my_bimanual_follower_right.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/openarm_follower/openarm_bimanual_follower_left.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/openarm_follower/openarm_bimanual_follower_right.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/openarm_follower/openarm_right_follower.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/safe_openarm_follower/openarm_bimanual_follower_left.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/robots/safe_openarm_follower/openarm_bimanual_follower_right.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/teleoperators/openarm_leader/my_bimanual_leader_left.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/teleoperators/openarm_leader/my_bimanual_leader_right.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/teleoperators/openarm_leader/openarm_bimanual_leader_left.json
/home/syhlabtop/.cache/huggingface/lerobot/calibration/teleoperators/openarm_leader/openarm_bimanual_leader_right.json
```

The sibling `SafeOpenArmFollower` reuses the non-safe OpenArm follower namespace
via `_reuse_calibration_namespace`, then mirrors into `safe_openarm_follower`.

## Safe Wrapper Context

`openarm_lerobot/src/openarm_lerobot/safe_followers.py` defines:

- `safe_openarm_follower`
- `safe_bi_openarm_follower`
- `safe_openarm_leader`
- `safe_bi_openarm_leader`

Safety-relevant behavior:

- safe shutdown sends repeated OpenArm CAN disable commands and requires disable
  acknowledgements,
- `SafeOpenArmFollower.send_action()` clamps gripper and rejects joint-limit
  violations before LeRobot's generic clipping path,
- on joint-limit violation it attempts torque disable and raises.

For the current folding audit this is context only. It does not authorize live
rollout, record, replay, or policy motion.

## Recommended Folding Snapshot Config Direction

For a future operator-approved, non-actuating snapshot path:

```text
robot.type=safe_bi_openarm_follower
robot.id=openarm_bimanual_follower
robot.left_arm_config.port=can0
robot.left_arm_config.side=left
robot.right_arm_config.port=can1
robot.right_arm_config.side=right
```

Camera keys should be folding-policy-compatible:

```text
left_wrist  -> serial 315122270766
right_wrist -> serial 230322273311
base        -> serial 234322070493
```

Auxiliary situation recording:

```text
situation_recording -> serial 211622062255
```

This D415 stream is not part of the `lerobot/folding_latest` policy contract and
must not replace `left_wrist`, `right_wrist`, or `base` in the A6000 snapshot
action review input.

If reusing existing `openarm_lerobot` config that names the base camera `chest`,
the snapshot metadata and A6000 replay must explicitly record the rename decision.

## Remaining Gates

Before A6000 shadow action review, as of the no-send snapshot created on
2026-05-11:

1. Transfer the local syhlabtop snapshot to A6000:
   `/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_135634`.
2. Run A6000 snapshot action review only; action output remains an offline
   proposal, not an actuator command.
3. Keep `send_allowed=false` and `motion_allowed=false` in review artifacts.
4. Human review of camera orientation and proposed action deltas is still required
   before any later motion gate.

## No-Send Snapshot Created

Snapshot path:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_135634
```

Contents:

```text
left_wrist.png
right_wrist.png
base.png
state_16.csv
metadata.json
```

State read path:

```text
DamiaoMotorsBus.connect(handshake=False)
sync_read_all_states()
disconnect(disable_torque=False)
```

This avoided `OpenArmFollower.connect()`, handshake enable, zeroing, goal writes,
torque commands, `send_action`, rollout, record, and replay. Metadata records
`send_allowed=false`, `motion_allowed=false`, and
`policy_computed_on_syhlabtop=false`.
