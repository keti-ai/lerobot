# OpenArm 폴딩 - 현재 상태

**마지막 갱신**: 2026-05-15

## 트랙 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| A | UNBLOCKED | Track D 결과 보고 messy shirt 실행 |
| B | COMPLETE | replay FAIL, deploy 후보 아님 |
| C | COMPLETE | ckpt 002000/003000/004000 모두 replay FAIL, full_folding deploy 후보 없음 |
| D | NOT STARTED | 축 probe + base 카메라 정렬 |

## 미해결 이슈

1. full_folding replay FAIL 원인: ckpt 002000/003000/004000 모두 relstats-aware replay FAIL. 단순 checkpoint selection으로 해결되지 않으며, underfit/학습 recipe/gate sample 재검토 필요
2. base 카메라 FOV/scale 불일치
3. left_joint_{4,5,6,7} + 양 gripper 의 축 sign 미검증
4. 지시문 기준 현역 md 8개 중 현재 작업트리에 `README.md`만 존재함
5. 지시문 기준 현역 py 7개 중 현재 작업트리에 5개만 존재하며 `a6000_live_policy_server.py`는 untracked 상태임
6. `audits/openarm_folding/tensorboard_remote_viewing_2026-05-14.md`가 잔류 목록에 없는 예외 파일로 남아 있음
7. `visual_dataset_alignment_and_full_folding_retrain_plan_2026-05-14.md`가 현재 작업트리에 없어 Current Situation 갱신을 수행할 수 없음
8. Track C replay 실행 환경: torch `2.11.0+cu128`에서 cuDNN Conv2d가 `CUDNN_STATUS_NOT_INITIALIZED`로 실패함. `torch.backends.cudnn.enabled=False` 우회로 002000/003000 산출물 생성 완료

## 다음 N개 작업 (우선순위 순)

1. Track D: `openarm_limit_axis_audit.py` read-only 재실행 (현 readback 확인)
2. Track D: base 카메라 alignment 확인 (read-only)
3. Track D: 운영자 입회 하 left_joint_4 +1deg/-1deg 축 probe
4. Track A: messy shirt 시나리오 첫 라이브 롤아웃 draft envelope 생성 (operator approval 전 execute 금지)
5. Track B/C: full_folding 재학습 recipe 또는 replay gate sample 재검토 결정

## Track C 결과

- ckpt 002000: recipe PASS, replay FAIL. Ratio `0.220-0.320`, raw normalized max error `0.433`, max global delta `4.799 deg`.
- ckpt 003000: recipe PASS, replay FAIL. Ratio `0.142-0.348`, raw normalized max error `0.402`, max global delta `2.026 deg`.
- ckpt 004000: recipe PASS, replay FAIL. Ratio `0.128-0.282`, raw normalized max error `0.413`, max global delta `2.086 deg`.
- 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/full_folding_dataset_replay_{002000,003000}.{md,json}`.
- 결론: 002000은 ratio가 가장 높지만 raw normalized error가 가장 크고 gate는 FAIL. 002000/003000/004000 중 deploy candidate 없음.

## 참조

SSOT: `docs/PLAN.md`
운영 룰: `AGENTS.md`
운영 문서: `audits/openarm_folding/README.md`
