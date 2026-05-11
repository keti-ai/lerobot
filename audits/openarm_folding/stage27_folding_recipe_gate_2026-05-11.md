# Stage 27 Folding Recipe Gate

## Decision

The replay path is now guarded by a folding recipe gate derived from the
`robot-folding` Space:

```text
https://huggingface.co/spaces/lerobot/robot-folding#hardware
```

The gate writes JSON/Markdown diagnostics and returns a non-zero exit code if
the model/dataset/processor recipe is not aligned. This prevents a dataset
replay from being misread as deployable when the folding recipe is broken.

Current `folding_latest` fails the gate. Robot motion remains blocked.

## Locked Recipe

The gate fixes the following recipe assumptions:

```text
robot: bimanual OpenArm / openarms_follower
hardware: +5 cm upper arm extension and larger gripper jaws expected for final deployment
state/action: 16D, right arm first then right gripper, left arm then left gripper
camera keys: observation.images.left_wrist, observation.images.right_wrist, observation.images.base
camera shapes: left/right wrist 720x1280x3, base 480x640x3
model: pi05
chunk_size: 30
n_action_steps: 30
action representation: relative trajectory
relative exclude: gripper only
training techniques recorded: SARM/RABC
inference deployment expectation: RTC execution horizon 20 and action interpolation multiplier 3
```

## Current Gate Result

The current checkpoint/dataset pair passes all structural checks:

```text
policy_type_pi05: PASS
model_training_dataset_matches_replay_dataset: PASS
dataset_robot_type_openarms_follower: PASS
action_names_match_folding_16d: PASS
state_names_match_folding_16d: PASS
camera_keys_and_shapes_match_space_recipe: PASS
use_relative_actions_enabled: PASS
relative_exclude_gripper_only: PASS
chunk_size_30: PASS
n_action_steps_30: PASS
rabc_recorded_in_train_config: PASS
```

It fails the critical relative-action stats check:

```text
postprocessor_action_stats_are_relative_for_arm_joints: FAIL
max_post_vs_relative_q01_error_deg: 69.973
max_post_vs_relative_q99_error_deg: 110.695
max_arm_span_ratio_postprocessor_over_sampled_relative: 14.230
worst_span_ratio_key: left_joint_1.pos
```

Dataset replay under the gate still shows unsafe deltas:

```text
frame 0 model mean_abs_delta=26.748 deg
frame 0 max_abs_delta=71.918 deg at right_joint_4.pos
frame 0 recorded mean_abs_delta=1.300 deg
```

## Implementation

`audits/openarm_folding/stage22_dataset_replay_and_ablation.py` now performs
the recipe gate by default. It can be bypassed only with `--no-recipe-gate` for
forensics.

Important command shape:

```bash
HF_HOME=/mnt/nas/huggingface \
HF_HUB_CACHE=/mnt/nas/huggingface/hub \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
python audits/openarm_folding/stage22_dataset_replay_and_ablation.py \
  --dataset-repo lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --dataset-root /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/datasets/level2_final_quality3_t_0_hil_data_c \
  --model-dir /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest \
  --frames 0 \
  --video-backend ffmpeg \
  --json-out /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage27_recipe_gate_current_folding_latest_2026-05-11.json \
  --md-out /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage27_recipe_gate_current_folding_latest_2026-05-11.md
```

Expected status for the current checkpoint is exit code `2`.

## Acceptance Criteria For Resuming Robot Work

1. Gate status must be `PASS`.
2. Dataset replay on the model-card training dataset must produce model deltas
   near recorded deltas.
3. Raw normalized output must match normalized recorded relative target.
4. Only then can syhlabtop no-send snapshot review resume.
5. Actuator write remains disallowed until no-send snapshot review also passes.
