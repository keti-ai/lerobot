# Stage 26 Recipe Alignment

## Decision

The deployment recipe is not aligned. The primary blocker is not camera
extrinsics, arm reach, or first-write clamp selection. The current
`lerobot/folding_latest` checkpoint was trained/exported with
`use_relative_actions=true`, but its saved action normalization stats match
absolute dataset action quantiles.

This violates the LeRobot pi action recipe: relative action conversion must
happen before normalization, so action normalizer/unnormalizer stats must be
computed in relative action space.

Robot motion remains blocked.

## Official Recipe Evidence

LeRobot Pi05 docs state that relative actions require recomputing dataset stats
in relative space before training:

```text
lerobot-edit-dataset \
  --repo_id your_dataset \
  --operation.type recompute_stats \
  --operation.relative_action true \
  --operation.chunk_size 50 \
  --operation.relative_exclude_joints "['gripper']"
```

The action representation docs state the same contract more explicitly:

```text
raw absolute action -> RelativeActionsProcessorStep -> normalize -> model
model output -> unnormalize -> AbsoluteActionsProcessorStep -> robot
```

Therefore `use_relative_actions=true` requires action stats over
`action - observation.state` for non-gripper joints. Grippers may remain
absolute through `relative_exclude_joints=["gripper"]`.

## Model/Dataset Identity

The model card for `lerobot/folding_latest` says the model was trained on:

```text
lerobot-data-collection/level2_final_quality3_t_0_hil_data_c
```

It was not trained directly on `lerobot/full_folding`. Stage 25 reran dataset
replay on the model-card training dataset and still reproduced the large-delta
failure:

```text
frame 0  model mean_abs_delta=25.588 deg, recorded mean_abs_delta=1.300 deg
frame 1  model mean_abs_delta=24.644 deg, recorded mean_abs_delta=1.156 deg
frame 10 model mean_abs_delta=26.065 deg, recorded mean_abs_delta=1.424 deg
frame 30 model mean_abs_delta=27.654 deg, recorded mean_abs_delta=1.325 deg
```

The failure is therefore not only a wrong replay dataset choice.

## Local Recipe Evidence

`src/lerobot/policies/pi05/processor_pi05.py` builds the intended order:

```text
RenameObservationsProcessorStep
AddBatchDimensionProcessorStep
RelativeActionsProcessorStep
NormalizerProcessorStep
Pi05PrepareStateTokenizerProcessorStep
TokenizerProcessorStep
DeviceProcessorStep
```

The postprocessor order is:

```text
UnnormalizerProcessorStep
AbsoluteActionsProcessorStep
DeviceProcessorStep
```

`src/lerobot/scripts/lerobot_train.py` passes `dataset.meta.stats` into both
normalizer and unnormalizer. That is only correct for relative training if the
dataset stats were recomputed into relative action space before training.

## Verified Mismatch

`folding_latest/train_config.json`:

```text
dataset.repo_id = lerobot-data-collection/level2_final_quality3_t_0_hil_data_c
policy.type = pi05
policy.pretrained_path = lerobot-data-collection/folding_final
policy.use_relative_actions = true
policy.relative_exclude_joints = ["gripper"]
policy.normalization_mapping = {"VISUAL":"IDENTITY","STATE":"QUANTILES","ACTION":"QUANTILES"}
policy.chunk_size = 30
```

The training dataset `meta/stats.json` action quantiles equal the checkpoint
postprocessor action quantiles. Representative absolute stats:

```text
right_joint_4 action q01/q99 = 24.8628 / 116.9012 deg
left_joint_4  action q01/q99 = 17.8704 / 115.2879 deg
right_joint_7 action q01/q99 = -72.8163 / 8.0137 deg
```

But sampled relative deltas from the same training dataset are much smaller:

```text
right_joint_4 relative q01/q99 ~= -5.2835 / 6.2061 deg
left_joint_4  relative q01/q99 ~= -4.9940 / 6.2808 deg
right_joint_7 relative q01/q99 ~= -2.8432 / 4.4488 deg
```

This explains why unnormalization can turn normalized model outputs into
60-70 degree "relative" deltas.

## Required Alignment Work

1. Stop using `folding_latest` for actuator commands.
2. Rebuild the policy processor stats for relative actions using the model-card
   training dataset:

```bash
lerobot-edit-dataset \
  --repo_id lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --operation.type recompute_stats \
  --operation.relative_action true \
  --operation.chunk_size 30 \
  --operation.relative_exclude_joints "['gripper']"
```

3. Decide whether to retrain/export a corrected checkpoint or locate an already
   corrected Hugging Face checkpoint trained with relative stats.
4. Before any robot run, perform dataset replay on the model-card training
   dataset. Acceptance threshold:

```text
model mean_abs_delta should be near recorded mean_abs_delta on held dataset frames
right_joint_4/left_joint_4/right_joint_7 must not show 60-70 deg deltas
raw normalized output should match normalized recorded relative target
```

5. Only after training-dataset replay passes, rerun syhlabtop no-send snapshot
   review. First actuator write remains disallowed until that pass.

## Current Root Cause Statement

The current best root cause is: `folding_latest` is a relative-action Pi05
checkpoint whose saved action processor stats are absolute-action stats from
`level2_final_quality3_t_0_hil_data_c`. This violates the official LeRobot
relative-action recipe and makes the deployed postprocessor unsafe.
