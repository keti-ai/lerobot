# OpenArm 폴딩 재학습/롤아웃 플랜 (SSOT)

**마지막 갱신:** 2026-05-19 (custom rollout archive, `lerobot-rollout` baseline 전환 준비)  
**브랜치:** `audit/openarm-folding-baseline`  
**용도:** 이 레포에 들어오는 세션이 현재 전략, 결정 항목, 데이터셋/모델 registry 위치를 한 문서에서 확인하게 한다.

---

## 1. 최종 목표

이 레포는 upstream LeRobot 위에 OpenArm 폴딩 실험을 얹은 포크다. 목표는
Hugging Face cloth-folding 계열 데이터셋과 A6000 재학습 산출물을 OpenArm 16D 양팔
하드웨어에서 공식 `lerobot-rollout` 실행 경로로 평가하고, 안정적인 폴딩 후보를
선정하는 것이다.

태스크 텍스트: `Fold the T-shirt properly`.

현재 deploy 가능성이 남아 있는 운영 후보는 **level2 corrected checkpoint 004000**
이다. 이 후보는 recipe PASS + replay PASS 이며, 현재 A6000 `8766` live server 와
`8765` snapshot server 에서 서빙 중이다.

`full_folding` 계열 `002000`, `003000`, `004000`, D-8a continuation `001000`~`012000`
은 replay gate FAIL 이므로 현재 deploy 후보가 아니다.

---

## 2. 시스템 아키텍처

```text
[syhlabtop 머신]                                  [A6000 머신 (10.252.205.103)]
- RealSense 카메라 3개                            - 데이터셋 prep (level2, full_folding)
  · left_wrist:  315122270766                     - relstats 재계산
  · right_wrist: 230322273311                       (chunk30, gripper 제외)
  · base:        213622075840                     - PI0.5 학습 (4x RTX A6000)
- OpenArm 양팔 CAN                                - recipe gate + replay gate
  · CAN0=left, CAN1=right                         - live server port 8766
- 공식 lerobot-rollout baseline 준비              - snapshot server port 8765
```

### 하드웨어/데이터 contract

```text
Action / State: 16D
  순서: right_joint_{1..7}.pos, right_gripper.pos,
        left_joint_{1..7}.pos,  left_gripper.pos
  단위: degrees
  gripper 범위: [-65, 0] deg
  chunk_size: 30
  runtime action semantics: absolute target
  action_space_version: openarm_folding_abs_16d_deg_v1

Motor types:
  J1-2: dm8009, J3-4: dm4340, J5-7/gripper: dm4310 (양쪽 동일)
```

### 실행 baseline

Phase 1 이후 live rollout 의 기준은 공식 `lerobot-rollout` 이다. 기존 syhlabtop custom
rollout/client/viewer 문서는 archive 로 이동한다. 실제 모션 안전 모델은 operator
현장 입회, power abort, E-stop 이며 code-side approval phrase/envelope contract 는
사용하지 않는다.

Phase 3 에서 `OpenArmFollower.connect()` side effect 를 최소 플래그로 제어한 뒤
`lerobot-rollout` preflight/load test 를 수행한다. A6000 HTTP serving `8766/8765` 는
그대로 유지하되, 공식 rollout 과의 호환 방식은 Phase 3 에서 검증한다.

### A6000 서버 환경변수

```bash
HF_HOME=/mnt/nas/huggingface
HF_HUB_CACHE=/mnt/nas/huggingface/hub
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### 현재 서빙 체크포인트

```text
포트:    8766 (live), 8765 (snapshot backup)
경로:    /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/
         pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
gate:    recipe PASS, replay PASS
loss:    0.066 at step 4000/4000
출처:    level2_final_quality3_t_0_hil_data_c corrected relstats 재학습
```

### A6000 학습 환경 (D-9)

```text
host:   ketiserver (a6000)
GPU:    RTX A6000 x 4
driver: 570.133.20

RESOLVED:
  torch 2.11.0+cu128 / CUDA 12.8 / cuDNN 91900 환경은 Conv2d 에서
  CUDNN_STATUS_NOT_INITIALIZED 로 실패했다.

결정:
  option (i) torch 2.7.x + 호환 cuDNN 새 venv.

venv:
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515

검증:
  torch 2.7.1+cu126, CUDA 12.6, cuDNN 90501
  cuDNN enabled Conv2d PASS
  1-step train smoke PASS with dataset.video_backend=pyav

주의:
  torchcodec backend FAIL. D-8 계열 config 는 pyav 사용.
  D-8a relaware 재판정 결과는 no-candidate.
```

---

## 3. 파이프라인 단계별 로드맵

| 단계 | 산출물 | 상태 | 비고 |
|---|---|---|---|
| **D1** 데이터셋 | `level2_final_quality3_t_0_hil_data_c` | 완료 | Phase 2 Dataset Registry 에 세부 정리 |
| **D2** 데이터셋 | `lerobot/full_folding` | 완료 | fold-only 4100 eps 여부는 D-1 |
| **P1** 전처리 | level2 chunk30 relstats | 완료 | gripper 제외 |
| **P2** 전처리 | full_folding chunk30 relstats | 완료 | curated mix 여부는 D-2 |
| **T1** 학습 | level2 step 4000 PI0.5 | 완료 | 현재 운영 후보 |
| **T2** 학습 | full_folding step 4000 + D-8a continuation | 완료/실패 | replay FAIL, no candidate |
| **G1** Recipe gate | level2 004000 | PASS | — |
| **G2** Replay gate | level2 004000 | PASS | — |
| **G3** Recipe gate | full_folding 계열 | relaware PASS | D-8a current gate false-negative 복구 |
| **G4** Replay gate | full_folding 계열 | FAIL | deploy 후보 없음 |
| **S1** 서빙 | port 8766 live | 가동 | level2 corrected 004000 |
| **S2** 서빙 | port 8765 snapshot | 가동 | backup |
| **R1** custom rollout | syhlabtop guarded live harness | archive | 2026-05-19 deprecated |
| **R2** 공식 rollout | `lerobot-rollout` baseline | 준비 중 | Phase 3 안전 패치/compat 검증 |
| **R3** 데이터셋/모델 registry | Dataset Registry + Model Registry v2 | Phase 2 예정 | 본문 placeholder 생성 |

---

## 4. 트랙 정의 + 현재 우선순위

| Track | Goal | 현재 상태 |
|---|---|---|
| **A** | syhlabtop OpenArm live rollout | `lerobot-rollout` baseline 전환 준비 |
| **B** | full_folding 재학습 | D-8a relaware COMPLETE, no deploy candidate |
| **C** | full_folding checkpoint replay 비교 | COMPLETE, 002000/003000/004000 모두 FAIL |
| **D** | 축/카메라 read-only 진단 | custom 후속 폐기, 첫 official rollout 시각 리뷰로 통합 |

### 우선순위 그룹

```text
P0 (안전 모델):
  - 실제 모션은 operator 현장 입회, power abort, E-stop 준비 상태에서만 실행한다.
  - Phase 1 은 문서 정리와 archive 이동만 수행한다. 실제 모션 없음.
  - code-side approval phrase/envelope contract 는 폐기한다.

P1 (Phase 1):
  - AGENTS hard-rules 섹션 제거.
  - custom syhlabtop rollout 파일 archive.
  - PLAN/STATUS/README 를 official lerobot-rollout baseline 기준으로 갱신.

P2 (Phase 2):
  - Dataset Registry 총망라.
  - Model Registry v2 재스터디.

P3 (Phase 3):
  - OpenArm follower connect side-effect 최소 패치.
  - 공식 lerobot-rollout preflight/load test.
  - operator 입회 후 첫 official rollout 실행.
```

---

## 5. 결정 필요 항목

| ID | 상태 | 항목 | 컨텍스트 |
|---|---|---|---|
| **D-1** | OPEN | `full_folding` fold-only 4100 eps 재학습 여부 | Phase 2 Dataset Registry 에서 task 분포/품질을 다시 정리한 뒤 결정한다. |
| **D-2** | OPEN | curated mix 데이터셋 생성 여부 | level2 + full_folding 선별 mix 가 유효한지 Dataset Registry 이후 결정한다. |
| **D-3** | RESOLVED | full_folding step 8000+ vs level2 fine-tune | D-8 로 통합되어 종료. |
| **D-4** | RESOLVED | Track C checkpoint 비교 일정 | 2026-05-15 완료. 002000/003000/004000 모두 replay FAIL. |
| **D-5** | SUPERSEDED | custom Track A rollout 실행 일정 | custom rollout 은 archive. official rollout 세션으로 대체한다. |
| **D-6** | DEFERRED | base 카메라 정렬 우선순위 | 별도 side-by-side 후속은 폐기. 첫 official rollout 시각 리뷰로 통합 평가한다. |
| **D-7** | DEFERRED | 단일 조인트 축 probe | 폐기. 첫 official rollout 시 전체 시퀀스 흐름과 함께 평가한다. |
| **D-8** | OPEN | full_folding no-candidate 이후 다음 재학습 방향 | D-8a relaware 결과도 no-candidate. D-8b fold-only 또는 curated mix 는 Phase 2 이후 결정한다. |
| **D-9** | RESOLVED | A6000 cuDNN 환경 | option (i) torch 2.7.x + cu126 venv, smoke PASS. |
| **D-10** | RESOLVED | D-8a gate false-negative 진단 | case gamma 완료. relaware recipe PASS, replay FAIL, deploy 후보 없음. |
| **D-11** | NEW | official `lerobot-rollout` OpenArm 안전 connect 패치 | `OpenArmFollower.connect()` 의 configure/set_zero/enable_torque side effect 를 config flag 로 제어한다. |
| **D-12** | NEW | Dataset Registry 총망라 | 데이터셋, 전처리, RABC/SARM, gate/replay 관계를 Phase 2 문서 본문으로 채운다. |
| **D-13** | NEW | Model Registry v2 재스터디 | public 후보 + A6000 후보를 dataset/gate/replay/rollout role 기준으로 재분류한다. |

---

## 6. 현역 참조 파일

### audits/openarm_folding

| 파일 | 역할 |
|---|---|
| `README.md` | pointer-only index |
| `stage22_dataset_replay_and_ablation.py` | dataset replay gate 도구 |
| `stage29_candidate_recipe_gate.py` | candidate recipe gate 도구 |
| `a6000_live_policy_server.py` | A6000 live 정책 서버, port 8766 |
| `a6000_snapshot_policy_server.py` | A6000 snapshot 정책 서버, port 8765 |
| `a6000_*.md` | a6000 측 진행/진단 ping 파일 |

### Archive

Custom syhlabtop rollout, Track A trial report, viewer/client, historical Track D planning 문서는
`docs/_archive/openarm_folding/` 로 이동했다. 세부 목록은 `docs/_archive/INDEX.md` 의
`Track A custom rollout (deprecated 2026-05-19)` 섹션을 본다.

### a6000 측 산출물

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/
├── train/
│   ├── pi05_openarm_relstats_full_nocompile_bsz4_20260512/
│   │   └── checkpoints/004000/pretrained_model
│   ├── pi05_openarm_full_folding_relstats_chunk30_20260514/
│   │   └── checkpoints/{002000,003000,004000}/pretrained_model
│   └── pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/
│       └── checkpoints/{001000..012000}/pretrained_model
└── full_folding_parallel_20260514/audits/
    ├── full_folding_* gate/replay 산출물
    ├── d8a_* relaware gate/replay 산출물
    └── level2_004000_* relaware 회귀 확인 산출물
```

---

## 7. 변경 이력

| 날짜 | 변경 | 비고 |
|---|---|---|
| 2026-05-19 | AGENTS hard rules 제거, custom syhlabtop rollout archive, official `lerobot-rollout` baseline 전환 준비 | Phase 1 |
| 2026-05-18 | A6000 8766/8765 serving 복구. D-10c postprocessor/RABC 진단 완료, case gamma current gate false-negative 판정 | A6000 측 작업 |
| 2026-05-18 | D-8a relaware gate/replay 재판정. 001000~012000 recipe PASS, replay FAIL, no deploy candidate | A6000 측 작업 |
| 2026-05-15 | a6000 측 Track C 결과 + D-9 cuDNN 환경 리뷰 통합 | 002000/003000/004000 replay FAIL |
| 2026-05-15 | SSOT 도입, 기존 Stage10~40 archive 분리 | historical archive |
| 2026-05-12 | level2 corrected relstats 재학습 완료, recipe + replay gate PASS | Stage31 |
| 2026-05-11 | public folding_latest relative-stats 불일치 발견 | recovery 시작 |

---

## 8. Dataset Registry (Phase 2 placeholder)

Phase 2 에서 다음 컬럼으로 본문을 채운다.

| dataset | source/path | level/task | episodes/frames | fps | cameras | action/state contract | action representation | curation | SARM/RABC | trained models | gate/replay result | deployment relevance |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `level2_final_quality3_t_0_hil_data_c` | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| `lerobot/full_folding` | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| A6000 level2 relstats chunk30 | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| A6000 full_folding relstats chunk30 | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| D-8a continuation dataset/config | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO |

---

## 9. Model Registry v2 (Phase 2 placeholder)

Phase 2 에서 public 후보와 A6000 후보를 같은 표에서 재분류한다.

| tier | model/checkpoint | source | training dataset | policy_type | chunk | relative_actions | RABC/SARM | processor/action_normalization_id | gate | replay | rollout role |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tier 1 | A6000 level2 corrected 004000 | TODO | TODO | TODO | TODO | TODO | TODO | TODO | PASS | PASS | official rollout 후보 |
| Tier 1 | A6000 8766 live serving | TODO | TODO | TODO | TODO | TODO | TODO | TODO | PASS | PASS | serving truth source |
| Tier 1 | `lerobot/folding_latest` | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | public reference |
| Tier 2 | `folding_final10` / `folding_final` / `ablation2-5_0` | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | metadata/gate only |
| Tier 2 | base/pretrain models | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | TODO | reference only |
