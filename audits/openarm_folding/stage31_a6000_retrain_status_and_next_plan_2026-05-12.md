# Stage 31 A6000 Retrain Status And Next Plan

Date: 2026-05-12

Branch: `audit/openarm-folding-baseline`

Repo HEAD: `e87db2f8a418e312b30186e633bb4a592d40b06f`

## Scope

This status records the A6000 offline retraining result for the OpenArm
folding PI0.5 baseline. No robot hardware was accessed. No rollout, record,
replay-to-robot, motor initialization, torque enable, zeroing, or
`robot.send_action()` was run.

Robot motion remains blocked until the syhlabtop no-send/shadow checks are
completed and explicitly approved.

## Final Candidate

Final checkpoint:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`

Training log:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/train_full_nocompile_bsz4_20260512_104831.log`

Training outcome:

- Command exited with status `0`.
- Final step: `4000/4000`.
- Final logged loss: `0.066`.
- Final logged grad norm: `0.443`.
- Final learning rate: `2.5e-06`.
- GPU state after training: all 4x RTX A6000 returned to idle.

## Dataset And Recipe

Original dataset root:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/datasets/level2_final_quality3_t_0_hil_data_c`

Relative-stats dataset root:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/datasets/level2_final_quality3_t_0_hil_data_c_relative_stats_chunk30`

Recipe locked for the candidate:

- Policy: `pi05`
- Robot type: `openarms_follower`
- Action/state dim: `16`
- State/action order:
  `right_joint_1.pos`, `right_joint_2.pos`, `right_joint_3.pos`,
  `right_joint_4.pos`, `right_joint_5.pos`, `right_joint_6.pos`,
  `right_joint_7.pos`, `right_gripper.pos`, `left_joint_1.pos`,
  `left_joint_2.pos`, `left_joint_3.pos`, `left_joint_4.pos`,
  `left_joint_5.pos`, `left_joint_6.pos`, `left_joint_7.pos`,
  `left_gripper.pos`
- Units: joint positions in degrees; gripper positions use the dataset/policy
  gripper position units and are excluded from relative arm conversion.
- Cameras:
  - `observation.images.left_wrist`: `[720, 1280, 3]`
  - `observation.images.right_wrist`: `[720, 1280, 3]`
  - `observation.images.base`: `[480, 640, 3]`
- Action representation: relative arm trajectory, grippers excluded.
- `chunk_size=30`
- `n_action_steps=30`
- RABC enabled through `sample_weighting`.

## Gate Results

Corrected Stage 29 metadata gate: PASS

Artifacts:

- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage29_full_nocompile_bsz4_corrected_relstats_gate_2026-05-12.json`
- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage29_full_nocompile_bsz4_corrected_relstats_gate_2026-05-12.md`

Important checks:

- `policy_type_pi05`: PASS
- `model_training_dataset_matches_replay_dataset`: PASS
- `dataset_robot_type_openarms_follower`: PASS
- `action_names_match_folding_16d`: PASS
- `state_names_match_folding_16d`: PASS
- `camera_keys_and_shapes_match_space_recipe`: PASS
- `use_relative_actions_enabled`: PASS
- `relative_exclude_gripper_only`: PASS
- `chunk_size_30`: PASS
- `n_action_steps_30`: PASS
- `rabc_recorded_in_train_config`: PASS
- `postprocessor_action_stats_match_chunk30_relative_stats`: PASS

Stage 31 dataset replay acceptance gate: PASS

Artifacts:

- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage31_full_nocompile_bsz4_dataset_replay_2026-05-12.json`
- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage31_full_nocompile_bsz4_dataset_replay_2026-05-12.md`
- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage31_full_nocompile_bsz4_normalized_target_2026-05-12.json`
- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage31_full_nocompile_bsz4_acceptance_gate_2026-05-12.json`
- `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage31_full_nocompile_bsz4_acceptance_gate_2026-05-12.md`

Stage 31 summary:

- `corrected_stage29_recipe_gate_passed`: PASS
- `model_mean_abs_delta_same_order_as_recorded`: PASS
- `no_60_70deg_abnormal_delta_on_watched_or_global_joints`: PASS
- `raw_normalized_output_close_to_recorded_relative_arm_target`: PASS

Frame summary:

- Frame `0`: model mean `0.408 deg`, recorded mean `1.300 deg`,
  ratio `0.313`, model max `1.230 deg` at `left_joint_4.pos`,
  arm raw max error `0.108`.
- Frame `1`: model mean `0.631 deg`, recorded mean `1.156 deg`,
  ratio `0.546`, model max `3.089 deg` at `left_joint_4.pos`,
  arm raw max error `0.109`.
- Frame `10`: model mean `2.077 deg`, recorded mean `1.424 deg`,
  ratio `1.459`, model max `8.905 deg` at `right_joint_4.pos`,
  arm raw max error `0.110`.
- Frame `30`: model mean `1.236 deg`, recorded mean `1.325 deg`,
  ratio `0.933`, model max `5.800 deg` at `left_joint_4.pos`,
  arm raw max error `0.146`.

No 60-70 degree abnormal delta was observed on `right_joint_4.pos`,
`left_joint_4.pos`, `right_joint_7.pos`, or any global action dimension in
the checked frames.

## Tooling Note

The older Stage 29 and Stage 24 scripts in the audit bundle can produce stale
false negatives for this candidate because they check the older top-level RABC
fields and raw sampled `action - state` stats instead of the chunk-size-30
relative stats metadata used by the retraining recipe.

Use the corrected Stage 29 gate and the Stage 31 acceptance summary above for
this candidate.

## Next Work Plan

### 1. A6000: Package Candidate For Transfer

Owner: A6000 server.

Goal: prepare the final candidate and audit bundle for syhlabtop without
touching robot hardware.

Actions:

- Create a manifest for the final checkpoint directory. Completed:
  `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/`
- Record file sizes and checksums for `config.json`, `train_config.json`,
  `policy_preprocessor.json`, `policy_postprocessor.json`, processor
  safetensors, and `model.safetensors`. Completed:
  `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/pretrained_model.sha256`
- Record audit artifact checksums. Completed:
  `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/audit_artifacts.sha256`
- Use the transfer packet:
  `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/transfer_packet.md`
- Decide transfer route:
  - Preferred: direct `rsync`/`scp` from A6000 to syhlabtop.
  - Alternative: place the final checkpoint bundle on NAS if syhlabtop mounts
    NAS later.
- Transfer only the final `004000/pretrained_model` candidate and audit docs,
  not all intermediate checkpoints.

Do not train again unless Stage 31 is invalidated.

### 2. syhlabtop: Pull Repo And Sync Audit Context

Owner: syhlabtop.

Goal: make the real robot PC aware of the candidate and safety state.

Actions:

- Pull `audit/openarm-folding-baseline`.
- Confirm HEAD is at least `e87db2f8`.
- Read this file plus:
  - `audits/openarm_folding/syhlabtop_work_prompt_2026-05-11.md`
  - `audits/openarm_folding/syhlabtop_stage_guides_2026-05-11.md`
  - `audits/openarm_folding/two_machine_pipeline_2026-05-11.md`
- Create or reuse syhlabtop work root:
  `/home/syhlabtop/openarm_folding_20260512`
- Copy the final candidate into a local syhlabtop model path.
- Verify checksum manifest after transfer.

No robot command is needed for this stage.

### 3. syhlabtop: No-Send Snapshot Readiness

Owner: syhlabtop.

Goal: verify observation/state/camera compatibility without sending actions.

Allowed after explicit local approval:

- Read-only camera checks.
- Read-only robot state snapshot.
- Metadata and shape checks.
- No-send policy input preparation.

Still blocked:

- `robot.send_action()`
- torque enable as part of motion
- zeroing
- rollout
- record
- replay-to-robot
- any command that writes robot motion

Acceptance:

- State vector has exactly the 16 expected names and order.
- Units match the trained dataset convention.
- Camera keys map to:
  - left wrist
  - right wrist
  - base
- Camera shapes are compatible or explicitly transformed to the trained
  shapes.
- No-send action output has no 60-70 degree abnormal delta.
- Output is written as JSON/Markdown under the syhlabtop work root.

### 4. syhlabtop + A6000: Shadow Review

Owner: syhlabtop captures, A6000 can review offline.

Goal: compare syhlabtop no-send output against the A6000 Stage 31 replay
contract.

Actions:

- Move syhlabtop no-send snapshot JSON/images/state CSV to A6000 or shared
  storage.
- Run offline review only.
- Compare:
  - state order
  - camera mapping
  - predicted relative arm deltas
  - gripper absolute behavior
  - any outlier joints

Acceptance:

- No abnormal deltas.
- No camera key swap.
- No state/action order mismatch.
- Gripper behavior is understood as absolute/excluded from relative
  conversion.

### 5. First Motion Remains A Separate Gate

Owner: human operator plus syhlabtop.

First motion is not authorized by this A6000 result alone.

Before any guarded actuator write:

- Stage 29 corrected gate: PASS.
- Stage 31 dataset replay: PASS.
- syhlabtop no-send snapshot: PASS.
- shadow review: PASS.
- physical workspace and e-stop confirmed.
- explicit human approval for the exact first-write command.

The first write should be a separately scoped guarded actuator test, not a
full folding rollout.
