# a6000 D-8a gate 요약

## 범위

- 실행: `pi05_openarm_full_folding_continue003000_torch27_pyav_20260515`
- 입력 checkpoint: original full_folding `003000`
- 생성 checkpoint: `001000`~`012000`
- gate script: `audits/openarm_folding/stage29_candidate_recipe_gate.py`
- 데이터셋: `lerobot/full_folding`
- 데이터셋 root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/datasets/full_folding_relative_stats_chunk30`
- 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/d8a_recipe_gate_<step>.{md,json}`

## 결과

| step | recipe | replay | ratio | raw_err | failed checks | rel_q01_err_deg | rel_q99_err_deg | span_ratio | deploy_candidate |
|---|---|---|---|---|---|---:|---:|---:|---|
| 001000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 002000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 003000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 004000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 005000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 006000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 007000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 008000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 009000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 010000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 011000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |
| 012000 | FAIL | SKIPPED | n/a | n/a | `rabc_recorded_in_train_config`, `postprocessor_action_stats_are_relative_for_arm_joints` | 40.268 | 39.561 | 12.932 | NO |

## 판정

Recipe PASS checkpoint가 없으므로 replay gate는 실행하지 않았다.
`001000`~`012000` 모두 deploy candidate가 아니다.

2026-05-18 D-10c 진단에서 이 판정은 current `stage29/stage22` gate 기준의
false-negative 가능성이 높다고 재해석했다. 해당 gate는 relstats dataset의
already-relative action을 다시 `action - state` 로 처리하고, RABC 기록 위치도
현재 `sample_weighting` contract가 아닌 top-level `use_rabc` 로 기대한다. 따라서
이 표는 “current gate 결과”로만 보존하고, deploy 여부는 relstats-aware gate/replay
재판정 전까지 미정이다.

주요 실패는 두 가지다.

- `rabc_recorded_in_train_config`: 저장된 `train_config.json` 에 gate가 기대하는 RABC 기록이 없다.
- `postprocessor_action_stats_are_relative_for_arm_joints`: postprocessor action quantile이 full_folding relstats dataset의 relative action 통계와 맞지 않는다. 최대 q01 error 40.268 deg, q99 error 39.561 deg, span ratio 12.932, worst key `left_joint_4.pos`.

다음 선택은 사용자 결정 필요 항목으로 남긴다.
