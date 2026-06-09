# D07c Gripper Command + Readback Trace

Date: 2026-06-09
Machine: syhlabtop
Trial: D07c banana
Profile: `diag_arm_cap` (arm max_relative_target 15.0, gripper max_relative_target 65.0)
Server: `10.252.205.103:8081` K8a RTC warm server

## Purpose

K9 showed only indirect evidence around gripper behavior: all gripper clipping was on the open side, but raw command and motor readback were not logged. D07c added a lightweight trace to decide whether weak grasp is caused by:

- weak policy close commands, or
- strong close commands that the live gripper motor does not reach.

## Logging Change

`audits/openarm_folding/k4_eval_runner.py` now enables D07c-only gripper trace logging:

- wraps `client.robot.send_action`
- records command action and performed action for `right_gripper.pos` and `left_gripper.pos`
- reads live motor `Present_Position` for both grippers
- writes `/home/syhlabtop/k4_logs/gripper_trace_D07c.csv`

CSV columns:

```text
step,right_cmd,right_performed,right_readback,left_cmd,left_performed,left_readback
```

This is diagnostics-only and does not change action values or control logic.

## Trial Summary

Summary file: `/home/syhlabtop/k4_logs/summary_trial_D07c.json`

```text
status: completed_control_window
duration_s: 30.0
last_avg_fps: 22.54
max_net_latency_ms: 908.09
queue_empty_cnt: 19
action_queue_samples: 661
clamp_events: 12
clamp_joint_counts: {'joint_4': 10, 'joint_7': 2}
gripper_trace_rows: 661
receiver_thread_alive_after_join: False
control_thread_alive_after_join: False
thread_errors: []
```

The trial completed the 30s control window and wrote 661 gripper trace rows.

## Gripper Trace Results

Trace file: `/home/syhlabtop/k4_logs/gripper_trace_D07c.csv`

| signal | min | max | mean |
|---|---:|---:|---:|
| right_cmd | -50.342 | 0.608 | -18.917 |
| right_performed | -50.342 | 0.000 | -18.926 |
| right_readback | -49.998 | -0.011 | -25.041 |
| left_cmd | -55.184 | 1.546 | -35.213 |
| left_performed | -55.184 | 0.000 | -35.231 |
| left_readback | -54.959 | 0.208 | -35.175 |

Close counts:

| side | cmd <= -10 | cmd <= -20 | cmd <= -40 |
|---|---:|---:|---:|
| right | 293 | 286 | 197 |
| left | 534 | 519 | 409 |

Most closed command points:

| side | row | step | cmd | performed | readback | cmd-readback |
|---|---:|---:|---:|---:|---:|---:|
| right | 145 | 143 | -50.342 | -50.342 | -48.905 | -1.437 |
| left | 418 | 416 | -55.184 | -55.184 | -54.347 | -0.836 |

Tracking gap:

| side | mean abs cmd-readback gap | max gap | mean abs cmd-performed gap |
|---|---:|---:|---:|
| right | 6.73 | 24.11 | 0.01 |
| left | 0.68 | 32.38 | 0.02 |

The command-to-performed gap is effectively zero except open-side clipping to `0.0`, which is expected from the gripper range. At the most closed points, motor readback is within about 1.5 degrees of command.

## Operator Observation

No operator note was provided in the Codex thread for D07c before commit. The decision below is based on the command/performed/readback trace and trial summary.

## Decision

D07c does not support the hypothesis that the gripper motor mapping or cap is preventing close motion:

- policy commands reach strong close values (`right -50.3`, `left -55.2`) within the configured `[-65, 0]` range
- performed actions preserve those close commands
- live readback reaches nearly the same close values at the strongest close points
- no gripper clamp events remain in the summary

Therefore the weak grasp/slip is not primarily a gripper cap or motor readback failure. The remaining likely causes are grasp geometry, timing, contact alignment, or policy/data limitations in the grasp strategy. This is narrower than the K9 provisional "model weak close" diagnosis: the model does command substantial close, but the behavior is still not producing a reliable physical grasp.

## Next Branch

Recommended next branch:

1. Keep `diag_arm_cap` style caps (`arm15/grip65`) for live diagnostics.
2. Do not spend time on gripper cap/mapping unless a separate mechanical probe shows mismatch under load.
3. Prioritize data/policy improvement around banana grasp contact quality:
   - more banana episodes with clear approach-contact-close-lift timing
   - stronger examples of sustained close while lifting/handover
   - examples with small pose errors and recovery/regrasp
4. If doing one more infrastructure diagnostic first, inspect gripper physical contact width/force under load, not command/readback mapping.
