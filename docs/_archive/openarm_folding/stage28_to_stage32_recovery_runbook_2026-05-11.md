# Stage 28-32 OpenArm Folding Recipe Recovery Runbook

## Decision

Robot motion remains blocked until a corrected checkpoint passes both the
recipe gate and training-dataset replay. The current `lerobot/folding_latest`
failure is treated as an artifact/recipe mismatch, not a camera or first-write
problem.

## Stage 28 Source Map

Locked recipe sources:

```text
robot-folding Space: https://huggingface.co/spaces/lerobot/robot-folding#hardware
Pi05 docs: docs/source/policy_pi05_README.md
relative actions docs: docs/source/action_representations.mdx
Pi05 processor order: src/lerobot/policies/pi05/processor_pi05.py
relative action conversion: src/lerobot/processor/relative_action_processor.py
RTC inference: src/lerobot/rollout/inference/rtc.py
action interpolation: src/lerobot/utils/action_interpolator.py
SARM/RABC weighting: src/lerobot/rewards/sarm/rabc.py
OpenArm hardware docs: docs/source/openarm.mdx
```

Locked recipe values:

```text
policy: pi05
chunk_size: 30
n_action_steps: 30
action representation: relative trajectory
relative exclude: ["gripper"]
state/action: 16D OpenArm order, right arm + right gripper, then left arm + left gripper
camera keys: observation.images.left_wrist, observation.images.right_wrist, observation.images.base
camera shapes: left/right wrist 720x1280x3, base 480x640x3
training: SARM/RABC recorded
runtime after acceptance: RTC execution horizon 20, action interpolation multiplier 3
hardware after acceptance: +5 cm upper arm and larger gripper jaws recorded before deployment
```

`stage22_dataset_replay_and_ablation.py` is the canonical entry point for all
future replay. Use its default recipe gate. `--no-recipe-gate` is reserved only
for forensics.

For lightweight candidate rejection, use:

```bash
uv run python audits/openarm_folding/stage22_dataset_replay_and_ablation.py \
  --recipe-gate-only \
  --dataset-repo lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --dataset-root <DATASET_ROOT> \
  --model-dir <MODEL_DIR> \
  --json-out <OUT>.json \
  --md-out <OUT>.md
```

This mode does not load policy weights, videos, snapshots, or robot IO.

## Stage 29 Candidate Search

Candidate order:

```text
lerobot/folding_latest revisions or siblings
lerobot-data-collection/folding_final*
robot-folding Space experiment 2.5 public checkpoint, currently tracked as lerobot-data-collection/ablation2-5_0 if available
```

Use the candidate gate wrapper:

```bash
uv run python audits/openarm_folding/stage29_candidate_recipe_gate.py \
  --dataset-repo lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --dataset-root <DATASET_ROOT> \
  --json-out audits/openarm_folding/stage29_candidate_recipe_gate_2026-05-11.json \
  --md-out audits/openarm_folding/stage29_candidate_recipe_gate_2026-05-11.md
```

The wrapper downloads/reads only lightweight metadata and processor stats. A
candidate with any recipe gate failure is excluded from deploy consideration.

2026-05-11 result:

```text
expanded candidates checked: 37
deploy candidates: 0
direct target-dataset candidates checked: lerobot/folding_latest, lerobot-data-collection/folding_final10
direct target-dataset failure: postprocessor_action_stats_are_relative_for_arm_joints
folding_latest q01/q99 relative stat errors: 69.973 deg / 110.695 deg
```

## Stage 30 Regeneration Path

If no public or local candidate passes, regenerate the dataset stats and retrain
or export from the corrected recipe. Processor-only stats swapping remains
disallowed for deployment because previous probes showed raw model output also
failed to match the recorded normalized relative target.

The target dataset relative-action reference has been written by
`stage30_relative_recipe_reference.py`:

```text
dataset: lerobot-data-collection/level2_final_quality3_t_0_hil_data_c
rows: 3414338
arm mean abs relative delta: 1.722 deg
arm p99 abs relative delta: 19.789 deg
arm max abs relative delta: 116.352 deg at left_joint_4.pos
```

Required stats regeneration:

```bash
lerobot-edit-dataset \
  --repo_id lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --root <DATASET_ROOT> \
  --new_root <CORRECTED_DATASET_ROOT> \
  --operation.type recompute_stats \
  --operation.relative_action true \
  --operation.chunk_size 30 \
  --operation.relative_exclude_joints "['gripper']"
```

Training/export defaults:

```text
policy.type=pi05
policy.pretrained_path=lerobot-data-collection/folding_final
policy.use_relative_actions=true
policy.relative_exclude_joints=["gripper"]
policy.chunk_size=30
RABC enabled with valid progress path
```

## Stage 31 Acceptance

Each corrected candidate must run training-dataset replay on frames `0,1,10,30`.

Acceptance criteria:

```text
recipe gate: PASS
model mean_abs_delta: same order as recorded mean_abs_delta
right_joint_4/left_joint_4/right_joint_7: no 60-70 degree deltas
raw normalized output: near normalized recorded relative target
diagnostics: JSON and Markdown written even on failure
```

No syhlabtop snapshot review, CAN access, torque, or `send_action` is allowed
before this stage passes.

## Stage 32 Real Setup Re-entry

After Stage 31 passes:

```text
capture a fresh syhlabtop no-send snapshot
confirm high/base camera views match the Space layout
confirm wrist camera keys and shapes
record whether +5 cm upper arms and larger gripper jaws are installed
confirm gripper zero/range is unchanged
run no-send snapshot replay on A6000
```

Only after the no-send replay passes may the Stage 15-19 guarded first-write
pipeline be restarted with a fresh execution packet.
