# OpenArm 폴딩 - 현재 상태

**마지막 갱신**: 2026-05-15

## 트랙 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| A | UNBLOCKED | Track D 결과 보고 messy shirt 실행 |
| B | DECISION_PENDING | D-9 cuDNN 환경 결정 후 D-8a/D-8b 진행 여부 결정 |
| C | COMPLETE | ckpt 002000/003000/004000 모두 replay FAIL, full_folding deploy 후보 없음 |
| D | WAITING_FOR_SYHLABTOP_TOOLS | syhlabtop에서 현역 도구 복구 후 read-only audit 재시도 |

## 미해결 이슈

1. full_folding replay FAIL 원인: ckpt 002000/003000/004000 모두 relstats-aware replay FAIL. 단순 checkpoint selection으로 해결되지 않으며, underfit 추가 학습(D-8a) 또는 fold-only 재학습(D-8b) 결정 필요
2. base 카메라 FOV/scale 불일치
3. left_joint_{4,5,6,7} + 양 gripper 의 축 sign 미검증
4. 지시문 기준 현역 md 8개 중 현재 작업트리에 `README.md`만 존재함
5. 지시문 기준 현역 py 7개 중 현재 작업트리에 5개만 존재하며 `a6000_live_policy_server.py`는 untracked 상태임
6. `audits/openarm_folding/tensorboard_remote_viewing_2026-05-14.md`가 잔류 목록에 없는 예외 파일로 남아 있음
7. `visual_dataset_alignment_and_full_folding_retrain_plan_2026-05-14.md`가 현재 작업트리에 없어 Current Situation 갱신을 수행할 수 없음
8. D-9 cuDNN 환경: A6000 torch `2.11.0+cu128` / CUDA `12.8` / cuDNN `91900` / driver `570.133.20`에서 cuDNN enabled Conv2d가 `CUDNN_STATUS_NOT_INITIALIZED`로 실패함. 사용자 결정 전 환경 변경 금지, cuDNN 우회 학습 금지
9. Track D1 실행 불가: 현재 호스트는 `ketiserver`이고 `/home/syhlabtop/workspace/lerobot` 및 `audits/openarm_folding/openarm_limit_axis_audit.py`가 없음

## 다음 N개 작업 (우선순위 순)

1. D-9: 사용자 결정 - torch 2.7.x + 호환 cuDNN 새 venv / torch 2.11.0 cuDNN 정비 / Docker 격리 중 선택
2. D-9 후속: 선택한 환경에서 cuDNN enabled Conv2d와 짧은 train smoke 검증
3. D-8a: 003000에서 8000/16000 step 추가 학습으로 underfit 가설 검증
4. D-8b: fold-only subset 생성 및 별도 재학습 여부 결정
5. Track D: syhlabtop repo와 현역 도구(`openarm_limit_axis_audit.py`, `syhlabtop_live_policy_input_viewer.py`) 복구/확인

## Track C 결과

- ckpt 002000: recipe PASS, replay FAIL. Ratio `0.220-0.320`, raw normalized max error `0.433`, max global delta `4.799 deg`.
- ckpt 003000: recipe PASS, replay FAIL. Ratio `0.142-0.348`, raw normalized max error `0.402`, max global delta `2.026 deg`.
- ckpt 004000: recipe PASS, replay FAIL. Ratio `0.128-0.282`, raw normalized max error `0.413`, max global delta `2.086 deg`.
- 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/full_folding_dataset_replay_{002000,003000}.{md,json}`.
- 결론: 002000은 ratio가 가장 높지만 raw normalized error가 가장 크고 gate는 FAIL. 002000/003000/004000 중 deploy candidate 없음.

## D-9 cuDNN 환경 리뷰

- 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/cudnn_env_review_20260515_140817.md`
- 확인 환경: ketiserver, RTX A6000 x4, driver `570.133.20`, torch `2.11.0+cu128`, CUDA `12.8`, cuDNN `91900`.
- 결과: cuDNN enabled Conv2d는 `CUDNN_STATUS_NOT_INITIALIZED`로 실패하고, `torch.backends.cudnn.enabled=False`에서는 같은 Conv2d가 통과한다.
- 판정: D-8 추가 학습은 환경 결정 전 시작 금지. 우회 설정은 학습에 사용하지 않는다.
- 선택지: (i) torch 2.7.x + 호환 cuDNN 새 venv, (ii) torch 2.11.0 유지 + cuDNN 별도 정비, (iii) Docker 격리.

## 참조

SSOT: `docs/PLAN.md`
운영 룰: `AGENTS.md`
운영 문서: `audits/openarm_folding/README.md`
