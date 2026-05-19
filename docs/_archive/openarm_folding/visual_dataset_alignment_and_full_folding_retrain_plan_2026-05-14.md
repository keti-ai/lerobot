# Visual Dataset Alignment And Full Folding Retrain Plan

timestamp: `2026-05-14`

## Current Situation

Track B is COMPLETE on A6000. `full_folding` step-004000 training finished.
Recipe gate PASS, but dataset replay gate FAIL (delta ratio 0.128–0.282 vs
threshold 0.25–4.0, no abnormal 60–70 deg deltas, max global delta 2.086 deg).
`full_folding` checkpoint 004000 is NOT a deploy candidate. Next: Track C compares
checkpoints 002000/003000 replay gate to decide underfit vs checkpoint selection.
Track A live rollout is unblocked and uses the current level2 corrected checkpoint.

The live policy input viewer is available on syhlabtop for read-only camera
checks. When running, it exposes the three actual policy camera inputs:

- `left_wrist`: RealSense `315122270766`, `640x480@30`
- `right_wrist`: RealSense `230322273311`, `640x480@30`
- `base`: RealSense `213622075840`, `640x480@30`

Viewer:

- `http://127.0.0.1:8091/`
- `http://10.252.216.81:8091/`
- `http://192.168.1.58:8091/`

The main observed visual gap is the `base` view. Raising the camera makes the shirt visible but makes the arms visually smaller/narrower than the dataset reference. Wrist views appear closer, but still need a key-by-key visual check.

## Dataset Metadata Facts

Small Hugging Face metadata files were checked only; no video shards were downloaded on syhlabtop.

### `lerobot/full_folding`

- robot_type: `openarms_follower`
- episodes: `5688`
- frames: `14129038`
- fps: `30`
- tasks: `1`
- task text from `meta/tasks.parquet`: `Fold the T-shirt properly`
- state/action: 16D, right arm first, then right gripper, left arm, left gripper
- cameras:
  - `observation.images.left_wrist`: `[720, 1280, 3]`
  - `observation.images.right_wrist`: `[720, 1280, 3]`
  - `observation.images.base`: `[480, 640, 3]`

### `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`

- robot_type: `openarms_follower`
- episodes: `1319`
- frames: `3414338`
- fps: `30`
- tasks: `1`
- task text from `meta/tasks.parquet`: `Fold the T-shirt properly`
- state/action/camera schema matches `full_folding`

Interpretation: the dataset gap is not a simple schema or task-string mismatch. It is primarily distributional: collection scope, difficulty split, episode composition, camera setup, hardware setup, and possibly quality weighting.

## Planning Decision

Do not treat `full_folding` as incompatible. It is a valid candidate for retraining or continued fine-tuning after relative action stats are recomputed.

Do not add a runtime-only fisheye or perspective transform directly into deployment as the first fix. If a camera transform is needed, it should be treated as part of the observation contract and tested in both:

1. dataset replay / offline inference,
2. live no-actuation proposal review,
3. retraining or fine-tuning if the transform materially changes the image distribution.

Runtime-only image warping can help if it approximates the training view, but it can also create a new OOD visual style if the model never saw that distortion.

## Work Placement

### syhlabtop

Use syhlabtop for real hardware and visual input truth. During Track B, keep
syhlabtop work to read-only viewer/camera preparation unless a separate command
explicitly requests otherwise.

- live 3-camera viewer,
- still captures from actual policy inputs,
- camera pose/FOV experiments,
- read-only state snapshots,
- side-by-side human visual review,
- final live rollout after Track B finishes and the selected A6000 candidate
  passes gates.

Do not use syhlabtop for full dataset download, full video decoding, or training.

### A6000

Use A6000 for dataset and model work. Track B owns this work now:

- metadata gate for `full_folding`,
- representative frame export from `full_folding` and `level2_final_quality3_t_0_hil_data_c`,
- relative stats recomputation,
- dataset replay,
- training/fine-tuning,
- visual embedding or sampled-frame comparisons,
- checkpoint serving.

## Immediate Work Plan

1. Track B A6000: finish `full_folding` relstats + RABC training.
   - Verify `sarm_progress.parquet` index compatibility.
   - Produce relative-stats artifact, checkpoint, recipe gate, and dataset replay.
   - Export level2 and `full_folding` reference mosaics.

2. syhlabtop: capture real policy input references when needed.
   - Use the live viewer to capture multiple still sets:
     - current rollout-ready pose,
     - shirt centered and visible,
     - arms on tabletop ready pose,
     - camera raised until shirt is fully visible,
     - camera raised plus any candidate physical tilt.
   - Save each as three separate images plus mosaic.

3. Compare dataset reference mosaics from A6000.
   - Export sampled `left_wrist`, `right_wrist`, `base` frames from:
     - `lerobot/full_folding`,
     - `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`.
   - Prefer comparable timestamps:
     - early ready frames,
     - first cloth contact,
     - mid-fold,
     - end-fold.
   - Include episode index, frame index, task text, and state/action row.

4. Build side-by-side comparison artifact.
   - Rows: real syhlabtop captures.
   - Columns: live input, `full_folding` references, level2 references.
   - Compare separately for:
     - base view FOV,
     - left/right wrist view direction,
     - cloth scale,
     - arm scale,
     - gripper visibility,
     - table edge / tabletop occupancy,
     - camera rotation or left-right swap risk.

5. Decide camera alignment strategy.
   - Preferred first: physical camera pose/height/tilt that matches dataset without image warping.
   - If physical view cannot show both shirt and arms at dataset-like scale:
     - test deterministic base-image transform candidates offline,
     - compare with dataset references,
     - run no-actuation A6000 proposals for each transform,
     - only then consider using the transform in live deployment.
   - Candidate transforms:
     - crop/resize,
     - mild barrel/fisheye-style warp,
     - perspective warp,
     - camera-specific undistort/rectify if intrinsics are known.

6. Resume live rollout only after Track B is done and the visual/candidate choice is fixed.
   - Keep monitor-only safety policy if operator chooses.
   - Keep metadata hard checks:
     - `robot_config_id`,
     - `joint_order`,
     - `action_units`,
     - `checkpoint_id`,
     - `action_normalization_id`.

## Key Open Questions

- Is the current base camera physically the same class and FOV as the dataset base camera?
- Are the +5 cm upper-arm extension and larger jaws installed exactly as in the folding setup?
- Does `full_folding` contain lower-quality or non-deploy episodes that should be filtered, despite larger size?
- Does the current live base view need a transform, or should the physical camera be moved first?
- Should training use `full_folding` only, or continue from the current level2 candidate with a curated mix?

## Recommendation

Proceed in this order:

1. Track B A6000 training/gate/replay,
2. dataset reference mosaic export,
3. syhlabtop visual comparison artifact,
4. camera physical alignment,
5. no-actuation or health/metadata proposal comparison after serving is restored,
6. only then Track A live rollout.

This keeps syhlabtop focused on real sensor truth and A6000 focused on data/model iteration.

## Revised Operator Plan

The current served model was retrained from the level2 dataset path, not from
`full_folding`. Track B is now training a `full_folding` candidate in parallel,
so the next real-robot experiment should wait for Track B completion, then choose
between the current level2 candidate and the Track B candidate.

### 1. Test The Current Level2 Model In A Level2-Like Scene

Place the shirt in the middle of the workspace in a messy/crumpled initial state.

Rationale:

- The official folding recipe defines Level 2 as a messy-shirt task: spread the
  shirt, fold it, and place it aside.
- The current checkpoint was trained from
  `level2_final_quality3_t_0_hil_data_c_relative_stats_chunk30`.
- The observed policy behavior already looks like it is trying to bring the
  arms toward the tabletop workspace, so the next test should reduce scene OOD
  before changing the model.

Acceptance signal:

- policy reaches toward the shirt rather than just the table edge,
- base view sees the messy shirt clearly,
- wrist views show grippers and cloth contact,
- no repeated limit-saturation behavior dominates the rollout.

### 2. Align The Base View Before Retaining A New Model

The base view is currently the largest visual mismatch. If the camera is raised
enough to see the shirt, the arms become visually narrow/small compared with the
dataset reference. This should be handled as an observation alignment problem.

Order of attempts:

1. Physical camera height/tilt adjustment.
2. Deterministic preprocessing candidates for the base image:
   - crop + resize,
   - mild barrel/fisheye-like warp,
   - perspective warp,
   - intrinsics-based undistort/rectify if intrinsics are available.
3. No-actuation proposal comparison for each preprocessing candidate.

Do not silently introduce a base image transform into live deployment without
recording it as part of the observation contract. If it is used in live rollout,
the same transform must be logged with a stable `vision_preprocess_id`.

### 3. Use Track B `full_folding` As A Parallel Candidate

`full_folding` is schema-compatible and much larger:

- 5,688 episodes / 14.1M frames,
- same `openarms_follower`,
- same 16D state/action names,
- same three camera keys and shapes.

However the official recipe notes that the full dataset mixes operators,
strategies, backgrounds, camera viewpoints, robot heights, and quality levels.
It also says the project later built a smaller high-quality dataset from the full
set because not all episodes were equally useful.

Therefore `full_folding` is a strong Track B retraining candidate, but it should
not be treated as automatically better. It still needs:

- task/instruction metadata audit,
- episode-level distribution audit,
- relative action stats recomputation,
- SARM/RABC or quality weighting decision,
- dataset replay acceptance,
- live no-actuation or health/metadata proposal comparison against the current
  level2 model after serving is restored.

If `full_folding` is used, prefer comparing at least three candidates:

1. current level2 relative-stats checkpoint,
2. `full_folding` relative-stats checkpoint,
3. staged or mixed fine-tune from current level2 candidate using curated
   `full_folding` episodes.

### 4. Concrete Next Sequence

1. A6000: finish Track B `full_folding` relstats + RABC training.
2. A6000: publish gate/replay outputs and representative dataset mosaics.
3. syhlabtop: capture the 3 live policy inputs with the viewer.
4. syhlabtop + A6000 outputs: compare live views against level2 and `full_folding` references.
5. syhlabtop: adjust base camera height/tilt if needed and capture comparison stills.
6. Choose Track A checkpoint: current level2 corrected candidate or Track B `full_folding` candidate.
7. Re-establish A6000 serving and verify health/metadata.
8. Generate a fresh Track A rollout envelope and execute only after explicit operator approval.
