# LeRobot OpenArm Folding Artifact Metadata Audit

Date: 2026-05-10
Branch: `audit/openarm-folding-baseline`
Workspace: `/home/syh/workspace/lerobot`

## Scope

This is a metadata-only audit. I did not edit repository code, run the robot, train, or download dataset payloads/video/data shards or `model.safetensors`.

Hub metadata was fetched under `/tmp/lerobot_openarm_folding_hf_meta` for the requested small files only:

- `README.md`
- `config.json`
- `train_config.json`
- `policy_preprocessor.json`
- `policy_postprocessor.json`
- `meta/info.json`
- `meta/stats.json`
- `meta/tasks.*`

## Source Inputs Read

Local files read:

- `AGENTS.md`, `CLAUDE.md`, `README.md`, `pyproject.toml`
- `docs/source/openarm.mdx`, `docs/source/pi05.mdx`, `docs/source/action_representations.mdx`
- `src/lerobot/robots/bi_openarm_follower/*`
- `src/lerobot/robots/openarm_follower/*` and `src/lerobot/motors/damiao/*` for delegated OpenArm motor units and gripper handling
- `src/lerobot/policies/pi05/*`
- `src/lerobot/processor/relative_action_processor.py`
- `src/lerobot/rollout/*`

Hub source URLs:

- `https://huggingface.co/lerobot/folding_latest`
- `https://huggingface.co/datasets/lerobot/high_quality_folding`
- `https://huggingface.co/datasets/lerobot/full_folding`
- `https://huggingface.co/datasets/lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`

## Required Conclusions

### Is `lerobot/folding_latest` LeRobot-native or OpenPI?

`lerobot/folding_latest` is a LeRobot-native checkpoint/repository layout for policy type `pi05`. It loads through LeRobot `PI05Policy` and LeRobot policy processor JSON files. It does not runtime-import an `openpi` Python package.

The implementation is still explicitly an OpenPI port/adaptation:

- `docs/source/pi05.mdx:3` says the LeRobot implementation is adapted from OpenPI.
- `src/lerobot/policies/pi05/modeling_pi05.py:949-952` prints that PI05 is a direct port of OpenPI.
- `rg` found OpenPI mentions only in docs/comments/strings, not `import openpi` or `from openpi`.

Verdict: LeRobot-native loader/checkpoint format, OpenPI-derived implementation.

### Exact State/Action Ordering

All audited folding datasets and `folding_latest` use the same 16-dimensional state/action names:

1. `right_joint_1.pos`
2. `right_joint_2.pos`
3. `right_joint_3.pos`
4. `right_joint_4.pos`
5. `right_joint_5.pos`
6. `right_joint_6.pos`
7. `right_joint_7.pos`
8. `right_gripper.pos`
9. `left_joint_1.pos`
10. `left_joint_2.pos`
11. `left_joint_3.pos`
12. `left_joint_4.pos`
13. `left_joint_5.pos`
14. `left_joint_6.pos`
15. `left_joint_7.pos`
16. `left_gripper.pos`

This matches `BiOpenArmFollower._motors_ft`, which is explicitly right arm first, then left arm (`src/lerobot/robots/bi_openarm_follower/bi_openarm_follower.py:96-106`). Observations are read right first then left (`bi_openarm_follower.py:157-165`), and actions are split by `right_`/`left_` prefixes before being sent to each arm (`bi_openarm_follower.py:176-192`).

### Units

- State/action `.pos` values are degrees.
- `OpenArmFollower` constructs Damiao `Motor(..., MotorNormMode.DEGREES)` (`src/lerobot/robots/openarm_follower/openarm_follower.py:54-57`).
- `DamiaoMotorsBus` encodes outgoing MIT position commands by converting degrees to radians internally, and decodes motor state back to degrees.
- Velocity, when enabled, is degrees per second; torque is motor torque. Those channels are not part of the audited policy feature tensors because rollout filters policy-facing state/action to `.pos` only (`src/lerobot/rollout/context.py:272-284`).
- Image tensors in dataset stats are normalized image values in `[0, 1]`; PI05 preprocessing converts model images to `[-1, 1]` and resizes/pads to `224x224`.

### Gripper Semantics

The grippers are positional Damiao joints in degrees, not binary open/close flags.

OpenArm calibration asks for grippers closed at zero position, and the default side-specific hardware limits are `gripper: (-65.0, 0.0)` for both arms (`src/lerobot/robots/openarm_follower/config_openarm_follower.py:23-42`). Runtime `send_action` clips each goal to configured joint limits before sending (`src/lerobot/robots/openarm_follower/openarm_follower.py:276-285`).

`folding_latest` excludes `"gripper"` from relative action conversion. Because the mask excludes any action name containing `gripper`, dimensions 8 and 16 remain absolute gripper target positions; all other joint dimensions are relative offsets during model normalization/training.

Dataset action stats contain some gripper outliers above zero, but a correctly configured OpenArm follower with side-specific limits will clip above-zero gripper targets back to `0.0`.

### Camera Mapping

Audited dataset and model camera keys:

- `observation.images.left_wrist`
  - Dataset video shape: `[720, 1280, 3]`
  - Policy config shape: `[3, 720, 1280]`
- `observation.images.right_wrist`
  - Dataset video shape: `[720, 1280, 3]`
  - Policy config shape: `[3, 720, 1280]`
- `observation.images.base`
  - Dataset video shape: `[480, 640, 3]`
  - Policy config shape: `[3, 480, 640]`

`BiOpenArmFollower` does not prefix camera names with `left_`/`right_`; camera keys are user-chosen names and are merged directly (`src/lerobot/robots/bi_openarm_follower/bi_openarm_follower.py:108-113`). Therefore the syhlabtop camera config must expose camera keys exactly as `left_wrist`, `right_wrist`, and `base`, or rollout must use an explicit `rename_map`.

Metadata does not identify physical camera serial numbers or image orientation. That remains a hardware-side validation item.

### Relative vs Absolute Action Processor Chain

`folding_latest` config:

- `type`: `pi05`
- `chunk_size`: `30`
- `n_action_steps`: `30`
- `use_relative_actions`: `true`
- `relative_exclude_joints`: `["gripper"]`
- `normalization_mapping`: `VISUAL=IDENTITY`, `STATE=QUANTILES`, `ACTION=QUANTILES`

Saved preprocessor chain:

1. `rename_observations_processor`
2. `to_batch_processor`
3. `delta_actions_processor`, enabled, exclude `["gripper"]`
4. `normalizer_processor`
5. `pi05_prepare_state_tokenizer_processor_step`
6. `tokenizer_processor`, `google/paligemma-3b-pt-224`
7. `device_processor`

Saved postprocessor chain:

1. `unnormalizer_processor`
2. `absolute_actions_processor`, enabled
3. `device_processor`

The PI05 factory comment states the intended order as:

`raw -> relative -> normalize -> model -> unnormalize -> absolute`

Source: `src/lerobot/policies/pi05/processor_pi05.py:132-165`.

The relative transform is:

- Training/preprocess: `relative = action - observation.state` for masked dimensions.
- Inference/postprocess: `absolute = relative + cached observation.state`.
- Gripper dimensions remain absolute because of the exclude mask.

Source: `src/lerobot/processor/relative_action_processor.py:40-81` and `relative_action_processor.py:106-202`.

### Can syhlabtop Robot IO Safely Pair With A6000 LeRobot Inference?

Not as a split-machine setup with the current rollout code.

The current rollout architecture is single-process:

- It loads the policy first, then connects robot hardware in the same `build_rollout_context` call (`src/lerobot/rollout/context.py:169-239`).
- `ThreadSafeRobot` serializes access between local threads, not between hosts (`src/lerobot/rollout/robot_wrapper.py`).
- RTC inference is a background thread in the same process, not a remote GPU service (`src/lerobot/rollout/inference/rtc.py:85-160`).
- `display_ip`/`display_port` are for remote Rerun display, not policy inference transport.

If syhlabtop owns CAN/camera IO and the A6000 is a different machine, the repo as read has no safe built-in RPC boundary to run robot IO on syhlabtop and inference on A6000. It can only be considered safe if the same process runs on a host that has both robot/camera IO access and the A6000 device, or if a separate remote-inference bridge is added and audited.

Also, `folding_latest` has relative actions enabled, and `SyncInferenceEngine` is explicitly rejected for relative-action policies at context-build time (`src/lerobot/rollout/context.py:398-405`). For this policy, rollout must use `--inference.type=rtc` unless sync is changed.

### What Remains Blocked Before No-Motion/Shadow Eval

Blocked items before a no-motion/shadow eval can be considered safe:

1. Required model/runtime assets are not downloaded yet:
   - `lerobot/folding_latest/model.safetensors`
   - `policy_preprocessor_step_3_normalizer_processor.safetensors`
   - `policy_postprocessor_step_0_unnormalizer_processor.safetensors`
   - tokenizer assets for `google/paligemma-3b-pt-224`, unless already cached
2. There is no audited no-motion/shadow rollout path yet. Current strategies eventually call `send_action` through `send_next_action` (`src/lerobot/rollout/strategies/core.py:269-304`).
3. Rollout teardown can send return-to-initial actions unless `return_to_initial_position=false`; even then, normal autonomous loops still send actions.
4. `OpenArmFollower.connect()` enables torque after configuration, so a shadow eval that physically connects hardware needs an explicit torque/no-send safety plan.
5. The syhlabtop camera/CAN mapping must be verified:
   - left arm CAN port and `side=left`
   - right arm CAN port and `side=right`
   - camera serials/devices bound to keys `left_wrist`, `right_wrist`, `base`
   - actual image orientation and time synchronization
6. The remote/split inference boundary is unresolved. Current code has no remote A6000 inference server/client path.
7. A one-batch offline processor check is still needed after allowed asset downloads:
   - policy config feature keys equal dataset and robot keys
   - normalizer state loads
   - relative/absolute processors reattach after deserialization
   - action tensor length is 16 and maps to the exact ordering above
8. Gripper behavior needs a hardware-side safety check because model/dataset gripper action outliers can exceed `0.0`, while OpenArm follower clips to configured limits.

## Hub Artifact Inventory

| Artifact | Repo Type | Revision SHA | Last Modified | Downloaded Audit Files |
| --- | --- | --- | --- | --- |
| `lerobot/folding_latest` | model | `ba6b3449705954d159853fb84ebe4e6749ae76a6` | `2026-04-03T15:56:33.000Z` | `README.md`, `config.json`, `train_config.json`, `policy_preprocessor.json`, `policy_postprocessor.json` |
| `lerobot/high_quality_folding` | dataset | `c9eb858d4b84e520edecbda84a3534c3c1e78436` | `2026-02-26T20:39:21.000Z` | `README.md`, `meta/info.json`, `meta/stats.json`, `meta/tasks.parquet` |
| `lerobot/full_folding` | dataset | `6ae73269ee62c41534347d31ae2b91fc9aa57a4b` | `2026-02-17T19:59:18.000Z` | `README.md`, `meta/info.json`, `meta/stats.json`, `meta/tasks.parquet` |
| `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c` | dataset | `2496db53d330c360f910d095e13698d968c56fc6` | `2026-03-09T23:32:20.000Z` | `README.md`, `meta/info.json`, `meta/stats.json`, `meta/tasks.parquet` |

## `lerobot/folding_latest` Model Metadata

Key config facts:

- Policy type: `pi05`
- Device in config: `cuda`
- dtype: `bfloat16`
- Base/pretrained path recorded in config: `lerobot-data-collection/folding_final`
- Repo ID recorded in config: `lerobot-data-collection/folding_final10`
- Training dataset in `train_config.json`: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`
- Train steps: `4000`
- Batch size: `32`
- Seed: `1000`
- RABC enabled: `true`
- RABC progress path: `hf://datasets/lerobot-data-collection/level2_final_quality3_t_0_hil_data_c/sarm_progress.parquet`

Important non-fetched model files present in the model repo:

- `model.safetensors`
- `policy_preprocessor_step_3_normalizer_processor.safetensors`
- `policy_postprocessor_step_0_unnormalizer_processor.safetensors`

Those are required for actual inference but were intentionally not fetched in this audit.

## Dataset Metadata Comparison

All three datasets use:

- `codebase_version`: `v3.0`
- `robot_type`: `openarms_follower`
- `fps`: `30`
- `total_tasks`: `1`
- task text from `meta/tasks.parquet`: `Fold the T-shirt properly`
- same 16 action/state names listed above
- same camera keys and shapes listed above

| Dataset | Episodes | Frames | Notes |
| --- | ---: | ---: | --- |
| `lerobot/high_quality_folding` | 1200 | 3,254,196 | Same schema as policy dataset, but not the dataset referenced by `folding_latest` train config |
| `lerobot/full_folding` | 5688 | 14,129,038 | Larger superset-style folding dataset with same schema |
| `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c` | 1319 | 3,414,338 | Dataset referenced by `folding_latest` train config |

The model was trained against `level2_final_quality3_t_0_hil_data_c`, not `high_quality_folding` or `full_folding`, based on `folding_latest/train_config.json`.

## Compatibility Notes

- `robot_type` in dataset metadata is `openarms_follower`, while the current local bimanual wrapper class is named `bi_openarm_follower`. The feature schema matches the bimanual wrapper; the `robot_type` string should not be treated as proof that a single-arm robot is compatible.
- The bimanual wrapper's motor ordering matches the dataset and policy ordering exactly.
- The bimanual wrapper's camera keys are not automatically namespaced. This is compatible with the dataset only if the hardware camera config uses the exact names `left_wrist`, `right_wrist`, and `base`.
- Relative-action inference with this policy requires the cached state from the preprocessor. RTC has explicit relative prefix re-anchoring logic (`src/lerobot/rollout/inference/rtc.py:141-159` and `rtc.py:287-308`); sync inference is blocked for relative-action policies.
