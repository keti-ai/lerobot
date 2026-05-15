# syhlabtop Experiment-Ready Handoff Prompt

Date: 2026-05-12

## Superseded

This prompt is superseded for the baseline two-machine plan.

Do not use this prompt to transfer `model.safetensors` to syhlabtop or run the
PI0.5 model locally on syhlabtop. The baseline plan is:

- syhlabtop owns read-only robot/camera snapshot capture.
- A6000 owns model weights and inference/review.
- syhlabtop sends a no-send snapshot bundle to A6000.

Use:

`audits/openarm_folding/syhlabtop_a6000_served_snapshot_handoff_prompt_2026-05-12.md`

Copy this whole prompt to the syhlabtop agent.

---

You are the syhlabtop agent preparing the real OpenArm PC for the next
experiment-ready no-send/shadow stage.

This is not a robot motion task. Your job is to get the syhlabtop environment
ready, verify the transferred A6000 candidate, inspect read-only hardware and
camera mapping, and produce a no-send snapshot report. Do not move the robot.

## Current Situation

The A6000 offline retraining for OpenArm folding is complete.

A6000 repo branch:

`audit/openarm-folding-baseline`

Minimum required repo commit:

`50078e4dff69e66acd12864b3990d954f24d6288`

The actual latest commit may be newer if this handoff prompt has been committed
after `50078e4d`. The syhlabtop repo is acceptable if it contains this file and
includes commit `50078e4d` in its history.

A6000 final checkpoint source:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`

A6000 transfer packet:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/transfer_packet.md`

A6000 gate status:

- Full retraining completed: PASS, exit `0`.
- Corrected Stage 29 metadata gate: PASS.
- Stage 31 dataset replay acceptance: PASS.
- No 60-70 degree abnormal delta in checked dataset replay frames.

The A6000 result does not authorize real robot motion. It only authorizes
transfer, checksum verification, read-only preflight, and no-send/shadow
inference.

## Hard Safety Stops

Do not run:

- `lerobot-rollout`
- `lerobot-record`
- `lerobot-replay`
- real robot rollout
- dataset replay to robot
- `robot.send_action()`
- `OpenArmFollower.connect()` followed by any write/send path
- torque enable for motion
- zeroing
- actuator write
- CAN write
- calibration write
- any command that can physically move the robot

Do not download a new `model.safetensors`.

Do not download full datasets.

If a command might move the robot, stop and ask the human operator for explicit
approval with:

- exact command
- expected physical effect
- affected joints
- safety preconditions

## Local Paths On syhlabtop

LeRobot repo:

`/home/syhlabtop/workspace/lerobot`

Work root:

`/home/syhlabtop/openarm_folding_20260512`

Expected transferred model target:

`/home/syhlabtop/openarm_folding_20260512/models/pi05_openarm_relstats_full_004000/pretrained_model`

Expected manifest directory:

`/home/syhlabtop/openarm_folding_20260512/manifests`

Expected audit output directories:

- `/home/syhlabtop/openarm_folding_20260512/audits`
- `/home/syhlabtop/openarm_folding_20260512/camera_maps`
- `/home/syhlabtop/openarm_folding_20260512/hardware/openarm`
- `/home/syhlabtop/openarm_folding_20260512/shadow_snapshots`
- `/home/syhlabtop/openarm_folding_20260512/shadow_reviews`
- `/home/syhlabtop/openarm_folding_20260512/safety_configs`

NAS may not be mounted on syhlabtop. Do not depend on NAS paths.

## Step 1: Sync Repo

Run:

```bash
cd /home/syhlabtop/workspace/lerobot
git status --short
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
```

Expected:

```text
HEAD includes 50078e4dff69e66acd12864b3990d954f24d6288
audits/openarm_folding/syhlabtop_experiment_ready_handoff_prompt_2026-05-12.md exists
```

If the worktree has local changes, report them. Do not revert anything unless
the human explicitly asks.

Read these files:

- `audits/openarm_folding/timeline_status_2026-05-11.md`
- `audits/openarm_folding/stage31_a6000_retrain_status_and_next_plan_2026-05-12.md`
- `audits/openarm_folding/syhlabtop_stage32_no_send_agent_prompt_2026-05-12.md`
- `audits/openarm_folding/two_machine_pipeline_2026-05-11.md`

## Step 2: Create Work Root

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

## Step 3: Confirm Candidate Transfer

Check whether the transferred candidate exists:

```bash
WORK=/home/syhlabtop/openarm_folding_20260512
MODEL="$WORK/models/pi05_openarm_relstats_full_004000/pretrained_model"
ls -lh "$MODEL"
ls -lh "$WORK/manifests"
```

Required files under `$MODEL`:

- `config.json`
- `train_config.json`
- `policy_preprocessor.json`
- `policy_postprocessor.json`
- `policy_preprocessor_step_3_normalizer_processor.safetensors`
- `policy_postprocessor_step_0_unnormalizer_processor.safetensors`
- `model.safetensors`

Required files under `$WORK/manifests`:

- `pretrained_model.sha256`
- `audit_artifacts.sha256`
- `transfer_packet.md`

If these files are missing, stop and ask the A6000 operator to transfer the
candidate using the A6000 transfer packet. Do not download replacement model
weights.

## Step 4: Verify Checksum

Run:

```bash
WORK=/home/syhlabtop/openarm_folding_20260512
MODEL="$WORK/models/pi05_openarm_relstats_full_004000/pretrained_model"
cd "$MODEL"
sha256sum -c "$WORK/manifests/pretrained_model.sha256"
```

All entries must pass.

Write result:

`$WORK/audits/stage32_candidate_checksum_2026-05-12.md`

If any checksum fails, stop. Do not load the model.

## Step 5: Metadata-Only Candidate Check

Inspect only small config files first:

```bash
WORK=/home/syhlabtop/openarm_folding_20260512
MODEL="$WORK/models/pi05_openarm_relstats_full_004000/pretrained_model"
python - <<'PY'
import json
from pathlib import Path

model = Path("/home/syhlabtop/openarm_folding_20260512/models/pi05_openarm_relstats_full_004000/pretrained_model")
for name in ["config.json", "train_config.json", "policy_preprocessor.json", "policy_postprocessor.json"]:
    print(f"\n===== {name} =====")
    data = json.loads((model / name).read_text())
    for key in [
        "type",
        "use_relative_actions",
        "relative_exclude_joints",
        "chunk_size",
        "n_action_steps",
    ]:
        if key in data:
            print(f"{key}: {data[key]}")
    if name == "train_config.json":
        print("dataset:", data.get("dataset"))
        print("sample_weighting:", data.get("sample_weighting"))
PY
```

Expected:

- policy type: `pi05`
- `use_relative_actions=true`
- `relative_exclude_joints=["gripper"]`
- `chunk_size=30`
- `n_action_steps=30`
- dataset repo:
  `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`
- `sample_weighting.type=rabc`
- `sample_weighting.kappa=0.0265`

Write:

`$WORK/audits/stage32_metadata_candidate_check_2026-05-12.md`

## Step 6: Read-Only Hardware And Camera Preflight

This step touches real hardware interfaces but must remain read-only.

Allowed:

- list camera devices
- list USB devices
- inspect camera serial/path mapping
- capture camera frame shape if the capture path is read-only
- read robot state only if the local operator confirms the read path does not
  torque-enable or command motion

Still forbidden:

- torque enable
- zeroing
- calibration write
- actuator write
- `send_action`
- any motion

Capture:

- camera device paths
- mapping to left wrist, right wrist, base
- observed frame shapes
- read-only robot state availability
- current 16D state vector if safely available

Expected state/action order:

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

Expected camera keys:

- `observation.images.left_wrist`
- `observation.images.right_wrist`
- `observation.images.base`

Write:

`$WORK/audits/stage32_readonly_hardware_preflight_2026-05-12.md`

## Step 7: No-Send Policy Snapshot

Only run this after checksum, metadata, camera mapping, and read-only state
checks pass.

Goal:

- load transferred policy locally
- build one current observation
- run preprocessing and policy forward path
- compute predicted action summary
- do not send anything to robot

Compute:

- predicted absolute action
- current state
- arm deltas: `predicted_abs_action - current_state`
- max absolute arm delta
- per-joint deltas
- gripper predicted absolute values

Acceptance for no-send snapshot:

- state vector order matches the 16D trained order exactly
- camera mapping is not swapped
- no arm joint has a 60-70 degree abnormal delta
- `right_joint_4.pos`, `left_joint_4.pos`, and `right_joint_7.pos` are
  explicitly reported
- grippers are treated as absolute/excluded from relative conversion

Write:

- `$WORK/shadow_snapshots/stage32_no_send_snapshot_2026-05-12.json`
- `$WORK/shadow_reviews/stage32_no_send_shadow_review_2026-05-12.md`

## Step 8: Final Report Back

Report in this format:

```text
repo_head:
candidate_checksum: PASS/FAIL
metadata_candidate_check: PASS/FAIL
camera_mapping:
state_order_check: PASS/FAIL
no_send_snapshot: PASS/FAIL/NOT_RUN
max_arm_delta_deg:
right_joint_4_delta_deg:
left_joint_4_delta_deg:
right_joint_7_delta_deg:
motion_status: BLOCKED
next_blocker:
artifact_paths:
```

The only acceptable `motion_status` is `BLOCKED`.

## Stop Condition

Stop immediately if:

- checksum fails
- metadata does not match the A6000 recipe
- camera mapping is ambiguous
- state order is ambiguous
- read-only robot state access appears to torque-enable or write to hardware
- no-send output contains a large abnormal arm delta

Do not proceed to guarded first motion. That is a separate stage requiring
explicit human approval after shadow review.
