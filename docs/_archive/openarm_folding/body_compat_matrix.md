# LeRobot OpenArm Folding Body Compatibility Matrix

Date: 2026-05-10
Policy artifact: `lerobot/folding_latest`
Training dataset from policy config: `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`

## Verdict

The policy/dataset body schema is compatible with the local `BiOpenArmFollower` motor key order: right arm first, then left arm; seven arm joints followed by the gripper for each arm.

The compatibility is metadata-only. It does not validate physical calibration, CAN bus assignment, camera serials, image orientation, latency, or no-motion safety.

## Joint State/Action Matrix

All state and action values are `.pos` positions in degrees. Model-space representation below refers to `folding_latest` preprocessing:

- `relative` means the model normalizer sees `action - observation.state` for that dimension.
- `absolute` means the dimension is excluded from relative conversion and stays an absolute target.
- Hardware send always receives absolute degree targets after postprocessing.

| Dim | Dataset/Policy Name | BiOpenArm Key Flow | Units | Model-Space Representation | Hardware Notes |
| ---: | --- | --- | --- | --- | --- |
| 1 | `right_joint_1.pos` | `right_` prefix removed, sent to right arm as `joint_1.pos` | deg | relative | Right shoulder pan |
| 2 | `right_joint_2.pos` | `right_` prefix removed, sent to right arm as `joint_2.pos` | deg | relative | Right shoulder lift |
| 3 | `right_joint_3.pos` | `right_` prefix removed, sent to right arm as `joint_3.pos` | deg | relative | Right shoulder rotation |
| 4 | `right_joint_4.pos` | `right_` prefix removed, sent to right arm as `joint_4.pos` | deg | relative | Right elbow flex |
| 5 | `right_joint_5.pos` | `right_` prefix removed, sent to right arm as `joint_5.pos` | deg | relative | Right wrist roll |
| 6 | `right_joint_6.pos` | `right_` prefix removed, sent to right arm as `joint_6.pos` | deg | relative | Right wrist pitch |
| 7 | `right_joint_7.pos` | `right_` prefix removed, sent to right arm as `joint_7.pos` | deg | relative | Right wrist rotation |
| 8 | `right_gripper.pos` | `right_` prefix removed, sent to right arm as `gripper.pos` | deg | absolute | Excluded from relative conversion; default side limit `[-65, 0]` |
| 9 | `left_joint_1.pos` | `left_` prefix removed, sent to left arm as `joint_1.pos` | deg | relative | Left shoulder pan |
| 10 | `left_joint_2.pos` | `left_` prefix removed, sent to left arm as `joint_2.pos` | deg | relative | Left shoulder lift |
| 11 | `left_joint_3.pos` | `left_` prefix removed, sent to left arm as `joint_3.pos` | deg | relative | Left shoulder rotation |
| 12 | `left_joint_4.pos` | `left_` prefix removed, sent to left arm as `joint_4.pos` | deg | relative | Left elbow flex |
| 13 | `left_joint_5.pos` | `left_` prefix removed, sent to left arm as `joint_5.pos` | deg | relative | Left wrist roll |
| 14 | `left_joint_6.pos` | `left_` prefix removed, sent to left arm as `joint_6.pos` | deg | relative | Left wrist pitch |
| 15 | `left_joint_7.pos` | `left_` prefix removed, sent to left arm as `joint_7.pos` | deg | relative | Left wrist rotation |
| 16 | `left_gripper.pos` | `left_` prefix removed, sent to left arm as `gripper.pos` | deg | absolute | Excluded from relative conversion; default side limit `[-65, 0]` |

## Camera Matrix

| Policy/Dataset Key | Dataset Shape | Policy Config Shape | Required Robot Camera Key | Compatibility Notes |
| --- | --- | --- | --- | --- |
| `observation.images.left_wrist` | `[720, 1280, 3]` | `[3, 720, 1280]` | `left_wrist` | Must physically be the left wrist view; metadata does not provide serial/orientation |
| `observation.images.right_wrist` | `[720, 1280, 3]` | `[3, 720, 1280]` | `right_wrist` | Must physically be the right wrist view; metadata does not provide serial/orientation |
| `observation.images.base` | `[480, 640, 3]` | `[3, 480, 640]` | `base` | Must physically be the base/third-person view |

`BiOpenArmFollower` does not prefix camera keys. The configured cameras must already use these names, or rollout must pass a `rename_map`.

## Processor Compatibility

| Stage | Chain | Compatibility Requirement |
| --- | --- | --- |
| Preprocess | rename -> batch -> relative action -> normalize -> PI05 state prompt -> tokenizer -> device | Needs state vector in the exact 16-key order above; gripper names must contain `gripper` so they stay absolute |
| Model | PI05 action chunk, `chunk_size=30`, `n_action_steps=30` | Needs `model.safetensors` and processor state safetensors before real inference |
| Postprocess | unnormalize -> absolute action -> CPU | Needs the paired relative step to have cached the current state before postprocessing |
| Rollout inference | RTC required | Sync inference is rejected for enabled relative-action policies |

## Host/Runtime Compatibility

| Question | Metadata-Only Answer | Blocker |
| --- | --- | --- |
| Can local `BiOpenArmFollower` key order match the policy? | Yes | Must instantiate with right/left configs whose motor dict order is unchanged |
| Can camera keys match the policy? | Yes, if configured exactly | Need syhlabtop camera serial/name map and orientation check |
| Can gripper commands be interpreted safely? | Partially | Grippers are absolute degree targets; outliers above `0` will clip only if hardware limits are configured |
| Can `folding_latest` run through sync rollout? | No | Relative-action policies are blocked in `SyncInferenceEngine` |
| Can syhlabtop IO safely pair with a separate A6000 inference host using current rollout code? | No | Current rollout has no remote inference transport; RTC is local-thread async only |
| Can no-motion/shadow eval run now? | No | Current strategies call `send_action`; no audited no-send path exists yet |

## Minimum Pre-Shadow Checklist

1. Confirm exact syhlabtop camera mapping for `left_wrist`, `right_wrist`, and `base`.
2. Confirm CAN mapping: right arm config uses `side=right`; left arm config uses `side=left`.
3. Confirm calibration files and that gripper zero means closed for both arms.
4. Decide same-host vs remote inference architecture. Current code only supports same-process inference/hardware.
5. Add or use an audited no-send path before connecting hardware for shadow eval.
6. Disable any return-to-initial movement for shadow eval unless explicitly testing motion.
7. After allowed downloads, run an offline one-observation processor check with no robot actions:
   - load policy config and processor states
   - verify action tensor length 16
   - verify postprocessed action dict uses the exact order in this matrix
   - verify gripper dimensions are absolute and joint dimensions are relative-to-absolute restored
