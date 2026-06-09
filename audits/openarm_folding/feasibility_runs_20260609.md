# K4 live feasibility runs - 2026-06-09

## Status

Official K4 is paused after trial `01-02`. Both official trials used banana and both were failures. Do not continue the N=20 official count until the diagnostic sequence below passes.

Diagnostic trials are not part of the official success rate. Write diagnostic rows to `/home/syhlabtop/k4_logs/diagnostic_results.csv`, not to `/home/syhlabtop/k4_logs/trial_results.csv`.

## Official K4 Trials

| trial | object | result | last Avg FPS | max latency | queue empty | clamp events | operator note |
|---|---|---:|---:|---:|---:|---:|---|
| 01 | banana | F | 21.69 | 813.71 ms | 3 | 1318 | grasp failed; motion was very choppy |
| 02 | banana | F | 4.75 | 1151.12 ms | 0 | 898 | approach tendency visible, but gripper grasp was almost absent; chunk-to-chunk jumps visible |

Official result CSV:

```text
/home/syhlabtop/k4_logs/trial_results.csv
```

Sidecar logs:

```text
/home/syhlabtop/k4_logs/summary_trial_01.json
/home/syhlabtop/k4_logs/summary_trial_02.json
/home/syhlabtop/k4_logs/queue_trial_01.json
/home/syhlabtop/k4_logs/queue_trial_02.json
```

## Working Diagnosis

Current failures look more likely to come from live recipe mismatch, low loop FPS, and gripper clamp behavior than from a too-small chunk size.

Confirmed aligned:

- Robot type: `bi_openarm_follower`
- Runtime FPS target: 30
- Cameras: 3 RealSense streams at 640x480
- Action/state order: 16D right arm/gripper then left arm/gripper

Major gaps:

- Training used `relative_exclude_joints=["gripper"]`, so gripper targets are absolute. Live K4 applied `max_relative_target=5.0` to the gripper too, which can cut off close commands.
- Checkpoint config wrist shape is 720x1280, while handover dataset/live wrist streams are 480x640. Resize absorbs this mechanically, but it is still a recipe mismatch.
- Locked recipe values `rtc_execution_horizon=20` and `action_interpolation_multiplier=3` are not applied by the current async inference wrapper.

Data risk:

- Clean dataset has 60 episodes total; banana has 19 clean episodes.
- Banana close-command density is sparse: right gripper about 6.5%, left gripper about 1.2%.
- Init is from folding/open dataset step `004000`, which gives OpenArm prior but weak handover/grasp prior.

## Diagnostic Profiles

The runner now supports these profiles:

| profile | max relative target | chunk threshold | aggregate | logging |
|---|---|---:|---|---|
| `k4` | all joints `5.0` | 0.5 | `weighted_average` | official settings; clamp warnings suppressed on console |
| `diag_baseline_silent` | all joints `5.0` | 0.5 | `weighted_average` | suppress clamp warnings in console/file, count in JSON |
| `diag_gripper_cap` | arm joints `5.0`, gripper `65.0` | 0.5 | `weighted_average` | suppress clamp warnings in console/file, count in JSON |
| `diag_queue_smooth` | arm joints `5.0`, gripper `65.0` | 0.9 | `conservative` | suppress clamp warnings in console/file, count in JSON |

Each summary JSON records:

- `clamp_events`
- `clamp_joint_counts`
- `last_avg_fps`
- `max_net_latency_ms`
- `queue_empty_cnt`

`queue_empty_cnt` is counted as runtime transitions into an empty action queue after at least one action has been performed.

## Diagnostic Sequence

Preflight before every diagnostic:

- Server `10.252.205.103:8081` is reachable.
- `can0` and `can1` are UP.
- RealSense serials `315122270766`, `230322273311`, and `213622075840` are visible.
- Operator is on-site with power abort / E-stop ready.

Use the same task prompt for all diagnostics:

```text
Pick the banana, hand it over to the other arm, and place it at the target.
```

D01:

```bash
uv run python audits/openarm_folding/k4_eval_runner.py \
  --trial D01 \
  --obj banana \
  --profile diag_baseline_silent \
  --duration-s 30 \
  --task "Pick the banana, hand it over to the other arm, and place it at the target."
```

Purpose: test whether removing clamp-warning log spam alone recovers FPS.

D02:

```bash
uv run python audits/openarm_folding/k4_eval_runner.py \
  --trial D02 \
  --obj banana \
  --profile diag_gripper_cap \
  --duration-s 30 \
  --task "Pick the banana, hand it over to the other arm, and place it at the target."
```

Purpose: test whether absolute gripper targets can close and grasp when gripper cap is raised to `65.0`.

D03:

```bash
uv run python audits/openarm_folding/k4_eval_runner.py \
  --trial D03 \
  --obj banana \
  --profile diag_queue_smooth \
  --duration-s 30 \
  --task "Pick the banana, hand it over to the other arm, and place it at the target."
```

Purpose: test whether threshold/aggregation tuning reduces chunk-to-chunk jump or skip behavior.

Expected outputs:

```text
/home/syhlabtop/k4_logs/summary_trial_D01.json
/home/syhlabtop/k4_logs/summary_trial_D02.json
/home/syhlabtop/k4_logs/summary_trial_D03.json
/home/syhlabtop/k4_logs/queue_trial_D01.json
/home/syhlabtop/k4_logs/queue_trial_D02.json
/home/syhlabtop/k4_logs/queue_trial_D03.json
/home/syhlabtop/k4_logs/diagnostic_results.csv
```

## Decision Rules

- If D01 FPS recovers strongly, clamp-warning logging overhead is a live FPS bottleneck.
- If D02 makes the gripper close and grasp behavior returns, gripper cap mismatch is the primary cause.
- If D03 reduces visual jumps, K4 can resume with async queue/aggregation tuning.
- If all three diagnostics fail, stop K4 and move alpha triple-prime toward data reinforcement or switch live execution to RTC/official rollout.

Resume official K4 only if:

- `last_avg_fps >= 20`
- `max_net_latency_ms < 1000`
- gripper clamp events are nearly gone
- operator visually confirms approach, close, and lift attempt

## Wrapper Verification

Completed before live diagnostic execution:

```bash
uv run python -m py_compile audits/openarm_folding/k4_eval_runner.py
uv run python audits/openarm_folding/k4_eval_runner.py --config-only --trial CFG --obj banana --profile k4 --task "Pick the banana, hand it over to the other arm, and place it at the target."
uv run python audits/openarm_folding/k4_eval_runner.py --config-only --trial CFG --obj banana --profile diag_baseline_silent --task "Pick the banana, hand it over to the other arm, and place it at the target."
uv run python audits/openarm_folding/k4_eval_runner.py --config-only --trial CFG --obj banana --profile diag_gripper_cap --task "Pick the banana, hand it over to the other arm, and place it at the target."
uv run python audits/openarm_folding/k4_eval_runner.py --config-only --trial CFG --obj banana --profile diag_queue_smooth --task "Pick the banana, hand it over to the other arm, and place it at the target."
```

Result: PASS. Config-only did not connect hardware or server.
