# Mini-leader Study (OpenArm 16D 양팔 — 산업 양팔 일반화 데이터 수집)

**Owner:** syh4661
**시작:** 2026-05-19 (v0 폴딩 종속 폐기, 산업 일반화로 재정의)
**격리 정책:** 이 디렉토리 외부 파일(`docs/PLAN.md` / `docs/STATUS.md` / `audits/` / `docs/_archive/` / `src/`) 은 read-only 참조만. 다른 세션의 Phase 1/2/3 진행을 방해하지 않는다.

---

## 1. 스터디 목적

OpenArm 16D 양팔 follower 위에서 작동하는 **미니 리더팔(제작 중)** 을, 옷 폴딩
보조 수단이 아니라 **산업 현장에서 활용 가능성이 무궁무진한 양팔 데이터 수집
플랫폼** 으로 사용한다. 이 스터디는 두 질문을 푼다.

1. **Q1 (Task)** — 한 팔로는 **완전히 불가능한** 양팔 본질 태스크 중, 산업 현장
   적용 가치가 큰 후보는 무엇인가? PI / ALOHA / Mobile-ALOHA / RT-2 / RT-X /
   Open X-Embodiment / Octo / SmolVLA / OpenVLA 사례를 참조한다.
2. **Q2 (Data strategy)** — 미니 리더 신규 데이터셋과 기존 폴딩 자산
   (`level2_final_quality3_t_0_hil_data_c`, `lerobot/full_folding`) 의 운용
   관계. 폴딩-종속 블랜딩 가정은 폐기. cloth 와 산업 도메인 분포 차이를
   인지한 투트랙 운용으로 정리.

대상 산업 도메인 (사용자 선택, 광범위):
- 조립/제조 (peg-in-hole, bolting, panel positioning, connector mating).
- 물류 / 픽앤플레이스 (박스/파우치/큰 물체 양손 취급).
- 케이블 / 흐름적 대상 (와이어 routing, hose coupling, 한 손 hold + 한 손 path).
- Hand-off / 도구 전달 / 재파지 (한 손→다른 손 전달, re-orient).

---

## 2. 임바디먼트 차이 (확정)

| 항목 | follower | mini leader | mismatch 유형 |
|---|---|---|---|
| 조인트 수/순서 | 16D, right(7+1) + left(7+1) | 16D, right(7+1) + left(7+1) | **없음** — encoding 호환 |
| 그리퍼 사양/범위 | `[-65, 0] deg` | 동일 | **없음** — `gripper.pos` 직접 매핑 |
| 바이셉(상완) 링크 | 정상 follower 사양 | follower 와 다름 (업데이트 미반영) | **kinematic** — end-effector 위치/도달 영역 차이 |
| 카메라 구성/위치/FOV | base + left_wrist + right_wrist (production setup) | 구성/마운트/FOV 모두 변경 가능 | **vision** — 입력 분포 shift |

action/state contract `openarm_folding_abs_16d_deg_v1` (absolute degrees,
chunk30) 은 그대로 사용 가능하다고 가정한다. 단, 같은 joint angle 입력이라도
바이셉 링크 길이가 달라 end-effector 위치는 달라지므로 **action label 이 같아도
visual outcome 은 다르다.** 이 사실이 데이터 운용 전략의 핵심 제약이다.

---

## 3. 산출물

### Stage 1 (현재)

| 파일 | 역할 | 상태 |
|---|---|---|
| [`task_universe_survey.md`](./task_universe_survey.md) | PI / ALOHA / RT-X / Octo·SmolVLA·OpenVLA 양팔 프로젝트 서베이 + 인사이트 | 작성 완료 |
| [`industrial_bimanual_task_matrix.md`](./industrial_bimanual_task_matrix.md) | 산업 4도메인 양팔 본질 태스크 후보 매트릭스 (한 팔로 불가능 필터) | 작성 완료 |
| [`data_strategy_two_tracks.md`](./data_strategy_two_tracks.md) | 데이터셋 운용 두 트랙 (Clean separation vs Pretrained-init reuse) | 작성 완료 |

### Stage 2+ (예정, 본 stage 에선 placeholder 만)

| 파일 | 단계 |
|---|---|
| `feasibility_protocol.md` | Stage 2 — 미니 리더 도착 후 dry-run / replay / short demo 프로토콜 |
| `mismatch_quantification_plan.md` | Stage 3 — 카메라 intrinsic / FOV / link length 측정 + 보정 옵션 |
| `dataset_collection_recipe.md` | Stage 4 — 선정 태스크의 episode 수, camera config, action chunk, 라벨링 컨벤션, A6000 prep 명령 |

---

## 4. 외부 의존 / 참조 (read-only)

- **SSOT:** `docs/PLAN.md`, `docs/STATUS.md`.
- **운영 baseline:** 공식 `lerobot-rollout` (Phase 3 전환 준비 중).
- **현재 deploy 후보 정책:** A6000 level2 corrected 004000 (`http://10.252.205.103:8766`).
- **A6000 학습 venv:** `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`.
- **양팔 follower 코드 패턴:** `src/lerobot/robots/bi_rebot_b601_follower/` (left_/right_ prefix composition).
- **양팔 leader 코드 패턴:** `src/lerobot/teleoperators/bi_openarm_leader/` (미니 리더가 mimic 할 모델).
- **language-conditioned 정책:** `src/lerobot/policies/pi05/` (task string per episode), `src/lerobot/policies/multi_task_dit/`, `src/lerobot/policies/act/` (bimanual default).
- **camera config schema:** `src/lerobot/cameras/configs.py` (dataset/robot-level 정적, per-episode 전환 미지원).

---

## 5. 변경 이력

| 날짜 | 변경 | 비고 |
|---|---|---|
| 2026-05-19 | Stage 1 시작, 폴딩 종속 v0 폐기, 산업 양팔 일반화 방향으로 재정의 | README + 3 산출물 (`task_universe_survey.md`, `industrial_bimanual_task_matrix.md`, `data_strategy_two_tracks.md`) 작성 |
