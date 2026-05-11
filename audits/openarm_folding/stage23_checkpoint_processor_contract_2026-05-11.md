# Stage 23 Checkpoint Processor Contract

## Decision

The current blocker is not a safe hardware-write problem. It is a model/runtime
contract problem.

`folding_latest` does not reproduce small recorded actions when replayed on
actual `lerobot/full_folding` episode 0 frames. The output remains large even
when using dataset images and dataset state, so syhlabtop camera extrinsics and
current robot pose are no longer sufficient explanations.

## Checked

- Dataset replay was run on A6000 with no robot I/O.
- Episode 0 frames `0,1,10,30` were decoded from `full_folding` AV1 videos
  using `ffmpeg`.
- Policy input used the same `prepare_observation_for_inference`,
  `policy_preprocessor`, `predict_action_chunk`, and `policy_postprocessor`
  route used by prior snapshot action reviews.
- HF gated tokenizer access required:

```bash
HF_HOME=/mnt/nas/huggingface
HF_HUB_CACHE=/mnt/nas/huggingface/hub
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

## Result

Dataset recorded actions are small at the start of episode 0:

```text
frame 0  recorded mean_abs_delta=0.674 deg
frame 1  recorded mean_abs_delta=0.465 deg
frame 10 recorded mean_abs_delta=0.621 deg
frame 30 recorded mean_abs_delta=0.472 deg
```

The loaded policy produces large deltas on the same dataset inputs:

```text
frame 0  model mean_abs_delta=25.055 deg, max=64.972 deg at right_joint_4.pos
frame 1  model mean_abs_delta=25.978 deg, max=67.200 deg at right_joint_4.pos
frame 10 model mean_abs_delta=26.492 deg, max=70.036 deg at right_joint_4.pos
frame 30 model mean_abs_delta=24.052 deg, max=68.171 deg at right_joint_4.pos
```

State/visual ablation does not isolate the problem to syhlabtop hardware inputs:

```text
dataset_images + dataset_state  mean_abs_delta=25.530 deg
dataset_images + snapshot_state mean_abs_delta=24.370 deg
snapshot_images + dataset_state mean_abs_delta=26.498 deg
snapshot_images + snapshot_state mean_abs_delta=26.648 deg
```

## Processor Risk

The policy config says:

```text
use_relative_actions=true
relative_exclude_joints=["gripper"]
```

But the checkpoint postprocessor action quantiles match absolute joint-angle
distributions:

```text
right_joint_4 q01/q99 = 24.8628 / 116.9012 deg
left_joint_4  q01/q99 = 17.8704 / 115.2879 deg
right_joint_7 q01/q99 = -72.8163 / 8.0137 deg
```

This is inconsistent with the small recorded relative deltas in episode 0.
However, changing inference postprocessor stats alone is not safe, because the
model may also have been trained with the same mismatched normalization. The
required next validation is to reconstruct the training-time target
normalization and compare it with the model's raw normalized output on dataset
frames.

## Required Next Work

1. Compute `recorded_action - observation.state` for selected dataset frames.
2. Normalize those relative deltas using the checkpoint's current action
   quantiles.
3. Compare the normalized targets against raw `policy.predict_action_chunk`
   output before postprocessing.
4. If raw outputs do not match normalized targets on dataset frames, verify that
   `folding_latest` is the intended trained checkpoint and not a wrong/base or
   incompatible checkpoint.
5. Only after dataset replay matches recorded actions should syhlabtop snapshot
   review resume.

## Motion Gate

Motion remains blocked. No policy output from Stage 22 or Stage 23 is eligible
for guarded actuator write.
