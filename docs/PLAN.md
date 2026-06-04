# OpenArm 폴딩 재학습/롤아웃 플랜 (SSOT)

**마지막 갱신:** 2026-05-21 (banana handover dataset 수집 + OpenArm record safety 반영)
**브랜치:** `audit/openarm-folding-baseline`  
**용도:** 이 레포에 들어오는 세션이 현재 전략, 결정 항목, 데이터셋/모델 registry 위치를 한 문서에서 확인하게 한다.

---

## 1. 최종 목표

이 레포는 `lerobot` 포크다. **현재 단계는 운영이 아니라 feasibility 검증**이다:
HuggingFace 의 cloth-folding 모델군 (PI0.5 `folding_latest`, ablation 시리즈,
자체 재학습 ckpt) 중 어떤 후보가 OpenArm 16D 양팔에서 "양팔이 옷에 접촉하고
폴딩스러운 시퀀스를 시도" 하는지를 짧게 여러 번 돌려서 확인한다.

운영 후보 선정은 feasibility 결과를 본 다음 사이클의 결정 사항.
특정 ckpt (예: level2 corrected 004000) 의 성공률을 고정 목표로 삼지 않고
여러 후보의 동작 패턴을 탐색하는 것이 목표.

라이브 baseline: 공식 `lerobot-rollout` + operator 입회 + power abort / E-stop.

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
  2026-05-15 Conv2d smoke 에서 CUDNN_STATUS_NOT_INITIALIZED 로 실패했다.

결정:
  기본 검증 환경은 option (i) torch 2.7.x + 호환 cuDNN 새 venv.
  단, 2026-05-21 현재 torch 2.11.0+cu128 / cuDNN 91900 환경에서
  cuDNN enabled Conv2d forward/backward multi-shape smoke 가 PASS 했으므로,
  handover alpha 학습은 no-sync smoke PASS 조건으로 현재 torch 2.11 환경 사용을 허용한다.

venv:
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515

검증:
  torch 2.7.1+cu126, CUDA 12.6, cuDNN 90501
  cuDNN enabled Conv2d PASS
  1-step train smoke PASS with dataset.video_backend=pyav
  2026-05-21 torch 2.11.0+cu128, CUDA available, cuDNN 91900
  cuDNN enabled Conv2d forward/backward multi-shape smoke PASS

주의:
  uv run 은 --no-sync 로 실행해 학습 중 환경 재동기화를 피한다.
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
| **D-9** | RESOLVED | A6000 cuDNN 환경 | torch 2.7.x + cu126 venv 가 기본. 2026-05-21 torch 2.11.0+cu128/cuDNN 91900 도 no-sync Conv2d forward/backward smoke PASS 조건으로 handover alpha 학습 허용. |
| **D-10** | RESOLVED | D-8a gate false-negative 진단 | case gamma 완료. relaware recipe PASS, replay FAIL, deploy 후보 없음. |
| **D-11** | NEW | Phase 3 serving adapter 위치 | `lerobot-rollout` 전환 시 A6000 HTTP 서빙 호환 adapter 를 server 쪽에 둘지 client 쪽에 둘지 별도 결정한다. |
| **D-12** | NEW | OpenArmFollower 안전 패치 default | upstream 유지 vs 안전 모드 default 여부는 Phase 3 에서 별도 결정한다. |
| **D-13** | RESOLVED | feasibility 첫 live P1 ckpt 큐 선정 | handover α shortlist (10k/12k/14k/16k/18k) 5개 모두 recipe gate REJECTED. 016000 도 deploy 불가. case α 진단 확정 (D-32). |
| **D-28** | RESOLVED | α HF push 정책 | push 안 함. α 학습 자체 결함 (D-32 case α) 으로 deploy candidate 아님. a6000 local 만 유지. |
| **D-29** | UPDATED | A6000 serving 정책 | (2026-05-22 RESOLVED → 2026-06-01 갱신) M4 REJECTED 후 8766 일단 정지 결정. 다음 사이클 (R: handover v1 재학습) GPU 확보 용도. baseline 라이브 없어짐을 감수. 8765 정지 상태 유지. |
| **D-30** | DEFERRED | operator 입회 일정 | D-33 재학습 결과 PASS 시점 이후로 보류. |
| **D-31** | SUPERSEDED | β 학습 진입 여부 | D-33 (handover relstats 변환 후 α 재학습) 결과 본 뒤 재검토. mixed corpus 는 그 다음 단계. |
| **D-32** | RESOLVED | α gate REJECTED 원인 진단 | **case α (B-1) 확정**. `use_relative_actions=true` ↔ handover dataset absolute action 미스매치. processor stats 가 absolute 분포 (q01/q99 ≈ -53.7..113.0) 로 학습됨. shortlist 5개 모두 같은 학습이라 동일 결함. → α 학습 자체 SKIP, deploy 불가. 보고서: `audits/openarm_folding/a6000_pi05_handover_alpha_postmortem_case_alpha_*.md` |
| **D-33** | RESOLVED | handover dataset relstats 변환 후 α′ 재학습 | M2b dataset private HF push 완료, α′ 30k 학습 PASS. Shortlist `022000`/`024000`/`026000`/`028000`/`030000` recipe/replay offline gate REJECTED. Relstats action-stat mismatch 는 해결됐지만 locked folding recipe 의 robot/camera/RABC checks 와 replay target-magnitude checks 가 FAIL. Deploy 후보 없음. |
| **D-34** | OPEN | dataset ↔ 환경 adaptation 미니 레포 (사이드) | dataset 분포와 운영 환경 (OpenArm + RealSense 3cam) 간극을 메우는 preprocessing 함수 컬렉션. P0 vision (FOV/scale/color/exposure), P1 proprio (joint offset/range/단위), P2 action contract = D-33 relstats 변환 일반화 (S2 commit ca532645 으로 P2 완료). P0/P1 은 D-35 분기 끝나고 진행. 위치 = `src/lerobot/openarm_adaptation/` (모듈) + `docs/STUDY/openarm_adaptation/` (스터디 노트). |
| **D-35** | OPEN | M4 REJECTED 후 다음 분기 (2026-06-01 결정) | 사용자 결정 = (U) episode 분포 진단 → (P) handover-specific recipe gate → (Q) replay threshold task-specific → (R) handover v1 50-100 ep 추가 수집. 순차 진행. (S) init 변경, (T) task 단순화 는 제외. R 의 사용자 일정은 별도 결정. |
| **D-36** | OPEN | handover-specific recipe gate (P 단계) | stage29 의 folding lock 3 항목 (robot_type=`openarms_follower` 강제, camera shape lock, RABC 강제) 을 handover task 용으로 완화 또는 별도 gate 작성. 위치 후보: `audits/openarm_folding/stage29_candidate_recipe_gate.py` 의 task-aware path 또는 신규 `handover_recipe_gate.py`. ~2-3h Codex syhlabtop. U 진단 결과 보고 디자인. |
| **D-37** | OPEN | replay threshold task-specific (Q 단계) | stage22 의 ratio/raw threshold 가 folding 분포 기준. handover 의 ratio 분포 (현재 0.03-0.14) 와 raw normalized error (~4.8) 에 맞춘 task-specific threshold 정의. 단 PASS 자체가 deploy 보장 아님 — 모델이 큰 swing 출력 못 하는 문제는 그대로. ~2-3h Codex syhlabtop. |
| **D-38** | DETAIL | handover v0 multi-object 수집 + α'' 후속 (R 단계, 방식 A) | 2026-06-02 수집 완료 (65 ep / 58,340 frames / 3 tasks: banana 0-19, olive green cup 20-44, blue toothpaste 45-64). plate skip (작업성). **Cleaning 진행** (사용자 결정 2026-06-04): 다른 고성능 PC 에서 HF clone → lerobot-dataset-viz review → 실패 ep index 식별 → Codex 가 delete_episodes 로 clean dataset 생성 → relstats 재변환 → α'' 재학습. 새 variant slug = `KETI-IRRC/openarm_handover_v0_multi3_clean_relstats_chunk30`. α 시리즈: α=20 ep absolute (D-32 REJECTED), α'=20 ep relstats (M4 REJECTED), α''=clean 65-N ep multi3 relstats (진행 예정). fix commit db4d0a6e. plan: `~/.claude/plans/quizzical-petting-sundae.md` §13. |
| **D-39** | NEW | (S) init 변경 / (T) task 단순화 추후 검토 | D-38 (handover v1 재학습) 결과 또 REJECTED 인 경우에 (S) base PI0.5 init 또는 (T) single-arm pick & place 시도. 현재 D-38 결과 input 으로 보류. |
| **D-40** | NEW | Wayland keyboard listener patch | 2026-06-02 R 수집 중 발견. pynput global keyboard listener 가 Wayland (XDG_SESSION_TYPE=wayland) 에서 Esc/Left Arrow 신뢰성 X. 다음 수집 전 patch 필요. 옵션: (a) stdin-based control / (b) evdev 직접 / (c) GUI button click. 위치: `src/lerobot/utils/control_utils.py` 의 `init_keyboard_listener`. ~2-3h Codex syhlabtop. |
| **D-41** | NEW | Open dataset replay sanity check (2026-06-04 사용자 회고 의견) | α/α' 평가 전 했어야 한다는 회고. 두 sub-task: **D-41a** stage22 gate 의 known-good 조합 (level2 corrected 004000 + level2_relative_stats_chunk30) replay PASS 확인 → gate 도구 자체 sanity. **D-41b** HF `lerobot/folding_latest` ckpt + dataset replay → PI0.5 자체 capability 검증, handover 가 PI0.5 한계인지 data/training 문제인지 분리 (D-39 V 옵션 input). A3 학습 중 병행 가능 (~1h Codex a6000). |

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

## 7-bis. Feasibility 판정 기준

현재 단계의 라이브 세션은 task success 가 아니라 folding 시도 패턴을
관찰하는 feasibility test 다. 세 역할이 같은 기준을 공유한다.

### 정성 (operator 가 라이브 직후 1줄 평가)

- 양팔이 testing zone 안에서 옷에 **접근** 했는가
- gripper open/close 가 **옷 잡기 의도** 로 보이는가
- 한쪽이 옷을 들고 다른 쪽이 **받는 패턴** 이 시도되는가
- 폴딩 동작 (대각선 접기 / 가운데 접기) 의 **일부** 라도 보이는가

### 정량 (study assistant 가 summary.json 에서 추출)

- `actions_executed`, `chunks_accepted` — runtime PASS proxy
- gripper close 횟수 — 옷 잡기 시도 빈도 proxy
- left-right joint trajectory 의 상관 계수 — 양팔 협응 proxy
- hard saturation count — 정책이 한계에 박혀 있는지

### 판정 라벨

- **PROMISING** — 폴딩 시도 동작 일부 관찰. 시간 더 투자할 가치
- **AMBIGUOUS** — 양팔은 움직이나 의도 불명. 다른 ckpt 우선 시도
- **REJECTED** — 옷 근처에 안 감 / 명백히 다른 task / 즉시 폐기

### 역할별 사용법

- **operator**: 라이브 세션 직후 정성 4항목 체크 + 라벨 1개 + 1줄 코멘트.
  `audits/openarm_folding/feasibility_runs_<date>.md` 에 append.
- **planner**: feasibility_runs 누적 → PROMISING 후보의 학습 방향 / 다음
  실험 큐 결정. PLAN.md §5 결정 항목 (D-13 등) 에 반영.
- **study assistant** (Registry/Codex): 정량 지표 추출 자동화. Registry §8/§9
  의 `feasibility_test_priority` 컬럼 갱신 입력으로 사용.

### 결과 누적 위치

- 텍스트 보고서 (정성/정량 요약, 1세션당 수 KB): syhlabtop git tracked
  `audits/openarm_folding/feasibility_runs_<YYYYMMDD>.md` 한 파일에 일자별 append
- 영상 / 카메라 frame / eval_frames 대용량: `/home/syhlabtop/openarm_folding_20260512/feasibility/<trial>/`
  (git ignore 영역, 필요 시 rsync 로 a6000 NAS 동기화)

## 7. 변경 이력

| 날짜 | 변경 | 비고 |
|---|---|---|
| 2026-06-04 | Cleaning ep 결정 (사용자 review 결과 [13, 24, 25, 51, 55] 제외 → 60 ep). D-41 NEW (open dataset replay sanity, α/α' 평가 전 했어야 한다는 회고). | syhlabtop SSOT |
| 2026-06-04 | Cleaning 진행 결정 (plan §13 정정). 다른 고성능 PC review → delete_episodes → α''. α 시리즈 명명 명확화 (α/α'/α''). D-38 DETAIL 갱신. | syhlabtop SSOT |
| 2026-06-02 | R (D-38) 수집 완료. 방식 A, 65 ep, 3 tasks. plate skip (작업성 부족) → blue toothpaste 대체. realsense detection fix db4d0a6e. Wayland keyboard 이슈 발견 → D-40 NEW. 실패 ep review + clean dataset 진행 예정. | syhlabtop R + Codex syhlabtop fix |
| 2026-06-01 | M4 REJECTED 분석 + 다음 분기 결정 (사용자). D-33 RESOLVED 확정. D-29 갱신 (8766 정지). D-35 분기 = U→P→Q→R 순차. D-36/37/38/39 NEW. | syhlabtop SSOT |
| 2026-05-26 | D-33 M2b/M3/M4 offline 완료. `KETI-IRRC/openarm_handover_v0_relstats_chunk30` private HF push, α′ relstats 30k 학습 PASS, shortlist 5개 recipe/replay REJECTED → no deploy candidate. | a6000 |
| 2026-05-22 | PI0.5 handover α 20k step 학습 완료 → shortlist gate REJECTED (5/5) → D-32 진단 case α 확정 (relative config ↔ absolute dataset 미스매치). D-13/28/29 RESOLVED, D-30 DEFERRED, D-31 SUPERSEDED. D-33 (handover relstats 변환 후 α 재학습) + D-34 (adaptation 미니 레포 사이드) OPEN | a6000 측 학습 + syhlabtop 측 결정 |
| 2026-05-21 | `KETI-IRRC/openarm_handover_v0_20260521_202117` banana handover 20 episodes 수집, resume/root 레시피와 OpenArm record safety 패치 기록 | syhlabtop live data collection |
| 2026-05-19 | Dataset Registry §8, Model Registry v2 §9 작성 | Phase 2 |
| 2026-05-19 | AGENTS hard rules 제거, custom syhlabtop rollout archive, official `lerobot-rollout` baseline 전환 준비 | Phase 1 |
| 2026-05-18 | A6000 8766/8765 serving 복구. D-10c postprocessor/RABC 진단 완료, case gamma current gate false-negative 판정 | A6000 측 작업 |
| 2026-05-18 | D-8a relaware gate/replay 재판정. 001000~012000 recipe PASS, replay FAIL, no deploy candidate | A6000 측 작업 |
| 2026-05-15 | a6000 측 Track C 결과 + D-9 cuDNN 환경 리뷰 통합 | 002000/003000/004000 replay FAIL |
| 2026-05-15 | SSOT 도입, 기존 Stage10~40 archive 분리 | historical archive |
| 2026-05-12 | level2 corrected relstats 재학습 완료, recipe + replay gate PASS | Stage31 |
| 2026-05-11 | public folding_latest relative-stats 불일치 발견 | recovery 시작 |

---

## 8. Dataset Registry

`feasibility_test_priority` 는 "이 dataset 기반으로 학습 없이 지금 시도 가능한
OpenArm 16D ckpt 가 있는가" 기준이다. P1 row 가 있더라도 첫 live 큐는 §9
Decision Inputs 의 D-13 에 따라 사용자가 직접 고른다.

| dataset | source/path | level/task | episodes/frames | fps | cameras | action/state contract | action representation | curation | SARM/RABC | trained models (which checkpoints used this) | gate/replay result | deployment relevance | feasibility_test_priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `KETI-IRRC/openarm_handover_v0_20260521_202117` | HF private; local root `/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117` | banana bimanual handover; `Pick the banana, hand it over to the other arm, and place it at the target.` | 20 episodes / 17,944 frames | 30 | left_wrist D405 `315122270766`, right_wrist D405 `230322273311`, base D435I `213622075840`; 640x480 RGB AV1 | `bi_openarm_follower`; 16D state/action, degrees, right joints/gripper then left joints/gripper | absolute target rows from `openarm_mini` teleop; runtime `max_relative_target=5`; gripper `0` closed | single syhlabtop live session; first 7 episodes survived a right_wrist timeout, then 13 episodes appended with `--resume=true` and explicit `--dataset.root` | none yet | none yet | metadata counts verified; rerun replay command recorded, visual replay pending for final review | new task-specific handover source for future training/eval | P2 |
| `KETI-IRRC/openarm_handover_v0_relstats_chunk30` | HF private; local root `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30` | banana bimanual handover relstats derivative | 20 episodes / 17,944 frames; 520,920 valid relative rows | 30 | same source cameras; 640x480 RGB AV1 | `bi_openarm_follower`; 16D state/action, degrees | 14 arm dims converted to relative chunk30; grippers `(7,15)` excluded/absolute | D-33 transform PASS; `.relstats_complete`; source payload unchanged outside stats/marker | none/RABC not recorded in α′ train | `pi05_handover_v0_alpha_relstats_20260522_213056` shortlisted `022000`-`030000` | relstats stats PASS; recipe FAIL on locked folding non-action checks; replay FAIL 5/5 | valid task-specific relstats dataset, but no deploy ckpt | P2 |
| `lerobot/full_folding` | HF public; local source mirror `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/datasets/full_folding_novideo` | full folding public mix; `Fold the T-shirt properly` 4100 eps, layout-then-fold 1561 eps, `Fold` 27 eps | 5688 episodes / 14,129,038 frames | 30 | left_wrist, right_wrist 720x1280; base 480x640 | OpenArm `openarms_follower`; 16D state/action, degrees | source action rows are absolute targets; A6000 relstats derivative converts arm 14D to relative chunk30, grippers excluded/absolute | no correction_report; broad full dataset; fold-only 4100 eps is D-1 candidate | SARM rows 14,129,038; downstream full_folding training uses RABC sample_weighting | A6000 full_folding 001000-004000; D-8a continuation 001000-012000 | relaware recipe PASS, replay FAIL for available full_folding ckpts | important training source, but no current deploy ckpt | P3 |
| `lerobot-data-collection/level2_final_quality3_t_0_hil_data_c` | HF public; local root `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/datasets/level2_final_quality3_t_0_hil_data_c` | Level 2 high-quality / HIL folding data | 1319 episodes / 3,414,338 frames | 30 | left_wrist, right_wrist 720x1280; base 480x640 | OpenArm `openarms_follower`; 16D state/action, degrees | source action rows are absolute targets; relstats derivative used for training | correction_report present; HQ/HIL subset | SARM progress used by folding/latest lineage and corrected relstats training; RABC in trained configs | public `folding_latest` lineage; A6000 level2 corrected 004000 | level2 corrected 004000 recipe PASS, replay PASS; legacy public folding_latest gate/replay FAIL | current live baseline source, not final goal | P1 |
| A6000 level2 relstats chunk30 | `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/datasets/level2_final_quality3_t_0_hil_data_c_relative_stats_chunk30` | Level 2 HQ/HIL relstats derivative | 1319 episodes / 3,414,338 frames | 30 | left_wrist, right_wrist 720x1280; base 480x640 | OpenArm 16D state/action, degrees | `use_relative_actions=true`, `chunk_size=30`, 14 arm dims relative, grippers excluded/absolute | corrected relstats derivative of HQ level2 | `sample_weighting.type=rabc`, progress from level2 SARM | `pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000` | recipe PASS, replay PASS, relaware recheck PASS | immediate feasibility baseline candidate | P1 |
| A6000 full_folding_relative_stats_chunk30 | `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/datasets/full_folding_relative_stats_chunk30` | full_folding relstats derivative | 5688 episodes / 14,129,038 frames; 13,964,086 valid relative chunks | 30 | left_wrist, right_wrist 720x1280; base 480x640 | OpenArm 16D state/action, degrees | `use_relative_actions=true`, `chunk_size=30`, 14 arm dims relative, grippers excluded/absolute | relstats recompute PASS; source has 3 task variants | SARM rows 14,129,038; RABC progress path local `sarm_progress.parquet`; kappa 0.0265 | full_folding 001000-004000; D-8a 001000-012000 | relaware recipe PASS; replay FAIL for checked ckpts | valuable training source, but current ckpts not deploy | P3 |
| D-8a continuation dataset/config | config `/data/.../full_folding_parallel_20260514/audits/d8a_full_folding_continue_003000_torch27_pyav_config_20260515.json`; dataset root same full_folding relstats chunk30 | continuation from full_folding 003000 toward 012000 | same as full_folding relstats | 30 | left_wrist, right_wrist 720x1280; base 480x640 | OpenArm 16D state/action, degrees | relative chunk30, grippers excluded/absolute; video_backend `pyav` | continuation config only; no new dataset curation | RABC sample_weighting kept; local SARM progress path | `pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints/001000..012000` | 001000-012000 relaware recipe PASS, replay FAIL | no deploy candidate; informs D-8 next training choice | P3 |
| `lerobot-data-collection/folding_final10` | public model/checkpoint repo; local metadata cache `/data/.../candidate_recipe_gate_cache/lerobot-data-collection__folding_final10` | public folding candidate lineage; train_config points to level2 final quality data | dataset details inherited from level2 lineage where recorded | 30 in gate metadata | OpenArm 3cam contract in candidate config | OpenArm 16D; PI0.5 action/state metadata present | relative action config present but processor stats failed legacy gate | public checkpoint candidate, not curated local dataset | RABC/SARM metadata needs relaware recheck | `lerobot/folding_latest` records this as repo_id/output lineage | legacy gate FAIL: postprocessor relative stats mismatch | metadata/gate-only public candidate | P2 |
| `lerobot-data-collection/folding_final` | public model/checkpoint repo; local metadata cache `/data/.../candidate_recipe_gate_cache/lerobot-data-collection__folding_final` | public folding candidate; train_config points to `level2_final_quality3` lineage | not fully revalidated in Phase 2 | 30 in gate metadata | OpenArm 3cam contract in candidate config | OpenArm 16D metadata present | relative action config present but stats mismatch in legacy gate | public checkpoint candidate | RABC/SARM metadata needs relaware recheck | pretrained/base path for `folding_latest` lineage | legacy gate FAIL: dataset mismatch + postprocessor stats mismatch | metadata/gate-only public candidate | P2 |
| `lerobot-data-collection/ablation2-5_0` | public model/checkpoint repo; local metadata cache `/data/.../candidate_recipe_gate_cache/lerobot-data-collection__ablation2-5_0` | robot-folding ablation candidate | not fully revalidated in Phase 2 | 30 in gate metadata | OpenArm 3cam contract in candidate config | OpenArm 16D metadata present | relative action config present but stats mismatch in legacy gate | ablation candidate, not current local training data | RABC/SARM metadata needs relaware recheck | public ablation candidate only | legacy gate FAIL: dataset mismatch + postprocessor stats mismatch | metadata/gate-only public candidate | P2 |
| public legacy ablation group: `ablation1-7_2`, `ablation1-5_9`, `ablation1_3_17_q` | public metadata cache under `/data/.../candidate_recipe_gate_cache/` | older ablation configs | not applicable | unknown/varies | not verified for current OpenArm rollout path | config decode errors use legacy `use_delta_actions` / `delta_exclude_joints` fields | historical reference only | not verified | none in current deploy path | legacy expanded gate ERROR for PI05Config decode | not a feasibility candidate without migration/re-export | X |

### Dataset Findings

- 공식 robot-folding recipe 에서는 고품질·일관 데이터가 핵심 lever 로 보인다.
- full dataset only 는 Level 2 동작에 약할 수 있다. full_folding 은 더 크지만 task variant 가 섞여 있고, 현재 replay PASS ckpt 가 없다.
- HQ + relative + RABC fine-tune 이 개선 핵심으로 보인다. 현재 PASS path 는 level2 HQ/HIL relstats + RABC 004000 이다.
- chunk=45 는 개선 없음으로 기록한다. 현재 registry 의 즉시 후보는 chunk30 기준으로 둔다.
- 현재 Track A 실패는 runtime 문제만이 아니라 데이터 / 분포 / OOD 가능성이 크다.
- 다음 후보는 네 갈래로 정리한다:
  (1) D-8b fold-only 4100 eps,
  (2) curated mix: level2 + full_folding 선별,
  (3) `lerobot/folding_latest` 재 metadata 확인,
  (4) 데이터 추가 수집.

---

## 9. Model Registry v2

`feasibility_test_priority` 는 모델/ckpt row 별 분류다. P1 은 조건 충족 여부를
나타낼 뿐이며, 첫 live 세션 큐 순서는 자동으로 정하지 않는다.

| tier | model/checkpoint | source | training dataset | policy_type | chunk | relative_actions | RABC/SARM | processor/action_normalization_id | gate | replay | rollout role | feasibility_test_priority |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tier 1 | A6000 8766 live | `http://10.252.205.103:8766`; ckpt `/data/.../pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model` | level2 relstats chunk30 | pi05 | 30 | true; gripper excluded | RABC sample_weighting + SARM progress | `processor_sha256:94f781979263ad3f6d85df772d790d3d6909e6379ee47aa8e38491056082c67f`; RTC ON | PASS | PASS | 즉시 실행 | P1 |
| Tier 1 | A6000 8765 snapshot | `http://10.252.205.103:8765`; same level2 corrected 004000 lineage when restored | level2 relstats chunk30 | pi05 | 30 | true; gripper excluded | RABC sample_weighting + SARM progress | same ckpt/processor lineage as 8766; verify `/health` before use | PASS | PASS | 즉시 실행 | P1 |
| Tier 1 | A6000 local level2 corrected 004000 | `/data/.../pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model` | level2 relstats chunk30 | pi05 | 30 | true; gripper excluded | `sample_weighting.type=rabc`, kappa 0.0265, level2 SARM progress | same processor as 8766 live | PASS | PASS | 즉시 실행 | P1 |
| Tier 1 | `lerobot/folding_latest` | local mirror `/data/.../models/folding_latest`; cache `/data/.../candidate_recipe_gate_cache/lerobot__folding_latest` | train_config records `level2_final_quality3_t_0_hil_data_c`; repo lineage `folding_final10` | pi05 | 30 | true; gripper excluded | metadata present but legacy gate mismatch | local processor exists; legacy stats mismatch requires relaware recheck | legacy FAIL | legacy replay FAIL / mismatch | metadata/gate only | P2 |
| Tier 2 | `lerobot-data-collection/folding_final10` | local cache `/data/.../candidate_recipe_gate_cache/lerobot-data-collection__folding_final10` | level2 final quality lineage | pi05 | 30 | likely true; metadata cache present | needs relaware RABC/SARM recheck | processor exists in cache; legacy stats mismatch | legacy FAIL | not current replay PASS | metadata/gate only | P2 |
| Tier 2 | `lerobot-data-collection/folding_final` | local cache `/data/.../candidate_recipe_gate_cache/lerobot-data-collection__folding_final` | `level2_final_quality3` lineage in legacy gate | pi05 | 30 | likely true; metadata cache present | needs relaware RABC/SARM recheck | processor exists in cache; legacy stats mismatch | legacy FAIL | not current replay PASS | metadata/gate only | P2 |
| Tier 2 | `lerobot-data-collection/ablation2-5_0` | local cache `/data/.../candidate_recipe_gate_cache/lerobot-data-collection__ablation2-5_0` | `level2_final_quality3` lineage in legacy gate | pi05 | 30 | likely true; metadata cache present | needs relaware RABC/SARM recheck | processor exists in cache; legacy stats mismatch | legacy FAIL | not current replay PASS | metadata/gate only | P2 |
| Tier 2 | A6000 handover α′ relstats `022000`-`030000` | `/data/.../handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056/checkpoints/{022000,024000,026000,028000,030000}/pretrained_model` | handover relstats chunk30 | pi05 | 30 | true; gripper excluded | none/RABC not recorded | processor stats match relstats target (`rel_q01_err=0`, `rel_q99_err=0`, span ratio `1.0`); folding-locked robot/camera/RABC checks fail | FAIL | FAIL for all 5 shortlisted checkpoints | not deploy | P2 |
| Tier 2 | full_folding 002000/003000/004000 | `/data/.../pi05_openarm_full_folding_relstats_chunk30_20260514/checkpoints/{002000,003000,004000}/pretrained_model` | full_folding relstats chunk30 | pi05 | 30 | true; gripper excluded | RABC + local full_folding SARM progress | processor exists; relaware gate validates stats | relaware PASS | FAIL for 002000/003000/004000 | not deploy | P3 |
| Tier 2 | D-8a continuation 001000-012000 | `/data/.../pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints/{001000..012000}/pretrained_model` | full_folding relstats chunk30 continuation from 003000 | pi05 | 30 | true; gripper excluded | RABC + local full_folding SARM progress | processor carried from 003000; no reset evidence | relaware PASS | FAIL for all 001000-012000 | not deploy | P3 |
| Tier 2 | `lerobot/pi05_base` | HF base/pretrain reference | broad pretraining, not OpenArm folding fine-tune | pi05 | not folding-specific | not OpenArm folding contract | none for current task | no OpenArm folding processor/action normalization | not run | not run | reference only | X |
| Tier 2 | `lerobot/pi0_base` | HF base/pretrain reference | broad pretraining, not OpenArm folding fine-tune | pi0 | not folding-specific | not OpenArm PI0.5 16D | none for current task | no OpenArm folding processor/action normalization | not run | not run | reference only | X |
| Tier 2 | `lerobot/pi05_libero_base` | HF/base reference | LIBERO/pretraining domain | pi05 | not OpenArm folding-specific | not verified for OpenArm 16D folding | none for current task | no OpenArm folding processor/action normalization | not run | not run | reference only | X |
| Tier 2 | `lerobot/xvla-folding` | HF reference / docs source | XVLA folding reference | xvla | not PI0.5 OpenArm contract | not OpenArm PI0.5 16D direct deploy | not applicable | not compatible with current PI0.5 serving path | not run | not run | reference only | X |

### Decision Inputs (사용자 결정 입력용)

- **D-13 입력**:
  feasibility 첫 라이브 세션에서 시도할 P1 ckpt 큐는 사용자가 직접 선정한다.
  자동 추천은 하지 않는다.
  사용자가 §9 의 P1 row 중 N개를 골라 큐를 정의한다.

- **D-1 (fold-only 4100 eps)**:
  Registry 분석 결과로 진행 가치 평가만 한다.
  자동 결정하지 않는다.

- **D-2 (curated mix)**:
  Registry 분석 결과로 진행 가치 평가만 한다.
  자동 결정하지 않는다.

- **D-8 (다음 학습 후보)**:
  P1 live 결과가 PROMISING / AMBIGUOUS / REJECTED 중 어디로 쌓이는지 본 뒤 결정한다.
  P1 이 모두 REJECTED 면 P2 재검증, P3 학습 추가, 또는 데이터 추가 수집으로 넘어간다.

- **D-11 (Phase 3 serving adapter 위치)**:
  `lerobot-rollout` 전환 시 A6000 HTTP 서빙 호환 adapter 를 server 쪽에 둘지 client 쪽에 둘지
  Phase 3 에서 별도 결정한다.

- **D-12 (OpenArmFollower 안전 패치 default)**:
  upstream 유지 vs 안전 모드 default 여부는 Phase 3 에서 별도 결정한다.
