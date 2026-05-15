# OpenArm Folding Baseline Shared Document

Date: 2026-05-10
Next test date: 2026-05-11
Branch: `audit/openarm-folding-baseline`
Workspace: `/home/syh/workspace/lerobot`

## Purpose

This document is the shared baseline for testing the LeRobot OpenArm folding policy with two machines:

- `syhlabtop`: robot IO owner
- `A6000 server`: model/inference/offline analysis owner

The immediate goal is not autonomous folding. The immediate goal is to reach a safe no-motion/shadow evaluation gate where camera/state input and policy output can be inspected without unintentionally sending robot motion.

## Current Source Of Truth

Audit artifacts already produced:

- `audits/openarm_folding/artifact_audit.md`
- `audits/openarm_folding/body_compat_matrix.md`

Hub artifacts audited:

| Artifact | Role | Status |
| --- | --- | --- |
| `lerobot/folding_latest` | PI05 folding policy | Metadata/config audited only |
| `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c` | Training dataset referenced by policy config | Metadata audited only |
| `lerobot/high_quality_folding` | Related folding dataset | Metadata audited only |
| `lerobot/full_folding` | Related folding dataset | Metadata audited only |

No robot was run, no training was run, no full datasets were downloaded, and `model.safetensors` was not downloaded during the audit.

## Machine Responsibilities

| Machine | Owns | Must Not Own |
| --- | --- | --- |
| `syhlabtop` | CAN buses, cameras, calibration files, final action safety gate, emergency stop path, logs from physical hardware | Unchecked remote direct robot control |
| `A6000 server` | Model weights, tokenizer/cache, offline inference, action proposal generation, latency profiling, audit logs | Direct actuator authority |

Operating rule: the A6000 may propose actions; `syhlabtop` decides whether anything can be sent to actuators.

## Policy Identity

`lerobot/folding_latest` is a LeRobot-native checkpoint/config layout for policy type `pi05`.

It is OpenPI-derived, but local code inspection found no runtime `import openpi` or `from openpi`. It loads through LeRobot PI05 policy and LeRobot policy processor files.

Important policy facts:

- `type`: `pi05`
- `chunk_size`: `30`
- `n_action_steps`: `30`
- `use_relative_actions`: `true`
- `relative_exclude_joints`: `["gripper"]`
- task text from dataset metadata: `Fold the T-shirt properly`
- training dataset in policy config: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`

## Body Contract

The state/action vector is 16-dimensional and ordered right arm first, then left arm.

| Index | Name | Units | Model-space |
| ---: | --- | --- | --- |
| 0 | `right_joint_1.pos` | deg | relative |
| 1 | `right_joint_2.pos` | deg | relative |
| 2 | `right_joint_3.pos` | deg | relative |
| 3 | `right_joint_4.pos` | deg | relative |
| 4 | `right_joint_5.pos` | deg | relative |
| 5 | `right_joint_6.pos` | deg | relative |
| 6 | `right_joint_7.pos` | deg | relative |
| 7 | `right_gripper.pos` | deg | absolute |
| 8 | `left_joint_1.pos` | deg | relative |
| 9 | `left_joint_2.pos` | deg | relative |
| 10 | `left_joint_3.pos` | deg | relative |
| 11 | `left_joint_4.pos` | deg | relative |
| 12 | `left_joint_5.pos` | deg | relative |
| 13 | `left_joint_6.pos` | deg | relative |
| 14 | `left_joint_7.pos` | deg | relative |
| 15 | `left_gripper.pos` | deg | absolute |

Hardware send receives absolute degree targets after policy postprocessing.

Gripper semantics:

- The gripper is not binary.
- The gripper is a positional degree command.
- The default OpenArm side limits are `[-65, 0]` degrees for each gripper.
- The gripper stays absolute because action names containing `gripper` are excluded from relative conversion.

## Camera Contract

The policy expects these exact visual observation keys unless a `rename_map` is used:

| Policy key | Robot camera key | Expected role |
| --- | --- | --- |
| `observation.images.left_wrist` | `left_wrist` | physical left wrist view |
| `observation.images.right_wrist` | `right_wrist` | physical right wrist view |
| `observation.images.base` | `base` | third-person/base view |

Dataset image shapes:

- `left_wrist`: `[720, 1280, 3]`
- `right_wrist`: `[720, 1280, 3]`
- `base`: `[480, 640, 3]`

The metadata does not prove physical serial numbers, USB paths, left/right placement, or image orientation. Those must be validated on `syhlabtop`.

## Processor Contract

The intended PI05 path is:

```text
raw observation/action
-> relative action processor
-> normalizer
-> PI05 model
-> unnormalizer
-> absolute action processor
-> absolute degree action dict
```

For non-gripper joints:

```text
model-space action = target_action - current_observation_state
hardware target = model_output + cached_observation_state
```

For grippers:

```text
model-space action = absolute target
hardware target = absolute target
```

This means stale state, wrong state ordering, or missing processor cache can create wrong absolute targets.

## Current Rollout Constraints

These are current code constraints, not policy preferences:

- `OpenArmFollower.connect()` connects cameras/CAN, configures motors, sets zero when calibrated, and calls `enable_torque()`.
- `send_next_action()` calls `ctx.hardware.robot_wrapper.send_action(processed)`.
- `SyncInferenceEngine` is rejected for enabled relative-action policies.
- RTC inference is an in-process background thread, not a remote A6000 inference service.
- `display_ip` and `display_port` are Rerun visualization settings, not inference transport.

Therefore the current repo does not yet provide a safe split-host path where `syhlabtop` owns robot IO and the A6000 runs live policy inference for the same control loop.

## Safety Invariants

The following must stay true until explicitly changed by a reviewed implementation:

1. Do not run autonomous policy motion from `lerobot-rollout` on the physical robot.
2. Do not call a path that reaches `send_action()` during shadow eval.
3. Do not rely on `connect()` as a no-motion operation; current OpenArm follower connect enables torque.
4. Do not trust example CAN port assignments. Verify `syhlabtop` left/right mapping directly.
5. Do not allow A6000 network output to become direct actuator commands.
6. Do not run sync inference with this policy; `folding_latest` uses relative actions.
7. Do not start motion unless E-stop, operator, and safety observer are ready.

## Tomorrow's Target Gate

Target for 2026-05-11:

```text
Gate 1: no-motion/shadow readiness
```

Gate 1 is passed only when:

- A6000 can load the policy assets and produce a 16-dim action proposal offline.
- `syhlabtop` camera keys and physical camera views are documented.
- `syhlabtop` CAN side mapping and calibration IDs are documented.
- A no-send execution path is identified or implemented before live policy observations are processed.
- A generated action can be inspected as degrees in the exact 16-key order without being sent.

Autonomous folding is outside Gate 1.

## Open Decisions

| Decision | Current recommendation |
| --- | --- |
| Same-host vs split-host execution | Treat split-host live inference as blocked until a remote inference bridge exists |
| First robot test scope | Hardware mapping and no-send shadow only |
| First motion scope | Not tomorrow unless no-send, safety gate, and command clamp are implemented and reviewed first |
| Camera naming | Prefer exact keys: `left_wrist`, `right_wrist`, `base` |
| Inference backend | RTC only for `folding_latest` |

## Log Locations

Recommended log layout:

```text
A6000:
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest/
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/offline_inference_logs/
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/

syhlabtop:
  <syhlabtop-work-root>/audits/
  <syhlabtop-work-root>/hardware/openarm/
  <syhlabtop-work-root>/calibration/
  <syhlabtop-work-root>/camera_maps/
  <syhlabtop-work-root>/shadow_snapshots/
  <syhlabtop-work-root>/shadow_reviews/
  <syhlabtop-work-root>/safety_configs/

Optional NAS exchange, after confirming both machines mount it:
  /mnt/nas/lerobot_shared/openarm_folding_20260511/
```

Minimum log file names for tomorrow:

- `2026-05-11_camera_probe.md`
- `2026-05-11_can_calibration_probe.md`
- `2026-05-11_policy_asset_probe.md`
- `2026-05-11_shadow_action_review.csv`
