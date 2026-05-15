# Stage 22 Dataset Replay And Stage 23 Ablation

## Decision

The large first-step deltas are reproducible on actual `lerobot/full_folding`
dataset frames. This rules out the current syhlabtop camera placement, high
base-camera trial, and current robot state as the only cause.

For episode 0 frames `0,1,10,30`, the recorded dataset action deltas are small
(`0.465-0.674 deg` mean absolute delta), but the loaded `folding_latest` policy
produces `24.052-26.492 deg` mean absolute delta and `64.972-70.036 deg` max
delta, always dominated by `right_joint_4.pos`.

The ablation result is also not state- or vision-specific: dataset images with
dataset state, dataset images with syhlabtop state, syhlabtop images with
dataset state, and syhlabtop images with syhlabtop state all produce the same
large-delta class of output. The immediate blocker is therefore upstream of
hardware deployment: checkpoint/runtime/processor contract validation.

Motion remains blocked. Do not generate an actuator write packet from this
model output.

## Decision Inputs

- Dataset: `lerobot/full_folding` episode `0`
- Model: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest`
- Video backend: `ffmpeg`
- Robot type: `openarms_follower`
- Snapshot: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260511_175613`

## Dataset Replay

- frame `0`: model mean_abs_delta=25.055, max_abs_delta=64.972 at `right_joint_4.pos`; recorded mean_abs_delta=0.674, model-vs-recorded max_error=65.082 at `right_joint_4.pos`
- frame `1`: model mean_abs_delta=25.978, max_abs_delta=67.200 at `right_joint_4.pos`; recorded mean_abs_delta=0.465, model-vs-recorded max_error=67.309 at `right_joint_4.pos`
- frame `10`: model mean_abs_delta=26.492, max_abs_delta=70.036 at `right_joint_4.pos`; recorded mean_abs_delta=0.621, model-vs-recorded max_error=70.211 at `right_joint_4.pos`
- frame `30`: model mean_abs_delta=24.052, max_abs_delta=68.171 at `right_joint_4.pos`; recorded mean_abs_delta=0.472, model-vs-recorded max_error=69.479 at `right_joint_4.pos`

## State / Visual Ablation

- `dataset_images__dataset_state`: mean_abs_delta=25.530, max_abs_delta=65.249 at `right_joint_4.pos`
- `dataset_images__snapshot_state`: mean_abs_delta=24.370, max_abs_delta=65.111 at `right_joint_4.pos`
- `snapshot_images__dataset_state`: mean_abs_delta=26.498, max_abs_delta=67.306 at `right_joint_4.pos`
- `snapshot_images__snapshot_state`: mean_abs_delta=26.648, max_abs_delta=71.123 at `right_joint_4.pos`

## Safety

- No robot connection, motor initialization, torque enable, zeroing, or action send is performed by this script.
- This is an offline A6000 policy/input contract probe only.

## Follow-up Finding

The checkpoint `policy_postprocessor_step_0_unnormalizer_processor.safetensors`
stores action quantiles that match absolute joint-angle distributions, not the
small relative action deltas observed in `full_folding` episode 0. Representative
examples:

```text
right_joint_4 action q01/q99 in checkpoint: 24.8628 / 116.9012 deg
left_joint_4  action q01/q99 in checkpoint: 17.8704 / 115.2879 deg
right_joint_7 action q01/q99 in checkpoint: -72.8163 / 8.0137 deg
```

Because the policy config has `use_relative_actions=true`, these absolute
action statistics are a major processor-contract risk. Dataset replay shows the
loaded model/runtime path still does not reproduce dataset actions, so the next
step is not robot motion; it is checkpoint/processor validation against the
training-time pipeline.
