# Stage 22 Dataset Replay And Stage 23 Ablation

## Decision Inputs

- Dataset: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c` episode `0`
- Model: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest`
- Video backend: `ffmpeg`
- Robot type: `openarms_follower`
- Snapshot: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260511_175613`

## Dataset Replay

- frame `0`: model mean_abs_delta=25.588, max_abs_delta=67.027 at `right_joint_4.pos`; recorded mean_abs_delta=1.300, model-vs-recorded max_error=70.496 at `right_joint_4.pos`
- frame `1`: model mean_abs_delta=24.644, max_abs_delta=65.440 at `right_joint_4.pos`; recorded mean_abs_delta=1.156, model-vs-recorded max_error=68.456 at `right_joint_4.pos`
- frame `10`: model mean_abs_delta=26.065, max_abs_delta=69.074 at `right_joint_4.pos`; recorded mean_abs_delta=1.424, model-vs-recorded max_error=72.919 at `right_joint_4.pos`
- frame `30`: model mean_abs_delta=27.654, max_abs_delta=73.030 at `right_joint_4.pos`; recorded mean_abs_delta=1.325, model-vs-recorded max_error=77.097 at `right_joint_4.pos`

## State / Visual Ablation

- `dataset_images__dataset_state`: mean_abs_delta=25.591, max_abs_delta=70.958 at `right_joint_4.pos`
- `dataset_images__snapshot_state`: mean_abs_delta=27.524, max_abs_delta=74.644 at `right_joint_4.pos`
- `snapshot_images__dataset_state`: mean_abs_delta=25.939, max_abs_delta=71.434 at `right_joint_4.pos`
- `snapshot_images__snapshot_state`: mean_abs_delta=26.328, max_abs_delta=69.975 at `right_joint_4.pos`

## Safety

- No robot connection, motor initialization, torque enable, zeroing, or action send is performed by this script.
- This is an offline A6000 policy/input contract probe only.
