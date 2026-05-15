# OpenArm Folding Audit Index

Date: 2026-05-14
Branch: `audit/openarm-folding-baseline`
Scope: syhlabtop/A6000 OpenArm folding deployment audit, corrected checkpoint rollout preparation, and `full_folding` retrain tracking.

## Current Status

```text
Track B A6000 full_folding retrain: READY_FOR_D8A_LAUNCH — torch 2.7/pyav config prepared
Track A syhlabtop level2 live rollout: UNBLOCKED — proceed with level2 model
Track C A6000 checkpoint_selection: COMPLETE — 002000/003000/004000 all replay FAIL, no deploy candidate
Track D syhlabtop axis/camera work: IN_PROGRESS — this is the parallel work
new_stage_numbers: forbidden
next_experiment_axis: rollout_trial_<timestamp>/
robot_motion_from_this_readme: NOT_AUTHORIZED
```

- Track B `full_folding` initial training finished at step 004000 (loss ~0.066). Recipe gate PASS. Dataset replay gate **FAIL**: model delta/recorded-delta ratio 0.128–0.282 (threshold 0.25–4.0), raw normalized error max 0.413 (threshold 0.25). No 60–70 deg abnormal deltas (max 2.086 deg). `full_folding 004000` is NOT a syhlabtop deploy candidate.
- D-9 decision is option (i): torch 2.7.x + compatible cuDNN new venv. Smoke PASS with torch `2.7.1+cu126`, cuDNN `90501`, and `dataset.video_backend=pyav`. Torchcodec backend still fails in the LeRobot file-like decoder path. D-8a 003000 continuation config/command is prepared under the A6000 audits directory. The parallel work refers to syhlabtop Track D1/D3.
- Track A is now unblocked. Use the current level2 corrected checkpoint (step 004000) on port 8766. Focus on base-view alignment and axis direction check before running a full session rollout.
- Track C (A6000): checkpoint comparison is complete. `full_folding` checkpoints 002000, 003000, and 004000 all fail replay gate, so checkpoint selection alone does not produce a deploy candidate.
- Any motion must use a fresh `rollout_trial_<timestamp>/` session, a fresh serving health check, a new approval envelope, and explicit operator approval.

## Major Timeline Summary

- **Stage 0-11:** Built the original two-machine no-send pipeline. A6000 loaded/probed policy assets; syhlabtop mapped cameras, CAN/state order, captured a no-send observation bundle, and received an A6000 action review.
- **Stage 12-19:** Performed gripper-zero adjustment, refreshed snapshots, built guarded first-motion dry-run/runtime-preflight/execution-packet tooling. First write was blocked by stale packet handling before actuator motion.
- **Stage 20-27:** Tested high-overview camera, diagnosed action contract, replayed dataset frames, added ablations, and built the recipe gate. Main finding: public `folding_latest` was structurally close but failed relative-action postprocessor stats.
- **Stage 28-31:** Wrote recovery runbook, searched public candidates, computed relative-action reference stats, retrained/exported the corrected level2 checkpoint, and passed corrected recipe gate plus dataset replay.
- **Stage 32-35:** Ran syhlabtop fresh snapshot/A6000 no-send review, generated a fresh guarded dry-run table, validated packet/no-execute paths, and completed the first explicitly approved guarded right-arm single write.
- **Stage 36-40:** Built the A6000 served-proposal bridge and completed repeated right-arm served-proposal single writes. All Stage35-40 packets are consumed historical artifacts and must not be reused.
- **Rollout trial work:** Shifted from one-shot target tables to live closed-loop chunk serving. A full-16 bimanual+gripper live harness exists, uses direct Damiao guarded MIT batch writes, and records saturation/readback/cleanup stats.
- **Current split:** Track B is active on A6000. Track A live rollout waits until Track B completes and A6000 serving is re-established.

## Major Findings So Far

- Public `lerobot/folding_latest` and related public folding candidates used `use_relative_actions=true` but stored action postprocessor stats that matched absolute action stats. They are not deployable without correction.
- The mismatch reproduced even on the model-card training dataset: recorded deltas were around 1 degree while public model outputs were tens of degrees.
- Corrected level2 relstats retraining fixed the primary contract gap. Stage31 replay passed: model deltas were the same order as recorded deltas, and the 60-70 degree abnormal deltas disappeared.
- Runtime action targets from the corrected A6000 server are absolute joint targets after postprocessing. Relative actions remain a training/processor detail.
- The current LeRobot checkpoint contract is right-first 16D, degrees, `left_wrist`/`right_wrist`/`base`, action chunk `[1, 30, 16]`. Do not mix it with the OpenPI left-first contract unless the checkpoint is changed too.
- Actual robot motion does not use `send_action`, `lerobot-rollout`, or `OpenArmFollower.connect`. The audited path is `DamiaoMotorsBus.connect(handshake=False)` plus guarded MIT batch commands.
- Persistent Damiao motor setting changes are not the current fix. Remaining hardware issues should be treated as axis, zero, runtime-limit, gripper-range, and folding hardware-contract alignment problems.
- `full_folding` is schema-compatible and has `sarm_progress.parquet`, so it is a valid Track B relstats + RABC retrain candidate.
- The largest current real-world gap is likely visual/hardware alignment: base camera FOV/scale, folding hardware extensions/jaws, joint4/gripper limit behavior, and suspicious axis conventions.

## Current Read Order

1. `README.md`
2. `trackA_level2_live_test_plan_2026-05-14.md`
3. `visual_dataset_alignment_and_full_folding_retrain_plan_2026-05-14.md`
4. `openpi_lerobot_live_pipeline_check_2026-05-14.md`
5. `damiao_setup_axis_alignment_review_2026-05-14.md`
6. `stage31_a6000_retrain_status_and_next_plan_2026-05-12.md`
7. `timeline_status_2026-05-11.md`
8. Historical single-write docs as needed: Stage35 through Stage40 result files.

## Track B: A6000 — COMPLETE (replay gate FAIL)

`full_folding` step-004000 training is done. Results:

```text
relstats recompute:  PASS
recipe gate:         PASS
dataset replay gate: FAIL  ← NOT deploy candidate

checkpoint: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/
            train/pi05_openarm_full_folding_relstats_chunk30_20260514/
            checkpoints/004000/pretrained_model

audit root: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/
            full_folding_parallel_20260514/audits/

key artifacts:
  full_folding_train_result_20260514.md
  full_folding_recipe_gate_20260514.md/json
  full_folding_dataset_replay_20260514.md/json     ← FAIL detail here
  full_folding_visual_refs_manifest_20260514.json
  d8a_full_folding_continue_003000_torch27_pyav_config_20260515.json
  d8a_full_folding_continue_003000_torch27_pyav_command_20260515.md
  /data/.../audits/d9_torch27_train_smoke_20260515.md/json
  visual_refs/   (left_wrist, right_wrist, base samples)
```

Replay gate failure detail:
- Model delta / recorded-delta ratio: 0.128–0.282 (threshold 0.25–4.0)
- Raw normalized error max: 0.413 (threshold 0.25)
- No 60–70 deg abnormal deltas: max 2.086 deg
- Conclusion: model outputs are systematically smaller than training targets — likely underfit

Task distribution in `full_folding`:
- `Fold the T-shirt properly`: 4100 eps
- `Layout the t-shirt...then fold properly`: 1561 eps
- `Fold`: 27 eps

## Track C: A6000 — Checkpoint Selection (NEEDED)

Compare `full_folding` checkpoints 002000 and 003000 on dataset replay gate to determine if
004000 is underfit or if an earlier checkpoint is better calibrated.

Sequence:
1. Run `stage22_dataset_replay_and_ablation.py` on checkpoint 002000.
2. Run same on checkpoint 003000.
3. Compare delta/ratio statistics across 002000 / 003000 / 004000.
4. If an earlier checkpoint passes replay gate → it becomes the Track B deploy candidate.
5. If none pass → consider task-filtered training (fold-only 4100 eps) or training from level2 candidate.

## Track A: syhlabtop Work After Track B

Track A live rollout is deferred until Track B finishes or A6000 serving is explicitly available again.

When resumed:

1. Re-check A6000 server health and checkpoint metadata.
2. Use a level2-like messy centered shirt scene for the current level2 checkpoint, or use the selected Track B checkpoint if it has passed gates.
3. Capture pre-run live camera evidence with the viewer.
4. Generate a fresh `rollout_trial_<timestamp>/` approval envelope.
5. Execute only after exact operator approval.
6. Capture post-run evidence and inspect:
   - `actions_executed`
   - `chunks_accepted`
   - `gripper_saturated_features`
   - `joint4_saturated_features`
   - `joint_limit_saturated_features`
   - `cleanup_errors`
   - `remaining_torque_enabled_motors`
   - `torque_disable_complete`

Use:

```text
trackA_level2_live_test_plan_2026-05-14.md
```

as the command source when Track A is re-enabled.

## Current Live Vision Viewer

Use this read-only viewer to compare real syhlabtop policy inputs against dataset reference views. It opens the three RealSense color streams used by the policy and does not touch robot/CAN/torque/action paths.

Source:

```text
syhlabtop_live_policy_input_viewer.py
```

Start:

```bash
cd /home/syhlabtop/workspace/lerobot

bash audits/openarm_folding/run_rsusb_py312.sh \
  audits/openarm_folding/syhlabtop_live_policy_input_viewer.py \
  --host 0.0.0.0 \
  --port 8091 \
  --left-wrist-serial 315122270766 \
  --right-wrist-serial 230322273311 \
  --base-serial 213622075840 \
  --wrist-width 640 \
  --wrist-height 480 \
  --base-width 640 \
  --base-height 480 \
  --camera-fps 30 \
  --display-fps 5 \
  --output-dir /tmp/openarm_folding_policy_input_viewer
```

Open:

```text
http://127.0.0.1:8091/
http://10.252.216.81:8091/
http://192.168.1.58:8091/
```

Viewer routes:

```text
/             live 3-camera page
/mosaic.jpg   current 3-view mosaic
/status.json  camera status JSON
/capture      save left_wrist/right_wrist/base/mosaic/metadata under output-dir
```

Capture output:

```text
/tmp/openarm_folding_policy_input_viewer/policy_input_view_<timestamp>/
  left_wrist.jpg
  right_wrist.jpg
  base.jpg
  mosaic.jpg
  metadata.json
```

Stop:

```bash
# If running in the foreground:
Ctrl-C

# If left running in another shell:
pkill -f syhlabtop_live_policy_input_viewer.py
```

Check whether it is running:

```bash
ps -ef | rg 'syhlabtop_live_policy_input_viewer|8091' | rg -v rg
```

If port `8091` is busy:

```bash
ss -ltnp | rg ':8091'
```

Then stop the stale viewer with the PID shown by `ss`, or restart on another port with `--port 8092`.

## Storage Policy

Keep source-controlled docs and scripts in this directory.

Keep large runtime assets out of the repo:

```text
/home/syhlabtop/openarm_folding_20260512
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```

The `/data/...` path is A6000-local persistent storage. Do not assume syhlabtop can write to it directly.

Use `/tmp` only for scratch viewer output. Preserve important captures under `/home/syhlabtop/openarm_folding_20260512` or transfer them to the A6000/NAS workflow.

Known syhlabtop repo path:

```text
/home/syhlabtop/workspace/lerobot
```

For syhlabtop RealSense capture scripts, use the checked-in wrapper so the RSUSB `pyrealsense2` path is not lost by nested shell quoting:

```bash
bash audits/openarm_folding/run_rsusb_py312.sh audits/openarm_folding/<script>.py ...
```

## Historical A6000 Setup

The original A6000 setup verified `lerobot/folding_latest` asset loading and synthetic no-robot probes. That path is historical because the public artifact failed the relative-stats gate.

Useful historical environment:

```bash
cd /home/syh/workspace/lerobot

export HF_HOME=/mnt/nas/huggingface
export HF_HUB_CACHE=/mnt/nas/huggingface/hub
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

BASE=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```

Current serving must be checked from the active Track B or selected corrected checkpoint after A6000 training finishes.

## Remaining Work

- Wait for Track B A6000 training/gate/replay outputs.
- Capture or preserve syhlabtop visual references if needed while Track B runs.
- After Track B, re-check A6000 serving health and selected checkpoint metadata.
- Decide whether Track A uses the current corrected level2 checkpoint or the new Track B `full_folding` candidate.
- Run Track A only through a fresh `rollout_trial_<timestamp>/` envelope and explicit operator approval.
- If Track A behavior remains poor, prioritize base camera/FOV alignment and suspicious axis/limit checks before changing Damiao persistent settings.
