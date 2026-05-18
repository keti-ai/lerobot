# a6000 D-8a deploy 후보 없음

## 결론

D-8a `003000` continuation 산출 checkpoint `001000`~`012000` 중 deploy 후보는 없다.

## 근거

- 학습은 `012000` checkpoint까지 저장한 뒤 step 12120 부근에서 `FrameTimestampError` 로 종료했다.
- Recipe gate는 `001000`~`012000` 모두 FAIL.
- Recipe PASS checkpoint가 없어 replay gate는 실행하지 않았다.
- 따라서 D-8a 산출물은 syhlabtop Track A serving 교체 후보가 아니다.

## 실패 요약

공통 실패 항목:

- `rabc_recorded_in_train_config`
- `postprocessor_action_stats_are_relative_for_arm_joints`

공통 수치:

- max postprocessor vs relative q01 error: 40.268 deg
- max postprocessor vs relative q99 error: 39.561 deg
- max arm span ratio: 12.932
- worst span key: `left_joint_4.pos`

## 산출물

- Gate 요약: `audits/openarm_folding/a6000_d8a_gate_summary.md`
- Recipe gate 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/d8a_recipe_gate_<step>.{md,json}`
- 실행 로그: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/d8a_run_20260515_163251.log`
- Checkpoints: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints/`

## 다음 결정

임의로 재시작하지 않는다. 다음 중 하나를 명시 결정해야 한다.

- D-8a를 recipe 보존 설정으로 재시도한다.
- D-8b fold-only subset 재학습으로 전환한다.
- full_folding continuation 중 postprocessor/RABC 기록이 왜 gate 밖으로 벗어났는지 먼저 조사한다.
