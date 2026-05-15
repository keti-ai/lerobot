# OpenArm 폴딩 재학습 - 작업 플랜 (SSOT)

## 1. 최종 목표

OpenArm 하드웨어에서 공개 데이터셋 `level2_final_quality3_t_0_hil_data_c`와
`lerobot/full_folding` 계열 데이터를 재학습한 정책을 운영하여, 현장에서 옷
폴딩 태스크를 안정적으로 수행하는 것이 최종 목표다. 현재 운영 후보는 level2
corrected checkpoint이며, full_folding 004000은 replay gate FAIL로 배포 후보가
아니다.

## 2. 시스템 아키텍처

- 두 머신: syhlabtop (RealSense + DamiaoMotorsBus) <-> A6000 (학습/서빙)
- HTTP 인터페이스: 8766 `/predict_live`, `/health`
- 16D action contract: right arm 7 + right gripper + left arm 7 + left gripper,
  degrees, gripper `[-65, 0]`
- 액추에이터 path: `DamiaoMotorsBus.connect(handshake=False)` + guarded MIT batch
- 카메라: left_wrist `315122270766` / right_wrist `230322273311` / base `213622075840`

## 3. 파이프라인 단계별 로드맵

| 단계 | 산출물 | 상태 | 비고 |
|---|---|---|---|
| D1 | level2 데이터셋 및 corrected checkpoint 입력 확인 | DONE | Track A live rollout 입력 기준 |
| D2 | full_folding 데이터셋 학습 입력 확인 | DONE | Track B 재학습 완료 |
| P1 | syhlabtop live policy 입력/스냅샷 path | READY | 실제 모션 전 approval envelope 필수 |
| P2 | A6000 HTTP serving path | READY | port 8766, HF offline env 필수 |
| T1 | level2 corrected checkpoint 004000 | READY | 현재 A6000 serving 대상 |
| T2 | full_folding checkpoint 004000 | COMPLETE | recipe PASS, replay FAIL |
| G1 | action contract gate | PASS | 16D degrees/gripper 계약 기준 |
| G2 | processor/checkpoint contract gate | PASS | 기존 Stage23-24 기록 기준 |
| G3 | recipe gate | PASS | full_folding 004000 recipe gate PASS |
| G4 | dataset replay gate | FAIL | delta ratio 0.128-0.282, threshold 0.25-4.0 |
| G5 | full_folding ckpt 002000 replay gate | FAIL | Ratio 0.220-0.320, raw normalized max error 0.433 |
| G6 | full_folding ckpt 003000 replay gate | FAIL | Ratio 0.142-0.348, raw normalized max error 0.402 |
| S1 | A6000 live policy server | READY | `a6000_live_policy_server.py`, offline env 필요 |
| S2 | snapshot policy server/client | READY | no-send/snapshot 검증용 |
| R1 | Track A first messy shirt rollout | WAITING FOR D | Track D 축/FOV 확인 후 operator approval |
| R2 | left wrist 축 sign probe | NOT STARTED | Damiao persistent setting 변경 금지 |
| R3 | base camera FOV/scale alignment | NOT STARTED | Track A 전 확인 필요 |
| R4 | full_folding ckpt selection decision | COMPLETE | 002000/003000/004000 모두 replay FAIL, deploy 후보 없음 |
| R5 | deploy candidate 선언 | NOT STARTED | replay gate PASS 전 금지 |

## 4. 트랙 정의 + 현재 우선순위

P0는 안전 불변조건 유지다. `OpenArmFollower.connect()`, `send_action()`,
`lerobot-rollout` 실제 path, Stage35-40 packet 재사용, Damiao persistent setting
변경을 금지하고 모든 실제 모션은 `syhlabtop_live_guarded_rollout.py` approval
envelope를 먼저 통과해야 한다.

P1은 A6000 Track B 후속 작업의 D-9 cuDNN 환경 결정이다. full_folding 추가
학습은 cuDNN enabled Conv2d가 통과하는 환경에서만 시작한다.

P2는 Track D다. left wrist 축 sign probe와 base 카메라 정렬이 아직 시작되지
않았으므로, Track A 첫 messy shirt 실행 전의 직접 선행조건이다.

P3은 Track A다. syhlabtop level2 라이브 롤아웃은 UNBLOCKED 상태지만 Track D
결과를 본 뒤 operator approval로 첫 messy shirt 실행을 진행한다.

P4는 Track C 후속 판정이다. full_folding 002000/003000/004000은 모두 replay
FAIL이므로 단순 checkpoint selection으로는 배포 후보를 만들 수 없고, underfit
추가 학습 또는 데이터/recipe 재설계 결정이 필요하다.

Track A: syhlabtop level2 라이브 롤아웃. 상태는 UNBLOCKED, 첫 messy shirt 실행
대기.

Track B: full_folding 재학습. 초기 004000 학습은 COMPLETE이나 002000/003000/004000
모두 replay gate FAIL이므로 deploy candidate가 없다. 추가 학습(D-8a) 또는
fold-only 재학습(D-8b)은 D-9 cuDNN 환경 결정 후에만 시작한다.

Track C: full_folding ckpt 002000/003000 replay gate 비교. 상태는 완료. 002000,
003000, 004000 모두 relstats-aware replay gate FAIL이므로 full_folding deploy
candidate는 없다.

Track D: left wrist 축 probe + base 카메라 정렬. 상태는 미실행.

## 5. 결정 필요 항목

- D-1: full_folding replay FAIL 원인을 ckpt 002000/003000 비교로 underfit인지 checkpoint selection인지 결정해야 한다.
- D-2: full_folding 004000은 deploy candidate에서 제외하고, replay gate PASS checkpoint가 나올 때까지 배포 금지를 유지해야 한다.
- D-3: base 카메라 FOV/scale 불일치를 어떤 기준으로 정렬할지 결정해야 한다.
- D-4: left_joint_{4,5,6,7}와 양 gripper 축 sign을 물리 probe로 확인해야 한다.
- D-5: Track D 결과 확인 후 Track A messy shirt 첫 live rollout go/no-go를 operator approval로 결정해야 한다.
- D-6: A6000 server는 `HF_HOME`, `HF_HUB_CACHE`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`을 유지한 offline serving으로만 운용해야 한다.
- D-7: 현재 작업트리에는 지시문 기준 현역 md/py 일부가 존재하지 않으므로 복구 또는 별도 소스 확인이 필요하다.
- D-8: full_folding 002000/003000/004000이 모두 replay FAIL이므로, 다음 full_folding 작업은 003000에서 8000/16000 step 추가 학습(D-8a)인지 fold-only subset 재학습(D-8b)인지 결정해야 한다. D-9가 해결될 때까지 학습 시작 금지.
- D-9: A6000 full_folding venv는 torch `2.11.0+cu128`, CUDA `12.8`, cuDNN `91900`, driver `570.133.20` 환경이며 cuDNN enabled Conv2d가 `CUDNN_STATUS_NOT_INITIALIZED`로 실패한다. `torch.backends.cudnn.enabled=False`는 추론 산출물 생성에만 사용했고 학습에는 사용하지 않는다. 선택지는 (i) torch 2.7.x + 호환 cuDNN 새 venv, (ii) torch 2.11.0 유지 + cuDNN 별도 정비, (iii) Docker 격리이며, 사용자 결정 필요. 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/cudnn_env_review_20260515_140817.md`.

## 6. 현역 참조 파일

- `audits/openarm_folding/README.md` - 운영 문서 진입점.
- `audits/openarm_folding/trackA_level2_live_test_plan_2026-05-14.md` - Track A level2 live test plan. 현재 작업트리 미존재.
- `audits/openarm_folding/visual_dataset_alignment_and_full_folding_retrain_plan_2026-05-14.md` - visual alignment 및 full_folding retrain plan. 현재 작업트리 미존재.
- `audits/openarm_folding/openpi_lerobot_live_pipeline_check_2026-05-14.md` - OpenPI/LeRobot live pipeline 점검. 현재 작업트리 미존재.
- `audits/openarm_folding/damiao_setup_axis_alignment_review_2026-05-14.md` - Damiao setup 및 축 정렬 리뷰. 현재 작업트리 미존재.
- `audits/openarm_folding/limit_axis_physical_check_plan_2026-05-14.md` - limit/axis 물리 확인 계획. 현재 작업트리 미존재.
- `audits/openarm_folding/openarm_follower_j4_5cm_fabrication_order_2026-05-14.md` - OpenArm follower J4 5cm 제작 주문 기록. 현재 작업트리 미존재.
- `audits/openarm_folding/live_deploy_technique_applicability_2026-05-14.md` - live deploy technique 적용성 검토. 현재 작업트리 미존재.
- `audits/openarm_folding/syhlabtop_live_guarded_rollout.py` - live guarded rollout approval envelope 도구. 현재 작업트리 미존재.
- `audits/openarm_folding/syhlabtop_live_policy_input_viewer.py` - live policy 입력 확인 도구. 현재 작업트리 미존재.
- `audits/openarm_folding/syhlabtop_snapshot_policy_client.py` - snapshot policy client.
- `audits/openarm_folding/a6000_live_policy_server.py` - A6000 live policy server. 현재 작업트리에서는 untracked 상태.
- `audits/openarm_folding/a6000_snapshot_policy_server.py` - A6000 snapshot policy server.
- `audits/openarm_folding/openarm_limit_axis_audit.py` - OpenArm limit/axis read-only audit. 현재 작업트리 미존재.
- `audits/openarm_folding/stage22_dataset_replay_and_ablation.py` - 이름은 stage*지만 현역인 dataset replay/ablation 도구.
- `audits/openarm_folding/stage29_candidate_recipe_gate.py` - 이름은 stage*지만 현역인 candidate recipe gate 도구.
- `audits/openarm_folding/run_rsusb_py312.sh` - RealSense/rsusb Python 3.12 실행 wrapper.
- `AGENTS.md` - 작업 룰.
- `docs/STATUS.md` - 변동 상태.

## 7. 변경 이력

- 2026-05-15: SSOT 도입, `_archive` 분리, `AGENTS.md` OpenArm 섹션 추가.
