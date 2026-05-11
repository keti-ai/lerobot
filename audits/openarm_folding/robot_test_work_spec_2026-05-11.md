# OpenArm Folding Robot Test Work Spec

Date prepared: 2026-05-10
Execution date: 2026-05-11
Branch: `audit/openarm-folding-baseline`

Chronological two-machine pipeline:

- `audits/openarm_folding/two_machine_pipeline_2026-05-11.md`

## Objective

Prepare and execute the first safe OpenArm folding baseline test across `syhlabtop` and the A6000 server.

The target result for 2026-05-11 is no-motion/shadow readiness, not autonomous folding.

Success means:

- policy assets are present on the A6000,
- `syhlabtop` camera and CAN mappings are documented,
- a 16-dim policy action proposal can be produced and reviewed,
- no policy-generated action is sent to the robot.

## Non-Goals

Do not do these during the first test block:

- no autonomous folding attempt,
- no full dataset download,
- no training,
- no `lerobot-rollout` live autonomous motion,
- no remote direct actuator control from A6000,
- no `send_action()` from a policy path unless a later motion gate is explicitly approved.

## People And Roles

| Role | Responsibility |
| --- | --- |
| `syhlabtop` operator | Cameras, CAN, calibration, robot power state, logs |
| A6000 operator | Model asset download, offline load, inference/action proposal logs |
| Safety observer | E-stop, workspace clearance, go/no-go calls |

One person can hold multiple roles only if the robot remains unpowered or torque-disabled. For any powered motion test, use at least two people: operator and safety observer.

## Hard Stop Conditions

Stop immediately if any of these happens:

- left/right arm mapping is uncertain,
- camera view or orientation is uncertain,
- gripper zero/closed convention is uncertain,
- generated action has unexpected length or key order,
- generated action is not finite,
- generated action exceeds configured joint limits before clamp,
- A6000 output is stale or from the wrong observation,
- any process reaches `send_action()` unexpectedly,
- E-stop or physical clearance is not ready.

## Phase 0: Preflight, Both Machines

Purpose: prove both machines are on the intended repo state before touching hardware or weights.

On A6000:

```bash
cd /home/syh/workspace/lerobot
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
```

On syhlabtop:

```bash
cd /home/syhlabtop/workspace/lerobot
git status --short --branch
git rev-parse --show-toplevel
git branch --show-current
```

Expected:

- branch is `audit/openarm-folding-baseline`,
- no unexpected source edits,
- A6000 repo root is `/home/syh/workspace/lerobot`,
- syhlabtop repo root is `/home/syhlabtop/workspace/lerobot`.

Record output in:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/2026-05-11_preflight.md
```

Gate:

- continue only if both machines are on the intended branch or the difference is documented.

## Phase 1: A6000 Policy Asset Preparation

Purpose: make the A6000 capable of loading `lerobot/folding_latest`.

Allowed downloads for this phase:

- `model.safetensors`
- `config.json`
- `train_config.json`
- `policy_preprocessor.json`
- `policy_postprocessor.json`
- `policy_preprocessor_step_3_normalizer_processor.safetensors`
- `policy_postprocessor_step_0_unnormalizer_processor.safetensors`
- tokenizer files needed by `google/paligemma-3b-pt-224`

Do not download full datasets or video shards.

Suggested A6000 command after download approval:

```bash
mkdir -p /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest
huggingface-cli download lerobot/folding_latest \
  --include "model.safetensors" \
  --include "config.json" \
  --include "train_config.json" \
  --include "policy_preprocessor.json" \
  --include "policy_postprocessor.json" \
  --include "policy_preprocessor_step_3_normalizer_processor.safetensors" \
  --include "policy_postprocessor_step_0_unnormalizer_processor.safetensors" \
  --local-dir /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest
```

Verification:

```bash
find /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest -maxdepth 1 -type f -printf "%f\n" | sort
```

Expected required files:

```text
config.json
model.safetensors
policy_postprocessor.json
policy_postprocessor_step_0_unnormalizer_processor.safetensors
policy_preprocessor.json
policy_preprocessor_step_3_normalizer_processor.safetensors
train_config.json
```

Gate:

- continue only after required files are present,
- record file list and byte sizes in `2026-05-11_policy_asset_probe.md`.

## Phase 2: A6000 Offline Policy Load

Purpose: verify the policy can load without robot hardware.

Use a no-robot script or notebook that only loads:

- `PI05Policy`,
- preprocessor/postprocessor,
- config,
- local model directory.

The check must not import or instantiate `RobotConfig`, `OpenArmFollower`, or `BiOpenArmFollower`.

Expected output:

- policy type is `pi05`,
- device is CUDA on A6000,
- action feature names exactly match the 16-key contract,
- `use_relative_actions=true`,
- gripper dimensions are excluded from relative conversion.

Action contract to verify:

```text
0  right_joint_1.pos
1  right_joint_2.pos
2  right_joint_3.pos
3  right_joint_4.pos
4  right_joint_5.pos
5  right_joint_6.pos
6  right_joint_7.pos
7  right_gripper.pos
8  left_joint_1.pos
9  left_joint_2.pos
10 left_joint_3.pos
11 left_joint_4.pos
12 left_joint_5.pos
13 left_joint_6.pos
14 left_joint_7.pos
15 left_gripper.pos
```

Gate:

- continue only if policy load and action contract pass.

## Phase 3: syhlabtop Camera Discovery

Purpose: bind physical cameras to policy names.

Do this before connecting robot motors.

On `syhlabtop`:

```bash
cd /home/syhlabtop/workspace/lerobot
uv run lerobot-find-cameras opencv \
  --output-dir <syhlabtop-work-root>/camera_maps/2026-05-11_opencv_probe \
  --record-time-s 3
```

If using RealSense as RealSense, run:

```bash
uv run lerobot-find-cameras realsense \
  --output-dir <syhlabtop-work-root>/camera_maps/2026-05-11_realsense_probe \
  --record-time-s 3
```

Document:

| Required key | Device path/serial | Resolution | Physical view | Orientation OK? |
| --- | --- | --- | --- | --- |
| `left_wrist` | TBD | `1280x720` target | left wrist | TBD |
| `right_wrist` | TBD | `1280x720` target | right wrist | TBD |
| `base` | TBD | `640x480` target | base/third-person | TBD |

Gate:

- continue only if all three views are identified and named.

## Phase 4: syhlabtop CAN And Calibration Probe

Purpose: document CAN side mapping and calibration IDs before policy testing.

Do not use policy rollout in this phase.

Checklist:

- identify physical left arm CAN interface,
- identify physical right arm CAN interface,
- confirm left config uses `side=left`,
- confirm right config uses `side=right`,
- confirm calibration ID used for the bimanual follower,
- confirm gripper zero means closed,
- confirm E-stop and power cutoff path.

Known warning:

Example docs are inconsistent about `can0`/`can1` assignment. Do not copy example port order blindly. The physical `syhlabtop` mapping wins.

Tentative config shape once ports are known:

```bash
--robot.type=bi_openarm_follower \
--robot.left_arm_config.port=<LEFT_CAN> \
--robot.left_arm_config.side=left \
--robot.right_arm_config.port=<RIGHT_CAN> \
--robot.right_arm_config.side=right \
--robot.id=syhlabtop_openarm_folding_20260511
```

Gate:

- continue only if left/right mapping is unambiguous.

## Phase 5: No-Send Shadow Path Decision

Purpose: decide how to produce policy actions without sending them.

Current repo state:

- `OpenArmFollower.connect()` enables torque.
- `send_next_action()` sends processed actions through `robot_wrapper.send_action`.
- `SyncInferenceEngine` is rejected for `folding_latest` because relative actions are enabled.
- RTC is local-thread async, not a remote A6000 service.

Therefore there is no already-audited command-line path for live no-send shadow rollout on the physical robot.

Choose one of these paths before continuing:

| Path | Description | Recommended for 2026-05-11 |
| --- | --- | --- |
| A | A6000 offline policy only; syhlabtop hardware mapping only | Yes |
| B | syhlabtop captures observation snapshots, A6000 computes actions offline, no robot send | Yes, if a no-send capture script is reviewed |
| C | live split-host inference with A6000 and syhlabtop robot IO | No, blocked by missing remote inference bridge |
| D | live autonomous `lerobot-rollout` on robot | No |

Gate:

- continue only with Path A or B unless a reviewed no-send implementation exists.

## Phase 6: Shadow Action Review

Purpose: inspect proposed policy outputs without motion.

For each tested observation:

Record:

```text
timestamp
source machine
observation state 16-vector
camera frame IDs or filenames
policy action 16-vector
postprocessed absolute action dict
limit-clamped action dict
reason action was not sent
```

Review checks:

- length is 16,
- keys match exact order,
- all values are finite,
- arm joints are absolute degrees after postprocessor,
- grippers are absolute degree targets,
- grippers are inside `[-65, 0]` or visibly clamped,
- deltas from current state are small enough for the intended safety gate,
- action timestamp corresponds to current observation.

Suggested CSV columns:

```text
timestamp,obs_id,action_id,key,current_deg,proposed_deg,clamped_deg,delta_deg,limit_min,limit_max,send_allowed
```

For Gate 1, every `send_allowed` value must be `false`.

## Phase 7: Motion Gate, Not Default For Tomorrow

Do not enter this phase unless all previous gates pass and a separate explicit go decision is made.

Before any policy-generated motion:

- implement or identify a safety gate on `syhlabtop`,
- clamp each joint to configured limits,
- enforce per-tick delta/rate limits,
- reject stale A6000 actions,
- reject missing camera frames,
- reject mismatched action order,
- set `return_to_initial_position=false` unless deliberately testing return motion,
- confirm E-stop,
- keep one operator at the machine and one observer at the robot.

Initial motion, if later approved, should not be autonomous folding. It should be a single reviewed low-delta hold/near-hold command.

## Known Safe Commands For Tomorrow

These commands are acceptable for discovery and preflight:

```bash
git status --short --branch
git branch --show-current
uv run lerobot-find-cameras opencv --output-dir <syhlabtop-work-root>/camera_maps/2026-05-11_opencv_probe --record-time-s 3
uv run lerobot-find-cameras realsense --output-dir <syhlabtop-work-root>/camera_maps/2026-05-11_realsense_probe --record-time-s 3
```

These commands are not acceptable as first actions:

```bash
uv run lerobot-rollout ...
uv run lerobot-record ...
uv run lerobot-replay ...
```

Reason: these are control/record/replay paths that may connect hardware and send actions unless separately reviewed and configured.

## Expected End State For 2026-05-11

Minimum acceptable end state:

- A6000 model files present and loadable.
- `syhlabtop` camera map documented.
- `syhlabtop` CAN/calibration map documented.
- no-send shadow architecture decision recorded.
- no robot motion from policy.

Better end state:

- one or more observation snapshots reviewed,
- A6000 produced postprocessed 16-dim absolute actions,
- action review CSV completed with `send_allowed=false`,
- list of code changes required for a true no-send/live shadow mode is ready.

## Required Follow-up Work

Before live shadow or motion, implement or verify:

1. no-send policy evaluation path,
2. split-host inference bridge or same-host execution decision,
3. action safety gate on `syhlabtop`,
4. stale-action and heartbeat rejection,
5. camera timestamp and orientation validation,
6. action-order assertion against `folding_latest/config.json`,
7. explicit operator confirmation before any call to `send_action()`.
