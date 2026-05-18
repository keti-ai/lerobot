# a6000 D-10c postprocessor/RABC 진단

## 목적

D-8a `003000` continuation 실패 원인이 다음 중 무엇인지 식별한다.

- α: 입력 `003000` checkpoint 자체 결함
- β: D-8a continuation config 결함
- γ: gate/진단 코드 contract 결함

## 대상

| 이름 | 경로 |
|---|---|
| full_folding 003000 | `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_full_folding_relstats_chunk30_20260514/checkpoints/003000/pretrained_model` |
| D-8a 012000 | `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints/012000/pretrained_model` |
| level2 corrected 004000 | `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model` |

## 003000 checkpoint 메타

- `use_relative_actions=true`
- `relative_exclude_joints=["gripper"]`
- `policy_preprocessor.json`: `delta_actions_processor` enabled
- `policy_postprocessor.json`: `unnormalizer_processor` 다음 `absolute_actions_processor` enabled
- `train_config.dataset.repo_id=lerobot/full_folding`
- `train_config.dataset.root=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/datasets/full_folding_relative_stats_chunk30`
- `train_config.sample_weighting.type=rabc`
- `train_config.sample_weighting.kappa=0.0265`
- `train_config.sample_weighting.progress_path=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/datasets/full_folding_relative_stats_chunk30/sarm_progress.parquet`
- top-level `use_rabc`, `rabc_kappa`, `rabc_progress_path` 는 없음

## Processor stats

수치만 보면 arm action quantile span이 수십 deg라서 절대 stats처럼 보일 수 있다. 하지만 level2 corrected 004000도 같은 scale이고, relstats-aware gate가 full_folding relstats dataset과 정확히 일치한다고 판정했다.

| checkpoint | q01 arm min/max | q99 arm min/max | span arm min/max/mean | worst span |
|---|---:|---:|---:|---|
| full_folding 003000 | -43.296 / -12.167 | 12.887 / 49.178 | 25.959 / 85.985 / 53.938 | `right_joint_4.pos` 85.985 |
| level2 corrected 004000 | -42.691 / -8.056 | 13.253 / 39.028 | 24.557 / 79.839 / 51.328 | `right_joint_4.pos` 79.839 |
| D-8a 012000 | -43.296 / -12.167 | 12.887 / 49.178 | 25.959 / 85.985 / 53.938 | `right_joint_4.pos` 85.985 |

### 003000 vs D-8a 012000

Postprocessor quantile diff:

- `action.q01` max_abs_diff = 0.0
- `action.q99` max_abs_diff = 0.0

판정: D-8a continuation 이 postprocessor stats를 새로 reset하거나 변형한 증거는 없다.

## 기존 relstats-aware gate

`full_folding_recipe_gate_003000_relstatsaware_20260515.json` 기준:

- `rabc_recorded_in_sample_weighting`: PASS
- `postprocessor_action_stats_match_relstats_dataset`: PASS
- `max_q01_diff`: 0.0
- `max_q99_diff`: 0.0
- `relstats_marker_records_14_relative_dims`: PASS

`full_folding_dataset_replay_003000.json` 도 이 relstats-aware gate를 source로 기록한다.

## D-8a gate false-negative 원인

D-8a gate에 사용한 현재 `stage29_candidate_recipe_gate.py` 는 `stage22_dataset_replay_and_ablation.py` 의 `validate_folding_recipe` 를 호출한다. 여기에는 relstats-aware contract와 맞지 않는 두 가지 가정이 있다.

1. `stage22_dataset_replay_and_ablation.py:205` 에서 `rel = action_arr - state_arr` 를 계산한다. 그러나 `full_folding_relative_stats_chunk30` 의 `action` 은 이미 arm 14D가 relative target이고 gripper만 absolute excluded dim이다. 여기서 state를 다시 빼면 fake relative stats가 만들어진다.
2. `stage22_dataset_replay_and_ablation.py:293` 은 top-level `use_rabc` 를 기대한다. 현재 train_config는 RABC를 `sample_weighting` 아래에 기록한다. 기존 relstats-aware gate는 이 위치를 PASS로 인정한다.

이 때문에 D-8a `001000`~`012000` current gate 결과는 다음 false-negative를 냈다.

- `rabc_recorded_in_train_config`: FAIL
- `postprocessor_action_stats_are_relative_for_arm_joints`: FAIL
- rel_q01_err 40.268 deg, rel_q99_err 39.561 deg, span_ratio 12.932

이 수치는 checkpoint stats 결함 확정값이 아니라, relstats dataset action을 다시 `action - state` 로 해석한 gate mismatch의 결과로 본다.

## Continuation command 검토

`d8a_full_folding_continue_003000_torch27_pyav_command_20260515.md` 는 config file 실행 방식이다.

- input checkpoint: full_folding `003000`
- config: `d8a_full_folding_continue_003000_torch27_pyav_config_20260515.json`
- `dataset.video_backend=pyav`
- `policy.pretrained_path` 는 full_folding `003000`
- 별도 processor reset 인자는 없음
- RABC는 CLI 인자가 아니라 config/train_config의 `sample_weighting` 로 기록됨

## 결론

case: γ

정확한 표현은 “학습 코드 결함 확정”이 아니라 “gate/진단 코드가 relstats-aware contract를 반영하지 못한 결함”이다. 현재 증거로는 full_folding `003000` 자체 결함(α) 또는 D-8a continuation config 결함(β)으로 판정하지 않는다.

## 다음 행동

1. D-8a `001000`~`012000` 에 대해 relstats-aware recipe gate를 다시 적용한다.
2. PASS checkpoint에 대해서만 relstats-aware dataset replay gate를 실행한다.
3. 그 결과 전까지 D-8a 산출물은 deploy 후보로 표기하지 않는다.
4. D-8a/D-8b 재학습 재시작은 위 gate/replay 재판정 뒤 결정한다.
