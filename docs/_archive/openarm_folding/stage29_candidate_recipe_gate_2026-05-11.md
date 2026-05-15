# Stage 29 Candidate Recipe Gate

## Decision

Only candidates with `deploy_candidate=true` may advance to Stage 31 dataset replay.
A gate failure excludes the checkpoint from robot deployment.

## Candidates

- `lerobot/folding_latest`: FAIL; deploy_candidate=`false`; failed_checks=`postprocessor_action_stats_are_relative_for_arm_joints`
- `lerobot-data-collection/folding_final10`: FAIL; deploy_candidate=`false`; failed_checks=`postprocessor_action_stats_are_relative_for_arm_joints`
- `lerobot-data-collection/folding_final`: FAIL; deploy_candidate=`false`; failed_checks=`model_training_dataset_matches_replay_dataset, postprocessor_action_stats_are_relative_for_arm_joints`
- `lerobot-data-collection/ablation2-5_0`: FAIL; deploy_candidate=`false`; failed_checks=`model_training_dataset_matches_replay_dataset, postprocessor_action_stats_are_relative_for_arm_joints`

## Safety

- This script downloads/reads only lightweight model metadata and processor stats.
- It does not load policy weights, videos, snapshots, robot connections, torque, or action sends.
