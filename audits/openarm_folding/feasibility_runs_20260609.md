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

## D02 Result

Run:

```text
trial: D02
profile: diag_gripper_cap
object: banana
duration: 30 s
summary: /home/syhlabtop/k4_logs/summary_trial_D02.json
queue: /home/syhlabtop/k4_logs/queue_trial_D02.json
diagnostic CSV: /home/syhlabtop/k4_logs/diagnostic_results.csv
```

There was one pre-motion invalid setup attempt at 16:11 KST where left-arm
CAN handshake failed on `joint_1`. Those sidecar files were archived with
`.invalid_setup_20260609_161342`. The valid D02 retry completed the 30 s
control window and did not touch `/home/syhlabtop/k4_logs/trial_results.csv`.

Summary metrics:

```json
{
  "status": "completed_control_window",
  "last_avg_fps": 19.86,
  "max_net_latency_ms": 1164.84,
  "queue_empty_cnt": 0,
  "clamp_events": 426,
  "clamp_joint_counts": {
    "joint_1": 136,
    "joint_2": 53,
    "joint_3": 65,
    "joint_4": 204,
    "joint_5": 138,
    "joint_6": 18,
    "joint_7": 119
  }
}
```

Official 01-02 vs D02:

| metric | trial 01 | trial 02 | D02 | interpretation |
|---|---:|---:|---:|---|
| last Avg FPS | 21.69 | 4.75 | 19.86 | recovered vs trial 02, but still below resume threshold `>=20` |
| max latency | 813.71 ms | 1151.12 ms | 1164.84 ms | still above resume threshold `<1000 ms` |
| queue empty | 3 | 0 | 0 | queue starvation was not the D02 bottleneck |
| clamp events | 1318 | 898 | 426 | lower absolute count, but D02 was 30 s vs official 60 s |
| gripper clamp | present in prior logs | present in prior logs | 0 counted | gripper cap 65 removed gripper relative-target clamps |
| operator grasp | fail | almost none | no attempt | run did not reach a meaningful grasp attempt |

Operator observation:

- Grasp result: `no attempt`.
- Motion was still choppy.
- The robot did not reach a meaningful grasping phase at all.
- There was still residual stutter/slip, and gripper motion looked awkward when it moved.

Clamp analysis:

- `diag_gripper_cap` did what it was designed to do at the clamp layer:
  `clamp_joint_counts` has no `gripper` entry.
- The remaining clamp load is arm-only and still high, led by `joint_4`
  (`204`), `joint_5` (`138`), `joint_1` (`136`), and `joint_7` (`119`).
- Normalized by duration, D02 still has about `14.2` clamp events/s
  (`426 / 30`), close to trial 02's about `15.0` clamp events/s
  (`898 / 60`). The gripper fix did not remove the broader live-control
  saturation problem.

Decision:

- Gripper cap mismatch is confirmed at the clamp layer, because gripper
  clamps disappeared under cap `65.0`.
- It is not sufficient as the primary root cause of K4 failure: the gripper
  did not reach a meaningful grasp attempt, motion stayed choppy, max latency
  remained over `1000 ms`, and arm clamp events remained high.
- Do not resume official K4 N=20 from this result.

Next branch:

- Run D03 `diag_queue_smooth` to test whether threshold/aggregation reduces
  the remaining choppy motion.
- If D03 does not restore smooth approach and close behavior, add a new arm-cap
  diagnostic profile before official resume. The current evidence suggests
  arm `max_relative_target=5.0` may also be too tight for handover swing, even
  after gripper cap is fixed.

## D04 Setup Status

New profile:

| profile | arm max_rel | gripper max_rel | threshold | aggregate | note |
|---|---:|---:|---:|---|---|
| `diag_arm_cap` | 15.0 | 65.0 | 0.5 | `weighted_average` | arm + gripper cap relaxed |

Rationale for arm cap `15.0`:

- D02 showed arm-only clamp pressure after gripper clamp disappeared:
  `joint_4=204`, `joint_5=138`, `joint_1=136`, `joint_7=119`.
- Relstats frame-delta reference: `mean_abs=1.44`, `q_max=60.7`.
- `15.0` is intentionally between those values: `1.44 << 15.0 << 60.7`.
- This is the first arm-cap relaxation trial, so `15.0` is chosen over `20.0`
  for safety. If D04 reaches the task phase safely but remains over-clamped,
  a later `20.0` diagnostic can be considered.

Verification:

```bash
uv run python -m py_compile audits/openarm_folding/k4_eval_runner.py
uv run python audits/openarm_folding/k4_eval_runner.py \
  --config-only \
  --trial D04 \
  --obj banana \
  --profile diag_arm_cap \
  --duration-s 30 \
  --task "Pick the banana, hand it over to the other arm, and place it at the target."
```

Result: PASS. Config-only showed arm joints at `15.0`, gripper at `65.0`,
threshold `0.5`, and aggregate `weighted_average`.

Live D04 status:

- Attempt 1 at 16:41 KST: pre-motion failure. Left-arm CAN handshake failed on
  `joint_1`; no control window started and no action was sent.
- Attempt 2 at 16:46 KST: same pre-motion failure. Left-arm CAN handshake failed
  on `joint_1`; no control window started and no action was sent.
- Invalid setup artifacts were archived:
  - `/home/syhlabtop/k4_logs/summary_trial_D04.json.invalid_setup_20260609_164223`
  - `/home/syhlabtop/k4_logs/summary_trial_D04.json.invalid_setup_20260609_164635`
  - `/home/syhlabtop/k4_logs/trial_D04_banana.log.invalid_setup_20260609_164223`
  - `/home/syhlabtop/k4_logs/trial_D04_banana.log.invalid_setup_20260609_164635`
  - `/home/syhlabtop/k4_logs/k4_runner_trial_D04_banana.debug.log.invalid_setup_20260609_164223`
  - `/home/syhlabtop/k4_logs/k4_runner_trial_D04_banana.debug.log.invalid_setup_20260609_164635`
- Active `/home/syhlabtop/k4_logs/diagnostic_results.csv` was restored to keep
  only valid diagnostic rows. It currently contains D02 only.

Decision:

- D04 is not evaluated yet. There are no D04 motion metrics and no operator
  task observation.
- The immediate blocker is hardware connection reliability on left `joint_1`,
  despite `can0` reporting link `UP`.
- Retry D04 only after the left-arm `joint_1` power/CAN response is stable.
