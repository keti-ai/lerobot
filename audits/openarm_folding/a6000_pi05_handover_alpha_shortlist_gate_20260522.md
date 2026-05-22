# alpha shortlist gate (PI0.5 handover, 5 ckpt)

작성일: 2026-05-22

alpha 학습: commit `d3bf4f9a`, run `pi05_handover_v0_alpha_20260522_002624`

dataset: `KETI-IRRC/openarm_handover_v0_20260521_202117`

shortlist: step 10000 / 12000 / 14000 / 16000 / 18000

raw 산출물:

- `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624/audits/recipe_gate_step_*.{md,json}`
- `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624/audits/replay_gate_step_*.{md,json}`

주의: 현재 `stage22_dataset_replay_and_ablation.py`는 `--video-backend pyav`를 받지 않아 replay는 `ffmpeg` backend로 실행했다. recipe gate는 별도 실행했으므로 replay 정량값은 `--no-recipe-gate`로 산출했다.

## 결과 표

| step | recipe | replay | ratio range | raw max err | max delta deg | deploy? |
|---|---|---|---:|---:|---:|---|
| 010000 | FAIL | FAIL | 0.084-1.878 | 2.504 | 2.665 | REJECTED |
| 012000 | FAIL | FAIL | 0.064-1.921 | 2.448 | 3.217 | REJECTED |
| 014000 | FAIL | FAIL | 0.082-1.780 | 2.305 | 2.920 | REJECTED |
| 016000 | FAIL | FAIL | 0.080-2.096 | 2.186 | 2.773 | REJECTED |
| 018000 | FAIL | FAIL | 0.070-1.926 | 2.185 | 2.579 | REJECTED |

## Recipe gate 공통 실패

5개 checkpoint 모두 동일한 recipe failure를 보였다.

- `dataset_robot_type_openarms_follower`
- `camera_keys_and_shapes_match_space_recipe`
- `rabc_recorded_in_train_config`
- `postprocessor_action_stats_are_relative_for_arm_joints`

postprocessor relative stats 요약도 전 step 동일했다.

- `rel_q01_err`: 50.189 deg
- `rel_q99_err`: 98.529 deg
- `span_ratio`: 10.162
- `worst_span`: `right_joint_1.pos`

## Replay gate 분석

5개 checkpoint 모두 replay failure를 보였다.

- `model_mean_abs_delta_same_order_as_recorded`: FAIL
- `raw_normalized_output_close_to_recorded_relative_arm_target`: FAIL
- `no_60_70deg_abnormal_delta_on_watched_or_global_joints`: PASS
- `gripper_excluded_from_relative_conversion`: PASS

초반 frame 0-2에서 recorded motion 대비 모델 delta가 너무 작다. 가장 낮은 ratio는 `012000`의 0.064이고, 가장 높은 max ratio는 `016000`의 2.096이다. raw normalized error는 모든 step에서 threshold 0.25를 크게 초과한다.

## 정량 분석

- 최저 raw err: step `018000` (2.185), step `016000` (2.186)와 거의 동일
- 최고 ratio: step `016000` (max ratio 2.096)
- 가장 균형 잡힌 진단 후보: step `016000`

`016000`은 raw error가 두 번째로 낮고 max ratio가 가장 높으며, max delta도 2.773 deg로 비정상 60-70 deg delta와는 거리가 있다. 하지만 recipe와 replay가 모두 FAIL이므로 deploy 후보는 아니다.

## 권장

다음 단계로 갈 deploy 후보는 없다.

- 첫 라이브 후보: 없음
- backup 후보: 없음
- 전체 판정: `REJECTED`

다음 행동 후보:

- beta 학습으로 넘어가기 전에 processor/action representation mismatch 원인을 먼저 분리한다.
- handover dataset이 20 episode 규모라서, 더 많은 episode 또는 더 균일한 초기 motion 구간이 포함된 dataset 추가 수집을 검토한다.
- 현재 alpha shortlist 중 live serving 전환 또는 HF push는 보류한다.
