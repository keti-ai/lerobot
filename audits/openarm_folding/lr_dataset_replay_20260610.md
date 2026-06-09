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

## Diagnosis

Replay result: **FAIL**.

Reason:

- Open-loop action replay completed all frames.
- Action feature order matches robot feature order.
- Dataset episode includes substantial gripper close commands.
- Operator observed no physical gripper actuation.

This points to a remaining live gripper actuation / readback / motor-control path issue for replay, rather than a policy-only issue. The dataset has close actions, but the current replay path did not produce visible gripper closure.

## Follow-Up

`replay_runner.py` now supports optional gripper trace logging:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/replay_runner.py \
  --episode 0 \
  --gripper-trace /home/syhlabtop/k4_logs/lr_replay_gripper_trace_episode0.csv
```

The trace records per frame:

- raw gripper command
- processed action
- sent action returned by `robot.send_action`
- gripper readback before/after send

Use this before further conclusions about steering or dataset quality. If command/sent values go negative but readback stays open, the next target is motor/control mapping. If command is lost before send, the replay wrapper/action processor path is the target.
