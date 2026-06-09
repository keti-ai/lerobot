# K9 Gripper Close Diagnosis

Date: 2026-06-09
Machine: `syhlabtop`
Branch: `audit/openarm-folding-baseline`
Baseline commit checked: `a222fb8c`

## Goal

D07b reached the grasp phase under the warm RTC server and `diag_arm_cap`
profile (`arm=15.0`, `gripper=65.0`), but the banana appeared to slip because
the grasp was weak. This diagnosis separates two hypotheses:

1. The policy is not issuing a strong close command.
2. The policy issues a strong close command, but the live gripper motor does
   not reach it because of mapping/cap/motor behavior.

This pass is read-only and uses D07b logs only. No live motion was run.

## Contract

- 16D action gripper indices:
  - index `7`: right gripper
  - index `15`: left gripper
- Gripper command range: `[-65, 0]` degrees.
- Negative means close; `0` means open.
- Training uses `relative_exclude_joints=["gripper"]`, so gripper is an
  absolute target.
- D07b live profile uses `gripper_max_relative_target=65.0`.

## Available Logs

D07b artifacts inspected:

- `/home/syhlabtop/k4_logs/trial_D07b_banana.log`
- `/home/syhlabtop/k4_logs/k4_runner_trial_D07b_banana.debug.log`
- `/home/syhlabtop/k4_logs/summary_trial_D07b.json`
- `/home/syhlabtop/k4_logs/queue_trial_D07b.json`

The current client debug log does not record raw 16D action tensors or the
performed action dictionary. It records action timestep execution, queue state,
latency, and gripper joint-limit clipping when clipping occurs.

## D07b Execution Context

Summary:

```json
{
  "trial": "D07b",
  "profile": "diag_arm_cap",
  "duration_s": 30.0,
  "last_avg_fps": 21.94,
  "max_net_latency_ms": 685.42,
  "queue_empty_cnt": 1,
  "clamp_events": 3,
  "clamp_joint_counts": {
    "joint_4": 3
  },
  "action_queue_samples": 684
}
```

The receiver stayed alive and actions continued through the full control
window.

## Gripper Command Evidence

Command-line checks:

```bash
grep -i "gripper\|action\|send" /home/syhlabtop/k4_logs/trial_D07b_banana.log | head -40
grep -i "readback\|observation.state\|_performed\|sent_action" /home/syhlabtop/k4_logs/trial_D07b_banana.log | head -30
grep -i "readback\|observation.state\|_performed\|sent_action\|Present_Position\|right_gripper\|left_gripper" \
  /home/syhlabtop/k4_logs/k4_runner_trial_D07b_banana.debug.log | head -80
```

Findings:

- `trial_D07b_banana.log` contains config, action chunk timesteps, FPS, and
  latency, but not raw action values.
- No `readback`, `observation.state`, `_performed`, `sent_action`,
  `right_gripper`, or `left_gripper` value series was found in the logs.
- The only gripper value evidence is joint-limit clipping in
  `k4_runner_trial_D07b_banana.debug.log`.

Gripper clipping statistics from the debug log:

```text
performed_count: 684
performed_action_range: 0..681
gripper_clip_count: 102
clip_from_min: +0.01 deg
clip_from_max: +1.84 deg
clip_from_mean: +0.569 deg
negative_clip_count: 0
positive_clip_count: 102
clip_target: 0.00 deg for all clips
```

Example log lines:

```text
Clipped gripper from 0.17° to 0.00°
Clipped gripper from 0.88° to 0.00°
Clipped gripper from 1.84° to 0.00°
```

Interpretation:

- All observed gripper clips are open-side clips: small positive commands
  outside the valid range were clipped to `0.00`.
- There are zero close-side clips. No log line shows a command below `-65` or
  an attempted strong close being clipped at the close limit.
- This does not prove that every in-range gripper command was weak, because
  in-range negative commands are not logged by the current client.
- It does prove that the available D07b logs contain no evidence of a strong
  close target such as `-65`.

## Command vs Motor Readback

The D07b logs do not contain gripper motor readback values aligned with sent
commands. Therefore:

- Cannot confirm whether a strong close command was sent and the motor failed
  to reach it.
- Cannot quantify command-vs-actual tracking error.
- Cannot classify a motor/mapping failure from D07b logs alone.

## Judgment

Based strictly on available log data:

- Strong close command evidence: not found.
- Motor failure evidence: not found.
- Best-supported diagnosis: policy/data close-command weakness is more likely
  than a gripper motor/cap failure, because the only observed gripper command
  evidence is small open-side clipping and no strong negative close command is
  visible.

This is not a definitive proof, because the D07b log did not record the raw
gripper action series. The correct next diagnostic is to add lightweight
read-only logging of gripper command and readback during the next operator-run
trial, or run a gripper-only probe if log-only evidence remains insufficient.

## Next Branch

Recommended next step:

1. Add diagnostic logging for each performed action:
   - action timestep
   - command index `7` and `15`
   - mapped action keys for both grippers
   - returned/performed gripper action if available
   - present gripper position readback if affordable
2. Repeat a short diagnostic under the D07b-good execution path:
   `arm=15.0`, `gripper=65.0`, RTC warm server.
3. If commands stay around `0` to weak negatives rather than approaching
   `-65`, treat this as a data/policy issue. Banana close-command density was
   already known to be sparse, so data reinforcement or a better init is the
   likely branch.
4. If commands reach strong negatives but readback remains open or weak, treat
   this as a gripper mapping/motor/control issue and fix infrastructure.

No gripper-only motion probe was run in this K9 pass.
