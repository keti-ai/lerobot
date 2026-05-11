# Stage 22 Dataset Replay And Stage 23 Ablation

## Recipe Gate

- Status: `FAIL`
- Source: https://huggingface.co/spaces/lerobot/robot-folding#hardware
- Failed checks: `postprocessor_action_stats_are_relative_for_arm_joints`
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
- `postprocessor_action_stats_are_relative_for_arm_joints`: FAIL

## Decision Inputs

- Dataset: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c` episode `0`
- Model: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest`
- Video backend: `ffmpeg`
- Robot type: `openarms_follower`
- Snapshot: `not provided`

## Dataset Replay

- frame `0`: model mean_abs_delta=26.748, max_abs_delta=71.918 at `right_joint_4.pos`; recorded mean_abs_delta=1.300, model-vs-recorded max_error=75.387 at `right_joint_4.pos`

## Safety

- No robot connection, motor initialization, torque enable, zeroing, or action send is performed by this script.
- This is an offline A6000 policy/input contract probe only.
