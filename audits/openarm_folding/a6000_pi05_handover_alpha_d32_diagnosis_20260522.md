# D-32 alpha postprocessor/action representation diagnosis

작성일: 2026-05-22

대상 checkpoint:

`/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624/checkpoints/016000/pretrained_model`

비교 기준:

`/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`

참고: 직전 shortlist gate에서 raw max err는 `018000=2.185`, `016000=2.186`으로 사실상 동률이다. D-32는 max ratio와 균형 기준에서 가장 나은 진단 후보인 `016000`을 기준으로 진행했다.

## 1. train_config 요약

`016000/pretrained_model/train_config.json`의 핵심 값:

| key | value |
|---|---|
| `dataset.repo_id` | `KETI-IRRC/openarm_handover_v0_20260521_202117` |
| `dataset.video_backend` | `pyav` |
| `dataset.root` | `null` |
| `dataset.use_imagenet_stats` | `true` |
| `policy.type` | `pi05` |
| `policy.path` | `null` |
| `policy.use_relative_actions` | `true` |
| `policy.relative_action_chunk_size` | `null` |
| `policy.relative_exclude_joints` | `["gripper"]` |
| `policy.scheduler_decay_steps` | `20000` |
| `output_dir` | `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624` |

해석:

- alpha 학습 config는 policy를 relative-action mode로 설정했다.
- 하지만 dataset root는 checkpoint config 안에 고정되어 있지 않고, dataset 자체는 relstats marker 없는 HF dataset으로 로드된다.

## 2. processor 파일

`016000/pretrained_model/` 파일 목록:

- `config.json`
- `model.safetensors`
- `policy_postprocessor.json`
- `policy_postprocessor_step_0_unnormalizer_processor.safetensors`
- `policy_preprocessor.json`
- `policy_preprocessor_step_3_normalizer_processor.safetensors`
- `train_config.json`

level2 corrected `004000`도 동일한 processor 파일 구조를 가진다.

## 3. processor stats 비교

아래 값은 arm 14D만 기준으로 min/max를 요약했다. gripper 2D는 제외했다.

| checkpoint | stat | arm min | arm max | 해석 |
|---|---|---:|---:|---|
| alpha `016000` | `action.mean` | -19.303 | 55.116 | zero-centered relative 분포가 아님 |
| alpha `016000` | `action.std` | 8.860 | 41.828 | absolute pose 범위에 가까운 큰 분산 |
| alpha `016000` | `action.q01` | -53.697 | 3.526 | absolute degree target 범위 |
| alpha `016000` | `action.q99` | 0.733 | 113.035 | absolute degree target 범위 |
| alpha `016000` | `observation.state.q01` | -52.827 | 4.876 | action q01과 매우 가까움 |
| alpha `016000` | `observation.state.q99` | 0.636 | 111.349 | action q99와 매우 가까움 |
| level2 `004000` | `action.mean` | -4.263 | 4.758 | zero-centered relative 분포 |
| level2 `004000` | `action.std` | 3.882 | 12.683 | relative delta에 가까움 |
| level2 `004000` | `action.q01` | -42.691 | -8.056 | relative delta 분포 |
| level2 `004000` | `action.q99` | 13.253 | 39.028 | relative delta 분포 |
| level2 `004000` | `observation.state.q01` | -72.966 | 25.286 | absolute state 범위 |
| level2 `004000` | `observation.state.q99` | -1.042 | 115.841 | absolute state 범위 |

alpha `016000`의 action stats는 observation.state stats와 거의 같은 absolute degree 범위를 가진다. 반대로 level2 corrected `004000`의 action stats는 state와 분리된 zero-centered relative delta 분포에 가깝다.

따라서 alpha `016000` processor는 relative action용 postprocessor가 아니라 handover dataset의 absolute action 분포를 학습한 것으로 보인다.

## 4. handover dataset action representation

`LeRobotDataset('KETI-IRRC/openarm_handover_v0_20260521_202117', video_backend='pyav')` 확인 결과:

| field | value |
|---|---|
| episodes | 20 |
| frames | 17944 |
| fps | 30 |
| action feature | `shape=(16,)`, 16D OpenArm joint/gripper names |

샘플:

```text
row0 action:
[ -0.308  -1.802  12.791  -1.275  -6.286  -3.560  19.560  -9.463
   4.527  -0.835 -12.000  16.747  10.242  -9.275  -2.242  -4.260]

row1 - row0:
[ 0.000  0.000  0.088  0.000  0.088  0.000  0.000  0.000
  0.000 -0.176  0.000  0.000  0.000  0.000  0.000  0.000]
```

row0 하나만 보면 작은 값도 포함되어 있어 모호할 수 있지만, 전체 processor stats 기준으로는 action이 state와 같은 absolute degree target 범위를 가진다. `row1-row0`은 adjacent-frame absolute target 차분일 뿐, dataset action row 자체가 relative라는 증거가 아니다.

## 5. gate auto 판정

`recipe_gate_step_016000.json`:

| field | value |
|---|---|
| `action_is_relative` | `false` |
| `action_is_relative_source` | `no relstats marker detected` |
| `deploy_candidate` | `false` |

recipe failed checks:

- `dataset_robot_type_openarms_follower`
- `camera_keys_and_shapes_match_space_recipe`
- `rabc_recorded_in_train_config`
- `postprocessor_action_stats_are_relative_for_arm_joints`

relative stats mismatch:

- `max_post_vs_relative_q01_error_deg`: 50.189
- `max_post_vs_relative_q99_error_deg`: 98.529
- `max_arm_span_ratio_postprocessor_over_sampled_relative`: 10.162
- `worst_span_ratio_key`: `right_joint_1.pos`

`replay_gate_step_016000.json`:

| field | value |
|---|---|
| `action_is_relative` | `false` |
| `action_is_relative_source` | `no relstats marker detected` |
| `replay_action_is_relative` | `false` |
| `replay_action_is_relative_source` | `no relative action-row marker detected; treating parquet action rows as absolute targets` |
| replay summary | FAIL |

replay failed checks:

- `model_mean_abs_delta_same_order_as_recorded`
- `raw_normalized_output_close_to_recorded_relative_arm_target`

## 6. Case 판정

판정: **case alpha (B-1)**.

근거:

- train_config는 `policy.use_relative_actions=true`.
- handover dataset은 relstats marker가 없고, gate auto도 `action_is_relative=false`로 판정했다.
- alpha `016000` action processor stats는 level2 corrected relative-action stats가 아니라 absolute degree/state 범위와 일치한다.
- replay에서도 absolute action rows로 판정했으며, relative target 기준 raw error가 크게 실패한다.

기각:

- case beta (B-2): train_config와 dataset이 모두 absolute인 경우가 아니다. train_config는 relative action mode다.
- case gamma (D-10c 재발): dataset이 relstats 형태인데 gate가 중복 차분한 상황이 아니다. gate auto는 relstats marker를 찾지 못했고 absolute rows로 처리했다.

## 7. 결론과 권장

alpha shortlist의 `REJECTED` 판정은 정당하다. `016000`은 shortlist 내에서 least-bad 진단 후보일 수는 있지만, live deploy 후보로 올리면 안 된다.

권장 다음 행동:

1. beta 학습으로 진행하기 전에 handover dataset을 명시적으로 relstats/relative-action dataset으로 변환할지 결정한다.
2. 또는 absolute-action 학습으로 갈 경우 `use_relative_actions=false`와 그에 맞는 processor/action contract로 새 실험을 분리한다.
3. 현재 alpha checkpoint의 HF push, serving 전환, live feasibility 투입은 보류한다.

## 8. Safety

- 모션 실행 없음.
- 학습 시작 없음.
- serving 재기동 없음.
- checkpoint 변경 없음.
- raw dataset/video shard 변경 없음.
