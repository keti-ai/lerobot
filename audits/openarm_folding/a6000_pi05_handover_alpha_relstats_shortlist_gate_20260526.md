# PI0.5 Handover alpha-prime relstats shortlist gate

마지막 갱신: 2026-05-26T15:45:37+09:00

## 요약

- source run: `pi05_handover_v0_alpha_relstats_20260522_213056`
- train result audit: `audits/openarm_folding/a6000_pi05_handover_alpha_relstats_result_20260523.md`
- dataset: `KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- dataset root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`
- shortlist: `022000`, `024000`, `026000`, `028000`, `030000`
- final decision: REJECTED, no deploy candidate from this shortlist

This is an offline A6000 gate/replay pass only. It did not connect to OpenArm, initialize motors, enable torque, zero joints, or send actions.

## Shortlist 선정

30k 학습은 22k 이후 low-loss plateau 에 들어갔다. 20k 이후 learning rate 는 `2.5e-06` floor 에 도달했고, 24k/26k/28k 구간에서 로그상 최저권 loss `0.011` 이 반복됐다. 그래서 final plateau 를 대표하는 5개 checkpoint 를 선택했다.

| step | aligned train loss | grad norm | lr |
| ---: | ---: | ---: | ---: |
| 022000 | 0.013 | 0.490 | 2.5e-06 |
| 024000 | 0.012 | 0.441 | 2.5e-06 |
| 026000 | 0.012 | 0.461 | 2.5e-06 |
| 028000 | 0.013 | 0.456 | 2.5e-06 |
| 030000 | 0.012 | 0.449 | 2.5e-06 |

## Recipe gate

Command family:

```bash
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python audits/openarm_folding/stage29_candidate_recipe_gate.py \
  --dataset-repo KETI-IRRC/openarm_handover_v0_relstats_chunk30 \
  --dataset-root /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30 \
  --candidate <checkpoint>/pretrained_model \
  --local-only \
  --action-is-relative true
```

Temporary raw outputs for this run were written under `/tmp/pi05_handover_alpha_relstats_stage29_recipe_gate_20260526.{json,md}`; the relevant values are copied into the table below.

| step | recipe | failed checks | rel q01 err | rel q99 err | span ratio |
| ---: | --- | --- | ---: | ---: | ---: |
| 022000 | FAIL | `dataset_robot_type_openarms_follower`, `camera_keys_and_shapes_match_space_recipe`, `rabc_recorded_in_train_config` | 0.000 | 0.000 | 1.000 |
| 024000 | FAIL | `dataset_robot_type_openarms_follower`, `camera_keys_and_shapes_match_space_recipe`, `rabc_recorded_in_train_config` | 0.000 | 0.000 | 1.000 |
| 026000 | FAIL | `dataset_robot_type_openarms_follower`, `camera_keys_and_shapes_match_space_recipe`, `rabc_recorded_in_train_config` | 0.000 | 0.000 | 1.000 |
| 028000 | FAIL | `dataset_robot_type_openarms_follower`, `camera_keys_and_shapes_match_space_recipe`, `rabc_recorded_in_train_config` | 0.000 | 0.000 | 1.000 |
| 030000 | FAIL | `dataset_robot_type_openarms_follower`, `camera_keys_and_shapes_match_space_recipe`, `rabc_recorded_in_train_config` | 0.000 | 0.000 | 1.000 |

Interpretation:

- D-32 의 original alpha failure 인 `postprocessor_action_stats_are_relative_for_arm_joints` 는 해결됐다.
- Remaining recipe failures come from the locked folding recipe, not from action relstats:
  - handover dataset metadata reports `bi_openarm_follower`, while the folding gate expects `openarms_follower`.
  - handover camera shapes/keys are not the locked folding recipe shape contract.
  - this alpha-prime run did not record RABC in `train_config.json`.
- Because the current gate policy requires all recipe checks to pass, no checkpoint may advance as a deploy candidate from recipe gate alone.

## Replay gate

The first replay attempt used `--video-backend pyav`, but this audit script only implements `cv2` and `ffmpeg` in `decode_dataset_images()`. The replay was rerun with `--video-backend ffmpeg`, matching the earlier alpha audit workaround.

Command family:

```bash
CUDA_VISIBLE_DEVICES=1 \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python audits/openarm_folding/stage22_dataset_replay_and_ablation.py \
  --dataset-repo KETI-IRRC/openarm_handover_v0_relstats_chunk30 \
  --dataset-root /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30 \
  --model-dir <checkpoint>/pretrained_model \
  --device cuda:0 \
  --video-backend ffmpeg \
  --action-is-relative true \
  --no-recipe-gate
```

Temporary raw outputs for this run were written under `/tmp/pi05_handover_alpha_relstats_replay_gate_<STEP>_20260526.{json,md}`; the relevant values are copied into the table below.

Note: `nvidia-smi` did not show a CUDA allocation during this Codex-launched replay run, so the policy appears to have completed via CPU fallback despite `--device cuda:0`. This affects runtime only; no robot IO was involved.

| step | replay | ratio range | arm raw max err | arm max delta deg | max delta deg | failed checks |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 022000 | FAIL | 0.041-0.141 | 4.943 | 5.356 | 47.811 | `model_mean_abs_delta_same_order_as_recorded`, `raw_normalized_output_close_to_recorded_relative_arm_target` |
| 024000 | FAIL | 0.038-0.105 | 4.861 | 2.840 | 50.742 | `model_mean_abs_delta_same_order_as_recorded`, `raw_normalized_output_close_to_recorded_relative_arm_target` |
| 026000 | FAIL | 0.029-0.096 | 4.838 | 2.994 | 16.214 | `model_mean_abs_delta_same_order_as_recorded`, `raw_normalized_output_close_to_recorded_relative_arm_target` |
| 028000 | FAIL | 0.035-0.129 | 4.824 | 4.712 | 67.237 | `model_mean_abs_delta_same_order_as_recorded`, `raw_normalized_output_close_to_recorded_relative_arm_target` |
| 030000 | FAIL | 0.031-0.097 | 4.844 | 3.503 | 57.711 | `model_mean_abs_delta_same_order_as_recorded`, `raw_normalized_output_close_to_recorded_relative_arm_target` |

Replay common passes:

- `recipe_gate_passed`: PASS because replay was intentionally run with `--no-recipe-gate`
- `no_60_70deg_abnormal_delta_on_watched_or_global_joints`: PASS
- `gripper_excluded_from_relative_conversion`: PASS

Replay common failures:

- `model_mean_abs_delta_same_order_as_recorded`: FAIL
- `raw_normalized_output_close_to_recorded_relative_arm_target`: FAIL

The model arm deltas remain much smaller than recorded relstats targets on episode 0 sample frames. Even the best max ratio is only `0.141`, and raw normalized target error remains about `4.8-4.9`.

## 판정

REJECTED.

No checkpoint from `022000`, `024000`, `026000`, `028000`, or `030000` is a deploy candidate.

Reasons:

- Recipe gate still fails the locked folding contract on robot type, camera shape recipe, and missing RABC record.
- Offline replay fails all five checkpoints on the same two quantitative checks.
- Relstats conversion fixed the action-stat mismatch from D-32, but it did not produce a checkpoint that follows recorded handover relstats target magnitudes in the current offline replay gate.

## 다음

- Do not switch 8766/8765 serving to these alpha-prime relstats checkpoints.
- Do not push policy checkpoints to HF as deploy candidates.
- Keep the M2b dataset HF repo for future experiments; dataset conversion itself remains valid.
- Next technical branch should diagnose why the model under-predicts recorded handover relative deltas despite matching relstats processor stats. Candidate directions:
  - inspect episode 0 replay target distribution vs later episodes,
  - test a handover-specific recipe gate rather than the folding-locked recipe,
  - add more handover episodes or introduce RABC/SARM for handover,
  - evaluate whether local replay thresholds should be task-specific before any live feasibility attempt.
