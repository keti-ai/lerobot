# Stage 30 Relative Recipe Reference

## Decision

This file is a training/export reference only. It is not a deployable checkpoint mutation.
A corrected checkpoint still must pass Stage 29 recipe gate and Stage 31 dataset replay.

## Dataset

- Dataset: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`
- Rows sampled: `3414338`
- Robot type: `openarms_follower`

## Relative Action Summary

- Arm mean abs delta: `1.722` deg
- Arm p99 abs delta: `19.789` deg
- Arm max abs delta: `116.352` deg at `left_joint_4.pos`

## Required Alignment

- `policy.use_relative_actions=true`
- `policy.relative_exclude_joints=["gripper"]`
- postprocessor action stats must match `relative_action_stats`, not `absolute_action_stats`
- processor-only stat swapping remains blocked for deployment; retrain or re-export from the corrected recipe

## Safety

- No model weights, videos, robot connection, torque, zeroing, or action send were used.
