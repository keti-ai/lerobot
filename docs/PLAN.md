# OpenArm 폴딩 재학습 — 작업 플랜 (SSOT)

**마지막 갱신:** 2026-05-15  
**브랜치:** `audit/openarm-folding-baseline`  
**용도:** 이 레포에 들어오는 Codex/Claude 세션이 이 문서 하나만으로 다음 작업을 선택 가능하게 함.

---

## 1. 최종 목표

이 레포는 `lerobot` 포크다. HuggingFace 의 cloth-folding 오픈 데이터셋
(`lerobot/full_folding`, `level2_final_quality3_t_0_hil_data_c`)을 OpenArm 16D 양팔
하드웨어에 맞게 재학습한 **PI0.5 체크포인트**로, syhlabtop 워크스테이션에서
실시간 옷 폴딩 태스크를 운영하는 것이 최종 목표다.

태스크 텍스트: `Fold the T-shirt properly`.

---

## 2. 시스템 아키텍처

```
[syhlabtop 머신]                                  [A6000 머신 (10.252.205.103)]
- RealSense 카메라 3개                            - 데이터셋 prep (level2, full_folding)
  · left_wrist:  315122270766                     - relstats 재계산
  · right_wrist: 230322273311                       (chunk30, gripper 제외)
  · base:        213622075840                     - PI0.5 학습 (4× RTX A6000)
- DamiaoMotorsBus                                 - recipe gate + replay gate
  · CAN0=left, CAN1=right                         - 라이브 서버 port 8766
- syhlabtop_live_guarded_rollout.py               - snapshot 백업 서버 port 8765
                                                  
  ◄──── 8766 /predict_live, /health ────►        
```

### 하드웨어 contract

```
Action / State: 16D
  순서: right_joint_{1..7}.pos, right_gripper.pos,
        left_joint_{1..7}.pos,  left_gripper.pos
  단위: degrees
  gripper 범위: [-65, 0] deg (larger jaws 설치 상태)
  chunk_size: 30
  runtime action semantics: absolute (A6000 postprocessor 가 상대→절대 변환)
  action_space_version: openarm_folding_abs_16d_deg_v1

Motor types:
  J1-2: dm8009, J3-4: dm4340, J5-7/gripper: dm4310 (양쪽 동일)

Actuator path (CORRECT):
  DamiaoMotorsBus.connect(handshake=False)
  + guarded MIT batch writes

Actuator path (FORBIDDEN):
  OpenArmFollower.connect()  ← set_zero_position + enable_torque 트리거
  send_action()
  lerobot-rollout
```

### A6000 서버 환경변수 (필수)

```bash
HF_HOME=/mnt/nas/huggingface
HF_HUB_CACHE=/mnt/nas/huggingface/hub
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### 현재 서빙 체크포인트

```
포트:    8766 (live), 8765 (snapshot 백업)
경로:    /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/
         pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
gate:    recipe PASS, replay PASS
loss:    0.066 at step 4000/4000
출처:    level2_final_quality3_t_0_hil_data_c 의 corrected relstats 재학습
```

---

## 3. 파이프라인 단계별 로드맵

| 단계 | 산출물 | 상태 | 비고 |
|---|---|---|---|
| **D1** 데이터셋 | `level2_final_quality3_t_0_hil_data_c` (1319 eps / 3.4M frames) | ✅ 완료 | — |
| **D2** 데이터셋 | `lerobot/full_folding` (5688 eps / 14.1M frames) | ✅ 완료 | task-filtered 4100 eps 사용 여부 = D-1 |
| **P1** 전처리 | level2 chunk30 relstats | ✅ 완료 | gripper 제외 |
| **P2** 전처리 | full_folding chunk30 relstats | ✅ 완료 | curated mix 필요 여부 = D-2 |
| **T1** 학습 | level2 step 4000 PI0.5 | ✅ 완료 | loss 0.066 |
| **T2** 학습 | full_folding step 4000 PI0.5 | ✅ 완료 | 추가 step / fine-tune = D-3 |
| **G1** Recipe gate | level2 004000 | ✅ PASS | — |
| **G2** Replay gate | level2 004000 | ✅ PASS | — |
| **G3** Recipe gate | full_folding 004000 | ✅ PASS | — |
| **G4** Replay gate | full_folding 004000 | ❌ FAIL | delta ratio 0.128–0.282 (threshold 0.25–4.0) |
| **G5** Replay gate | full_folding 002000 | ⬜ 미실행 | **Track C, D-4** |
| **G6** Replay gate | full_folding 003000 | ⬜ 미실행 | **Track C, D-4** |
| **S1** 서빙 | port 8766 = level2 corrected 004000 | ✅ 가동 | — |
| **S2** 서빙 | port 8765 = snapshot 백업 | ✅ 가동 | — |
| **R1** Dry-run | Stage35–40 packet write 시퀀스 | ✅ 완료 | archive 됨 |
| **R2** 라이브 롤아웃 | messy shirt 시나리오 | ⬜ 미실행 | **Track A, D-5** |
| **R3** 카메라 정렬 | base FOV/scale 일치 | ⬜ 미완 | physical raise vs preprocessing = D-6 |
| **R4** 축 probe | left_joint_{4,5,6,7} + 양 gripper sign | ⬜ 미완 | operator 입회 필요 = D-7 |
| **R5** 분석 | 시나리오 다양화 / 결과 회귀 | ⬜ 미완 | — |

---

## 4. 트랙 정의 + 현재 우선순위

| Track | Goal | 현재 상태 |
|---|---|---|
| **A** | syhlabtop level2 라이브 롤아웃 | UNBLOCKED — Track D 결과 본 뒤 messy shirt 실행 |
| **B** | full_folding 재학습 | COMPLETE — replay FAIL, 004000 은 deploy 후보 아님 |
| **C** | full_folding ckpt 002000/003000 replay gate 비교 | NOT STARTED — A6000 단독 가능 |
| **D** | 축 방향 probe + base 카메라 정렬 | NOT STARTED — operator 필요 |

### 우선순위 그룹

```
P0 (지금 막힌 진짜 의존성):
  - 없음.

P1 (병렬 가능):
  - Track C: A6000 ckpt 002000/003000 replay gate 실행
  - Track D1: openarm_limit_axis_audit.py read-only 재실행
  - Track D2: base 카메라 alignment 확인 (syhlabtop 단독)

P2 (Track D 통과 후):
  - Track A: messy shirt 시나리오 라이브 롤아웃

P3 (Track C 결과에 따라):
  - 002000/003000 PASS → S1 서빙을 full_folding 후보로 전환
  - 모두 FAIL → 추가 학습 / fine-tune 결정 (D-3)
```

---

## 5. 결정 필요 항목

> 이 항목들은 임의 결정 금지. 사용자 또는 operator 의 명시적 결정 후 실행.

| ID | 항목 | 컨텍스트 |
|---|---|---|
| **D-1** | full_folding 안에서 `Fold the T-shirt properly` 4100 eps 만 사용한 재학습 시도 여부 | full_folding 은 3개 task 변형 포함 (4100 + 1561 + 27). 품질 차이 있음. |
| **D-2** | curated mix 데이터셋 (level2 + full_folding 선별) 생성 여부 | 도메인 갭이 큰 두 데이터셋의 mix 가 유효한지 평가 필요. |
| **D-3** | full_folding 학습 step 8000+ 진행 vs level2 에서 fine-tune | replay FAIL 이 underfit (step 부족) 인지 ckpt selection 인지 G5/G6 결과 보고 결정. |
| **D-4** | Track C 실행 일정 | A6000 단독 작업. 누가 / 언제 실행할지 결정. |
| **D-5** | Track A 라이브 롤아웃 실행 일정 | Track D 통과 후. operator 입회 필요. |
| **D-6** | base 카메라 정렬 우선순위 | (a) 물리 raise/tilt 우선 vs (b) runtime preprocessing transform 우선. 후자는 `vision_preprocess_id` 로 contract 등록 필요. |
| **D-7** | left_joint_{4,5,6,7} + 양 gripper 물리 축 probe 실행 여부 | `limit_axis_physical_check_plan_2026-05-14.md` 의 `+1deg/-1deg` 시퀀스. operator 입회 필요. |

---

## 6. 현역 참조 파일

### audits/openarm_folding/ — 운영 문서 (8 md)

| 파일 | 역할 |
|---|---|
| `README.md` | Track A/B/C 상태 인덱스. PLAN/STATUS 가 도입되기 전 메인 인덱스였음. |
| `trackA_level2_live_test_plan_2026-05-14.md` | Track A messy shirt 라이브 롤아웃 커맨드 템플릿 |
| `visual_dataset_alignment_and_full_folding_retrain_plan_2026-05-14.md` | Track B 데이터/카메라 정렬 계획 |
| `openpi_lerobot_live_pipeline_check_2026-05-14.md` | OpenPI vs LeRobot 파이프라인 결정 (LeRobot 채택) |
| `damiao_setup_axis_alignment_review_2026-05-14.md` | Damiao 모터 영구설정 변경 동결 결정 |
| `limit_axis_physical_check_plan_2026-05-14.md` | 물리 축 sign probe 계획 |
| `openarm_follower_j4_5cm_fabrication_order_2026-05-14.md` | J4 +5cm extension 제작 주문 |
| `live_deploy_technique_applicability_2026-05-14.md` | live deploy 기법 매핑 |

### audits/openarm_folding/ — 운영 스크립트 (8 py + 1 sh)

| 파일 | 역할 |
|---|---|
| `syhlabtop_live_guarded_rollout.py` | 메인 라이브 롤아웃 (1300+ 줄, `--readback-stride 0 --hold-last-action` 지원) |
| `syhlabtop_live_policy_input_viewer.py` | 3-카메라 read-only 웹 뷰어 (port 8091) |
| `syhlabtop_snapshot_policy_client.py` | snapshot 서버 클라이언트 |
| `a6000_live_policy_server.py` | A6000 live 정책 서버 (port 8766) |
| `a6000_snapshot_policy_server.py` | A6000 snapshot 백업 서버 (port 8765) |
| `openarm_limit_axis_audit.py` | joint readback + 제한 마진 read-only 감사 |
| `stage22_dataset_replay_and_ablation.py` | dataset replay gate (이름 stage* 지만 현역) |
| `stage29_candidate_recipe_gate.py` | recipe gate (이름 stage* 지만 현역) |
| `run_rsusb_py312.sh` | RSUSB pyrealsense2 환경 래퍼 |

### 기타

- `AGENTS.md` (= `CLAUDE.md` symlink) — 작업 룰, OpenArm 하드룰 8개
- `docs/STATUS.md` — 변동성 있는 현재 상태 (PLAN.md 보다 자주 갱신됨)
- `docs/_archive/openarm_folding/` — Stage10~40 작업 기록 96개 (보존만)
- `docs/_archive/INDEX.md` — archive 인덱스

---

## 7. 변경 이력

| 날짜 | 변경 | 비고 |
|---|---|---|
| 2026-05-15 | SSOT 도입 (`docs/PLAN.md`, `docs/STATUS.md`), `docs/_archive/openarm_folding/` 분리, `AGENTS.md` 에 OpenArm Fork Operations 섹션 + 8개 하드룰 추가 | 96개 stage 잔재 archive 이동 |
| 2026-05-15 | `syhlabtop_live_guarded_rollout.py` 에 `--readback-stride`, `--hold-last-action` 추가 | 모션 끊김 해소 |
| 2026-05-15 | Track B `full_folding` 004000 학습 완료, replay gate FAIL | 별도 커밋, A6000 측 작업 |
| 2026-05-14 | `trackA_level2_live_test_plan_2026-05-14.md` 커맨드에 `--readback-stride 0 --hold-last-action` 반영 | — |
| 2026-05-12 | `level2_final_quality3` corrected relstats 재학습 (PI0.5 step 4000) 완료, recipe + replay gate PASS | Stage31 |
| 2026-05-11 | folding_latest 의 relative-stats 불일치 발견 (Stage21–27) | recovery 시작 |
