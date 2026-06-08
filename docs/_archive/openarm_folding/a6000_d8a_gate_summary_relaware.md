# a6000 D-8a relstats-aware gate 요약

## 범위

- 실행: `pi05_openarm_full_folding_continue003000_torch27_pyav_20260515`
- 입력 checkpoint: original full_folding `003000`
- 생성 checkpoint: `001000`~`012000`
- gate script: `audits/openarm_folding/stage29_candidate_recipe_gate.py`, `audits/openarm_folding/stage22_dataset_replay_and_ablation.py`
- 데이터셋: `lerobot/full_folding`
- dataset root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/datasets/full_folding_relative_stats_chunk30`
- 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/d8a_*_relaware_<step>.{md,json}`

## 회귀 확인

- level2 corrected `004000` recipe recheck: PASS
- level2 corrected `004000` replay recheck: PASS
- level2 auto 판정: stats relative=True, replay action rows relative=False
- 산출물:
  - `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/level2_004000_recipe_recheck_relaware_20260518.{md,json}`
  - `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/level2_004000_replay_recheck_relaware_20260518.{md,json}`

## 결과

| step | recipe (relaware) | replay (relaware) | ratio range | arm raw max err | deploy_candidate |
|---|---|---|---|---:|---|
| 001000 | PASS | FAIL | 0.191-0.378 | 0.439 | NO |
| 002000 | PASS | FAIL | 0.188-0.261 | 0.513 | NO |
| 003000 | PASS | FAIL | 0.227-0.393 | 0.455 | NO |
| 004000 | PASS | FAIL | 0.225-0.401 | 0.428 | NO |
| 005000 | PASS | FAIL | 0.125-0.406 | 0.398 | NO |
| 006000 | PASS | FAIL | 0.177-0.316 | 0.420 | NO |
| 007000 | PASS | FAIL | 0.225-0.341 | 0.402 | NO |
| 008000 | PASS | FAIL | 0.206-0.367 | 0.380 | NO |
| 009000 | PASS | FAIL | 0.149-0.380 | 0.361 | NO |
| 010000 | PASS | FAIL | 0.132-0.260 | 0.407 | NO |
| 011000 | PASS | FAIL | 0.160-0.468 | 0.372 | NO |
| 012000 | PASS | FAIL | 0.152-0.217 | 0.413 | NO |

## 판정

Relstats-aware recipe gate는 `001000`~`012000` 전부 PASS로 복구됐다. 기존 current gate의 recipe FAIL은 false-negative였다는 D-10c 판정과 일치한다.

하지만 replay gate는 12개 checkpoint 모두 FAIL이다. 실패 항목은 전부 다음 두 개다.

- `model_mean_abs_delta_same_order_as_recorded`
- `raw_normalized_output_close_to_recorded_relative_arm_target`

따라서 D-8a continuation `001000`~`012000` 중 deploy candidate는 없다.
