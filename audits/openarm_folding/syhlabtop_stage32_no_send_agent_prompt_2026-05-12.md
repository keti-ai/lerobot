# syhlabtop Stage 32 No-Send Agent Prompt

Date: 2026-05-12

Use this prompt on the real robot PC only after the A6000 final candidate has
been transferred to syhlabtop.

## Role

You are the syhlabtop agent for LeRobot OpenArm folding Stage 32 readiness.
Your task is no-send/shadow readiness only. You must not move the robot.

## Current A6000 Result

A6000 retraining completed successfully.

Final candidate:

`/home/syhlabtop/openarm_folding_20260512/models/pi05_openarm_relstats_full_004000/pretrained_model`

A6000 source checkpoint:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`

Gate status:

- Corrected Stage 29 metadata gate: PASS.
- Stage 31 dataset replay acceptance: PASS.
- No 60-70 degree abnormal deltas were observed in the A6000 dataset replay.

Reference docs to read first:

- `audits/openarm_folding/stage31_a6000_retrain_status_and_next_plan_2026-05-12.md`
- `audits/openarm_folding/syhlabtop_work_prompt_2026-05-11.md`
- `audits/openarm_folding/syhlabtop_stage_guides_2026-05-11.md`
- `audits/openarm_folding/two_machine_pipeline_2026-05-11.md`

## Hard Stops

Do not run:

- `lerobot-rollout`
- `lerobot-record`
- `lerobot-replay`
- any full policy rollout against the robot
- `robot.send_action()`
- torque enable for motion
- zeroing
- actuator write
- CAN write
- any command whose purpose is robot movement

Do not download a new model or full dataset on syhlabtop. Use only the
transferred candidate from A6000.

If a command might move the robot, stop and ask for explicit human approval
with the exact command and expected physical effect.

## Work Root

Use:

`/home/syhlabtop/openarm_folding_20260512`

Expected layout:

- `models/pi05_openarm_relstats_full_004000/pretrained_model/`
- `manifests/pretrained_model.sha256`
- `manifests/audit_artifacts.sha256`
- `audits/`
- `camera_maps/`
- `hardware/openarm/`
- `shadow_snapshots/`
- `shadow_reviews/`
- `safety_configs/`

## Step 1: Repo Context

Run:

```bash
cd /home/syhlabtop/workspace/lerobot
git status --short
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
```

Expected: HEAD is at least `e87db2f8a418e312b30186e633bb4a592d40b06f`.

If the worktree has unrelated local changes, do not revert them. Report them.

## Step 2: Create Local Work Root

Run:

```bash
WORK=/home/syhlabtop/openarm_folding_20260512
mkdir -p \
  "$WORK/audits" \
  "$WORK/camera_maps" \
  "$WORK/hardware/openarm" \
  "$WORK/calibration" \
  "$WORK/shadow_snapshots" \
  "$WORK/shadow_reviews" \
  "$WORK/safety_configs" \
  "$WORK/models/pi05_openarm_relstats_full_004000/pretrained_model" \
  "$WORK/manifests"
```

## Step 3: Verify Transferred Candidate

After A6000 transfer is complete, run:

```bash
WORK=/home/syhlabtop/openarm_folding_20260512
cd "$WORK/models/pi05_openarm_relstats_full_004000/pretrained_model"
sha256sum -c "$WORK/manifests/pretrained_model.sha256"
```

All entries must pass before any model loading or no-send inference.

## Step 4: Metadata-Only Candidate Check

Read these files from the transferred candidate:

- `config.json`
- `train_config.json`
- `policy_preprocessor.json`
- `policy_postprocessor.json`

Confirm:

- policy type is `pi05`
- `use_relative_actions=true`
- `relative_exclude_joints=["gripper"]`
- `chunk_size=30`
- `n_action_steps=30`
- dataset repo is
  `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`
- `sample_weighting.type=rabc`
- `sample_weighting.kappa=0.0265`

Write:

`$WORK/audits/stage32_metadata_candidate_check_2026-05-12.md`

## Step 5: Read-Only Robot/Cameras Preflight

This step is allowed only as read-only inspection. It still requires local
human awareness because it touches hardware interfaces.

Capture and report:

- current USB/video device mapping
- camera serial/path mapping
- OpenArm interface availability
- current state vector order and values, if read-only state access is safe
- camera frame shapes

Do not command torque, zeroing, calibration write, or any actuator movement.

Write:

`$WORK/audits/stage32_readonly_hardware_preflight_2026-05-12.md`

## Step 6: No-Send Policy Snapshot

Only after Steps 1-5 pass:

- Build a single observation from the current read-only state and camera frames.
- Run local policy preprocessing and forward inference if the environment can
  load the transferred candidate.
- Compute predicted arm deltas as `predicted_abs_action - current_state`.
- Do not call any send/write method.

Acceptance:

- state/action order exactly matches the 16-dim trained order
- camera mapping is left wrist, right wrist, base
- no 60-70 degree abnormal predicted arm delta
- grippers are interpreted as absolute/excluded from relative conversion

Write:

- `$WORK/shadow_snapshots/stage32_no_send_snapshot_2026-05-12.json`
- `$WORK/shadow_reviews/stage32_no_send_shadow_review_2026-05-12.md`

## Report Format

Report:

1. repo HEAD
2. candidate checksum result
3. metadata candidate check result
4. read-only hardware/camera mapping result
5. no-send action delta summary
6. whether motion remains blocked
7. exact next blocker before guarded first actuator write

Motion remains blocked unless a human separately approves a guarded first
actuator write command.
