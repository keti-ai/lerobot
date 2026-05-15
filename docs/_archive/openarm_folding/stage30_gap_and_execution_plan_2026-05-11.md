# Stage 30 Gap And Execution Plan

## Current Position

Goal: deploy a PI0.5 folding policy from the A6000 inference path to the real
bimanual OpenArm on syhlabtop.

Current project state:

- Stage 27 hard recipe gate exists.
- Stage 29 candidate search completed on A6000.
- Stage 30 target relative-action reference stats completed on A6000.
- Robot motion remains blocked.

## What Was Checked

Expanded Stage 29 checked 37 public folding/level/ablation checkpoint
candidates using only lightweight model metadata and processor stats.

Result:

- deploy candidates: `0`
- direct target-dataset candidates `lerobot/folding_latest` and
  `lerobot-data-collection/folding_final10`: failed
  `postprocessor_action_stats_are_relative_for_arm_joints`
- many older ablation checkpoints use legacy `use_delta_actions` fields or
  non-PI0.5 policy types and are not compatible with the current recipe gate

Target dataset reference:

- dataset: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`
- rows: `3414338`
- robot type: `openarms_follower`
- arm mean absolute relative delta: `1.722 deg`
- arm p99 absolute relative delta: `19.789 deg`
- arm max absolute relative delta: `116.352 deg` at `left_joint_4.pos`

## Primary Gap

The locked folding recipe is relative-action PI0.5:

```text
policy.type=pi05
policy.use_relative_actions=true
policy.relative_exclude_joints=["gripper"]
policy.chunk_size=30
policy.n_action_steps=30
```

For pi policies, relative conversion happens before normalization. Therefore
normalizer/postprocessor action stats must be computed over `action - state`
for arm joints, while grippers remain absolute.

The currently available folding checkpoints do not satisfy that contract. For
`lerobot/folding_latest`, the postprocessor stats differ from sampled relative
stats by up to:

```text
q01 error: 69.973 deg
q99 error: 110.695 deg
span ratio: 14.230
worst span key: left_joint_1.pos
```

That magnitude explains the large first action deltas and makes the issue a
recipe/artifact mismatch before it is a live-camera or embodiment problem.

## Secondary Gaps

Hardware/extrinsic differences still matter after the recipe gap is fixed:

- HF setup uses +5 cm upper arm extensions.
- HF setup uses larger gripper jaws.
- Base/high camera must match the robot-folding high overview layout.
- Current syhlabtop camera was raised about 25 cm as a temporary experiment.

These are not first-order blockers for the current abnormal delta because the
failure reproduces from dataset replay without live camera input.

## Required Next Work

1. Create or use a corrected dataset artifact whose stats are recomputed for
   relative actions with `chunk_size=30` and gripper excluded.
2. Retrain or re-export a PI0.5 checkpoint from that corrected recipe.
3. Run Stage 29 recipe gate on the corrected candidate.
4. If Stage 29 passes, run Stage 31 dataset replay on frames `0,1,10,30`.
5. Only after Stage 31 passes, return to syhlabtop no-send snapshot and guarded
   first-write preparation.

## A6000 Commands

Use a new dataset repo or local copy for recomputed stats. Do not mutate the
original target dataset unless that is intentional.

```bash
BASE=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
cd /home/syh/workspace/lerobot

uv run lerobot-edit-dataset \
  --repo_id lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --root "$BASE/datasets/level2_final_quality3_t_0_hil_data_c" \
  --new_root "$BASE/datasets/level2_final_quality3_t_0_hil_data_c_relative_stats_chunk30" \
  --operation.type recompute_stats \
  --operation.relative_action true \
  --operation.chunk_size 30 \
  --operation.relative_exclude_joints "['gripper']"
```

Training/export must keep:

```text
policy.type=pi05
policy.pretrained_path=lerobot-data-collection/folding_final
policy.use_relative_actions=true
policy.relative_exclude_joints=["gripper"]
policy.chunk_size=30
policy.n_action_steps=30
```

After a corrected candidate is produced:

```bash
BASE=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
cd /home/syh/workspace/lerobot

PYTHONPATH=$BASE/tools $BASE/probevenv/bin/python \
  $BASE/tools/stage29_candidate_recipe_gate.py \
  --dataset-repo lerobot-data-collection/level2_final_quality3_t_0_hil_data_c \
  --dataset-root "$BASE/datasets/level2_final_quality3_t_0_hil_data_c" \
  --candidate <CORRECTED_MODEL_DIR_OR_REPO> \
  --json-out "$BASE/audits/stage29_corrected_candidate_gate_2026-05-11.json" \
  --md-out "$BASE/audits/stage29_corrected_candidate_gate_2026-05-11.md"
```

Stage 31 replay may start only if that command returns pass.

## Safety State

Still blocked:

- `lerobot-rollout`
- `lerobot-record`
- `lerobot-replay`
- `OpenArmFollower.connect()` for read-only probes
- any `robot.send_action()`
- any policy output to motors
- any full-arm zero/calibration
