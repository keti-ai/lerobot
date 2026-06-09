# LR Dataset Replay (Clean Dataset -> OpenArm)

Date: 2026-06-10

## Objective

Replay the clean dataset actions open-loop on the current OpenArm/banana setup to separate data/embodiment issues from policy execution issues.

- Dataset: `KETI-IRRC/openarm_handover_v0_20260521_202117_clean`
- Episode: `0`
- Robot config: K4 bimanual OpenArm follower config
- Safety cap: arm joints `15.0 deg`, gripper `65.0 deg`
- FPS: dataset/replay `30`
- Operator: present with power abort/E-stop
- a6000 policy server: not used

## Wrapper

Added `audits/openarm_folding/replay_runner.py`.

The wrapper reuses the validated K4 robot construction:

- `bi_openarm_follower`
- CAN: left `can0`, right `can1`
- RealSense:
  - `left_wrist`: `315122270766`
  - `right_wrist`: `230322273311`
  - `base`: `213622075840`
- `max_relative_target` is required and refuses non-positive caps.

The replay loop follows `lerobot-replay`:

1. `dataset[idx][action]`
2. default robot action processor
3. `robot.get_observation()`
4. `robot.send_action()`
5. `precise_sleep(1 / fps)`

It also logs a 3 second countdown before motion and disconnects the robot in `finally`.

## Feature Mapping

Dry-run verified the dataset action order and robot action feature order match exactly:

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

Dry-run output:

- `/home/syhlabtop/k4_logs/replay_dry_episode_0.json`
- `num_frames`: `897`
- dataset FPS: `30`

## Physical Replay

Two operator-supervised replays were run for episode `0`.

| run | log | frames | elapsed | clamp events | clamp joints | CAN after |
|---|---|---:|---:|---:|---|---|
| LR-01 | `/home/syhlabtop/k4_logs/lr_replay_episode0.log` | 897/897 | 49.55s | 3 | `joint_4:2`, `joint_7:1` | `can0/can1 UP` |
| LR-02 | `/home/syhlabtop/k4_logs/lr_replay_episode0_retry1.log` | 897/897 | 49.22s | 4 | `joint_4:2`, `joint_7:2` | `can0/can1 UP` |

The clamp events occurred at the beginning and are consistent with the first-frame ramp toward the dataset start pose. There was no sustained clamp problem.

Latest summary:

- `/home/syhlabtop/k4_logs/replay_summary_episode_0.json`

## Operator Observation

The physical replay completed, but the gripper did not visibly actuate. This means the replay did not validate successful grasp/place behavior.

## Gripper Action Check

Read-only analysis of episode `0` shows the clean dataset does contain close commands:

| channel | min command | max command | frames `< -10` | frames `< -30` | frames `< -50` | min frame |
|---|---:|---:|---:|---:|---:|---:|
| right_gripper.pos | -46.8 | -0.0 | 540 | 396 | 0 | 600 |
| left_gripper.pos | -54.8 | -0.0 | 371 | 314 | 107 | 714 |

So the immediate failure is not explained by missing gripper close commands in the dataset.

## Initial Diagnosis

Initial upstream-style replay result: **FAIL**.

Reason:

- Open-loop action replay completed all frames.
- Action feature order matches robot feature order.
- Dataset episode includes substantial gripper close commands.
- Operator observed no physical gripper actuation.

This initial diagnosis was later narrowed by the gripper probe and action-only replay. The dataset has close actions, the gripper motor path works, and action-only replay sends/executes those close commands. The remaining replay sensitivity is start pose / object pose / open-loop timing alignment, not gripper cap or motor mapping.

## Follow-Up

Prior D07c evidence shows the same robot/control stack can close both grippers:

| signal | min | max | mean |
|---|---:|---:|---:|
| D07c right_cmd | -50.342 | 0.608 | -18.917 |
| D07c right_readback | -49.998 | -0.011 | -25.041 |
| D07c left_cmd | -55.184 | 1.546 | -35.213 |
| D07c left_readback | -54.959 | 0.208 | -35.175 |

This makes the replay-specific gripper failure actionable: compare replay/probe command, sent action, and readback under the same local robot path.

## LR Gripper Probe Result

Probe command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --gripper-probe \
  --probe-values=-20,-45,0 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_gripper_probe_episode0.csv
```

Outputs:

- log: `/home/syhlabtop/k4_logs/lr_gripper_probe_episode0.log`
- trace: `/home/syhlabtop/k4_logs/lr_gripper_probe_episode0.csv`
- summary: `/home/syhlabtop/k4_logs/replay_summary_episode_0.json`

Result:

- completed `90` probe frames
- clamp events: `0`
- post-disconnect CAN: `can0/can1 UP`

Trace summary:

| side | target | sent last | readback first | readback last | readback mean |
|---|---:|---:|---:|---:|---:|
| right | -20 | -20.0 | -0.011 | -20.097 | -19.481 |
| right | -45 | -45.0 | -20.097 | -45.036 | -44.266 |
| right | 0 | 0.0 | -45.036 | -0.098 | -2.035 |
| left | -20 | -20.0 | -0.011 | -19.944 | -19.268 |
| left | -45 | -45.0 | -19.966 | -45.014 | -44.185 |
| left | 0 | 0.0 | -45.014 | -0.011 | -1.947 |

Decision:

- The local replay robot path can close and open both grippers.
- The gripper cap, motor mapping, and readback path are not the blocker.
- The remaining replay failure is more likely replay timing/fidelity, grasp phase timing, object alignment, or the fact that the original wrapper replayed at about `18 FPS` instead of the dataset `30 FPS`.

## Action-Only Replay Result

The first physical replays followed upstream `lerobot-replay` and called `robot.get_observation()` every frame. On this setup that reads 3 cameras, so `897` dataset frames took about `49s` instead of the expected `29.9s`. That changes the demonstration timebase.

`replay_runner.py` now supports:

```text
--action-only
```

This mode sends the 16D dataset action sequence without per-frame camera observation. If trace is enabled, it reads only gripper motor positions through the CAN bus, so it can preserve the dataset FPS much more closely.

Action-only replay command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --action-only \
  --gripper-trace /home/syhlabtop/k4_logs/lr_replay_action_only_trace_episode0.csv
```

Outputs:

- log: `/home/syhlabtop/k4_logs/lr_replay_action_only_episode0.log`
- trace: `/home/syhlabtop/k4_logs/lr_replay_action_only_trace_episode0.csv`
- summary: `/home/syhlabtop/k4_logs/replay_summary_episode_0.json`

Result:

- sent frames: `897/897`
- control elapsed: `30.02s`
- effective control FPS: `29.88`
- clamp events: `3` (`joint_4:1`, `joint_7:2`), all at the start ramp
- post-disconnect CAN: `can0/can1 UP`

Gripper trace:

| side | cmd min | sent min | readback min | close frame count |
|---|---:|---:|---:|---:|
| right | -46.782 | -46.782 | -46.785 | `cmd <= -30`: 396 |
| left | -54.777 | -54.777 | -54.413 | `cmd <= -30`: 314 |

Operator observation:

- The robot approached the banana.
- The gripper actuated.
- Full grasp/place parity is not yet confirmed.

Decision:

- Action replay timing is now close to the dataset FPS.
- Gripper command/sent/readback are correct during replay.
- Remaining mismatch is likely from open-loop start condition: current robot pose and banana pose must match the dataset episode start closely. The safety cap prevents jumps, but it does not make the absolute replay invariant to different initial pose.

## Start Pose Sensitivity

The dataset action sequence is absolute joint target replay. If the current robot starts away from the dataset episode start, the first frames become a cap-limited catch-up ramp. That is safe, but it can shift timing and contact geometry before the grasp phase.

`replay_runner.py` now supports:

```text
--prealign-start-s
```

This holds dataset frame `0` for a fixed duration before starting the episode clock and logs start error before/after pre-align.

Next physical replay command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --action-only \
  --prealign-start-s 3 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_replay_action_only_prealign_trace_episode0.csv
```

Expected checks:

- start error after pre-align is smaller than before pre-align
- `effective_control_fps` remains close to `30`
- operator verifies approach/grasp/place with banana placed at the dataset-matching start location

## Prealign Replay Result

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --action-only \
  --prealign-start-s 3 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_replay_action_only_prealign_trace_episode0.csv
```

Outputs:

- log: `/home/syhlabtop/k4_logs/lr_replay_action_only_prealign_episode0.log`
- trace: `/home/syhlabtop/k4_logs/lr_replay_action_only_prealign_trace_episode0.csv`
- summary: `/home/syhlabtop/k4_logs/replay_summary_episode_0.json`

Result:

- prealign frames: `90`
- sent frames: `897/897`
- control elapsed: `30.03s`
- effective control FPS: `29.87`
- clamp events: `2` (`joint_4:1`, `joint_7:1`), during prealign
- post-disconnect CAN: `can0/can1 UP`

Start error:

| metric | before prealign | after prealign |
|---|---:|---:|
| max arm abs error | 19.57 deg | 1.07 deg |
| mean arm abs error | 7.24 deg | 0.30 deg |
| max gripper abs error | 9.45 deg | 0.08 deg |

Gripper trace during replay:

| side | cmd min | sent min | readback min | close frame count |
|---|---:|---:|---:|---:|
| right | -46.782 | -46.782 | -21.933 | `cmd <= -30`: 396 |
| left | -54.777 | -54.777 | -18.699 | `cmd <= -30`: 314 |

Operator observation:

- The robot approached the banana and the gripper actuated, but the gripper closed outside / beside the banana rather than capturing it cleanly.

Decision:

- Prealign fixed the robot start-pose error.
- The replay still misses because the object pose is not matching the dataset start condition closely enough.
- The low gripper readback at high close commands is consistent with contact or mechanical obstruction during a bad approach, not command loss. The separate gripper-only probe closed both grippers to `-45`.

## Object Placement Reference

Reference frames were dumped from dataset episode `0`:

```text
/home/syhlabtop/k4_logs/lr_episode0_reference_frames/
```

Contact sheet:

```text
/home/syhlabtop/k4_logs/lr_episode0_reference_frames/episode0_reference_contact_sheet.png
```

Use `frame_0000_observation_images_base.png` for banana starting pose. In the dataset start, the banana is on the white table to the left of the blue tray, not centered inside the tray. The later `frame_0300` through `frame_0714` views show the gripper approach/contact geometry. For the next retry, match both:

- robot start pose via `--prealign-start-s 3`
- banana pose/orientation from the reference base image

## Video-Matched Retry

After matching the scene from the replay reference video/images, `retry2` was run with action-only replay and 3s prealign:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --action-only \
  --prealign-start-s 3 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_replay_action_only_prealign_trace_episode0_retry2.csv
```

The replay completed all action frames, but summary writing was interrupted by a RealSense disconnect exception because the action-only path still had cameras configured. The trace is complete:

| metric | value |
|---|---:|
| trace rows | 987 (`90` prealign + `897` replay) |
| prealign start error, max arm | 19.57 deg -> 1.10 deg |
| prealign start error, max gripper | 9.45 deg -> 0.08 deg |

Replay gripper trace:

| side | cmd min | sent min | readback min | close frame count | readback at min-cmd frame |
|---|---:|---:|---:|---:|---:|
| right | -46.782 | -46.782 | -46.326 | `cmd <= -30`: 396 | -44.577 |
| left | -54.777 | -54.777 | -54.478 | `cmd <= -30`: 314 | -53.211 |

Decision:

- Dataset action contains strong close commands.
- The replay path sends those commands without clipping them away.
- Motor readback reaches the commanded close range when the object pose is matched from reference.
- Remaining replay success/failure is dominated by physical scene alignment and open-loop sensitivity, not gripper mapping or missing dataset grasp.

Tooling follow-up:

- `--action-only` and `--gripper-probe` now omit camera configuration because neither path needs RealSense observations.
- Disconnect is wrapped with best-effort CAN cleanup so a camera shutdown exception cannot hide replay trace/summary results.

## Trace Tools

`replay_runner.py` supports optional replay gripper trace logging:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_replay_gripper_trace_episode0.csv
```

It also supports a safer gripper-only probe that holds the arms at the current pose and sends close/open targets:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --gripper-probe \
  --probe-values=-20,-45,0 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_gripper_probe_episode0.csv
```

If `--gripper-probe` is used without `--gripper-trace`, the wrapper writes:

```text
/home/syhlabtop/k4_logs/lr_gripper_probe_episode0.csv
```

The trace records per frame:

- raw gripper command
- processed action
- sent action returned by `robot.send_action`
- gripper readback before/after send

Use the probe before further full replays. If command/sent values go negative but readback stays open, the next target is motor/control mapping under the local replay path. If the probe works but full replay does not, inspect replay timing, gripper close phase, and object alignment rather than dataset action absence.
