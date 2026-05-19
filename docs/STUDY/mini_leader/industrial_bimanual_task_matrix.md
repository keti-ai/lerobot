# Industrial Bimanual Task Matrix — 양팔 본질 산업 태스크 후보

**Status:** Stage 1 draft (2026-05-19)
**Scope:** 미니 리더로 OpenArm 16D follower 위에서 수집할 산업 양팔 태스크 후보를 4도메인(조립/제조, 물류/PnP, 케이블/흐름적, hand-off/도구) 에 걸쳐 정리하고, **한 팔로는 완전히 불가능** 필터로 1차 거른 뒤 6축 채점한다.
**관련 산출물:** `task_universe_survey.md`, `data_strategy_two_tracks.md`.

---

## 0. TL;DR — Stage 1 추천

| 우선순위 | 태스크 (도메인) | 이유 |
|---|---|---|
| **P1** | **양손 box / 파우치 lift & place** (물류/PnP) | 양팔 필수 H, 산업 가치 H, 미니 데모 난이도 L-M, contact-rich 아님 → 운영 risk 작음. 첫 산업 데이터셋 형성에 가장 합리적. |
| **P1** | **한 손→다른 손 부품 hand-off** (hand-off) | 양팔 필수 정의 그 자체, 산업 hand-off lines 직접 적용 가능. contact-rich 정밀도 요구 낮음. |
| **P2** | **한 손 connector hold + 한 손 cable routing** (케이블/흐름) | 산업 가치 매우 H, 양팔 필수 H. 케이블 deformable 이라 vision robustness 일부 손해. |
| **P3** | **한 손 panel hold + 한 손 screw/fastener 동작** (조립/제조) | 산업 가치 매우 H. 정밀도/contact 요구가 높아 미니 데모 난이도 M-H. 양팔 본질 + 활용 무궁무진. |
| **Defer** | peg-in-hole 정밀, bolting (toque-control), large rigid panel positioning | 미니 리더 reach / payload / 정밀도 한계 가능. Stage 2 feasibility 확인 후 결정. |

상세 근거는 §3 (필터 후 후보표) 와 §4 (추천 + open questions).

---

## 1. 평가 축 (6 axes)

§3 의 후보 모두 동일한 6축으로 H/M/L 채점.

| Axis | 의미 | 채점 방향 |
|---|---|---|
| **A1 양팔 필수성** | 한 팔로는 완전히 불가능한가 (constraint 관점) | **H 만 통과** (1차 필터) |
| **A2 산업 적용성** | 공장 / 물류 / 제조 라인의 실제 활용 가치, 일반화 가능성 | ↑ |
| **A3 미니 데모 난이도** | 미니 리더로 사람이 teleop 으로 안정 demo 가능한 정도 | **↓ (낮을수록 좋음)** |
| **A4 vision robustness** | follower ↔ 미니 카메라 mismatch 와 배경/조명 변화 흡수 | ↑ |
| **A5 데이터 가치** | 양팔 데이터의 희소성, generalist 학습 신호 | ↑ |
| **A6 운영 risk** | operator-on-site + power abort 기준 첫 motion 충돌/낙하 위험 | **↓** |

A1 H 만 후보로 인정. 이 필터를 적용한 후보표가 §3.

---

## 2. 도메인별 후보 (필터 전, 양팔 본질성 점검)

각 도메인 후보의 양팔 본질성(A1) 만 먼저 평가. H 가 아닌 후보는 후속 매트릭스에서 제외.

### 2.1 조립/제조

| ID | 태스크 | A1 양팔 본질성 | 한 팔로? | 후속 통과 |
|---|---|---|---|---|
| C1 | **panel hold + screw / fastener driving** (한 손 panel 잡고 한 손 fastener) | **H** | 부품이 흔들려 단팔 불가능 | ✓ |
| C2 | **connector mating** (한 손 connector body + 한 손 cable 끼움) | **H** | 한 손으로는 정확한 alignment 불가 | ✓ |
| C3 | **peg-in-hole** (정밀 끼움, 한 손 고정 + 한 손 삽입) | **H** | 부품 흔들리면 hole 정렬 안 됨 | ✓ |
| C4 | **bolting** (한 손 너트 holding + 한 손 볼트 driving) | **H** | 너트가 회전 자유라 단팔 불가능 | ✓ |
| C5 | **threaded cap on/off** (한 손 본체 + 한 손 cap turning) | **H** | 본체 회전 방지 위해 단팔 불가능 | ✓ |
| C6 | single screw driving on fixed jig | L (jig 가 fixation 대신함) | 가능 | × |

### 2.2 물류 / 피앤플레이스

| ID | 태스크 | A1 양팔 본질성 | 한 팔로? | 후속 통과 |
|---|---|---|---|---|
| L1 | **양손 box / 큰 파우치 lift & place** (한 손 그립 불가능한 사이즈/무게) | **H** | 한 손으로는 잡히지 않거나 떨어짐 | ✓ |
| L2 | **양손 bag manipulation** (한 손 입구 벌림 + 한 손 내용물 삽입) | **H** | 한 손은 bag 입구를 벌리지 못 함 | ✓ |
| L3 | **large flat item / panel 양손 운반** (한 손으로 잡히지 않는 사이즈) | **H** | 한 손 그립 면적 부족 | ✓ |
| L4 | **양손 협조 stacking** (큰 박스 정렬, 한 손 정렬 + 한 손 push) | **H** | 정렬과 push 동시 안 됨 | ✓ |
| L5 | small box single-arm PnP | L | 가능 | × |

### 2.3 케이블 / 흐름적 (deformable but linear)

| ID | 태스크 | A1 양팔 본질성 | 한 팔로? | 후속 통과 |
|---|---|---|---|---|
| K1 | **connector hold + 한 손 cable routing** (한 손 끝단 고정 + 한 손 경로 따라 통과) | **H** | 한 손은 cable 변형 제어 불가 | ✓ |
| K2 | **양손 hose / tube coupling** (한 손 hose + 한 손 fitting 정렬 후 결합) | **H** | 양쪽 부품 동시 정렬 필요 | ✓ |
| K3 | **양손 wire harness 정리** (한 손 harness 잡고 한 손 strap / clip) | **H** | 한 손은 harness 풀림 제어 불가 | ✓ |
| K4 | **케이블 끝단 → 슬롯 삽입 with strain relief** (한 손 strain relief hold + 한 손 insertion) | **H** | 부드러운 cable 의 buckling 제어 단팔 불가능 | ✓ |
| K5 | single-cable laying on table | L (단순 직선) | 가능 | × |

### 2.4 Hand-off / 도구 / 재파지

| ID | 태스크 | A1 양팔 본질성 | 한 팔로? | 후속 통과 |
|---|---|---|---|---|
| H1 | **한 손 → 다른 손 부품 hand-off** (전달) | **H** | 정의상 양팔 필수 | ✓ |
| H2 | **재파지 re-orient** (drop 없이 자세 변경, 한 손 hold + 한 손 re-grasp) | **H** | drop 허용 안 하면 단팔 불가능 | ✓ |
| H3 | **양손 도구 + 부품** (한 손 driver, 한 손 screw / part) | **H** | 도구를 들고 부품을 동시 조작 필요 | ✓ |
| H4 | **도구 → 도구 swap** (한 손 도구 사용 중 다른 손이 새 도구 받음) | M-H | 작업 종료 후 단팔 순차 가능 (다만 cycle time 손해) | △ |
| H5 | put down → pick up same tool with same hand | L | 가능 | × |

---

## 3. 필터 후 후보표 (A1 = H 만 채택, 6축 채점)

각 셀 점수는 작성 시점 가정 기반. Stage 2 feasibility 결과로 조정.

| ID | 태스크 (도메인) | A1 | A2 산업 | A3 데모난이도 ↓ | A4 vision robust | A5 데이터가치 | A6 risk ↓ | 종합 |
|---|---|---|---|---|---|---|---|---|
| **L1** | 양손 box/파우치 lift & place (물류) | H | **H** | **L** | **H** (rigid) | M-H | **L** | **◎ P1** |
| **L2** | 양손 bag manipulation (물류) | H | M-H | M | M (bag 변형) | H | M | ○ P2 |
| **L3** | large flat item 양손 운반 (물류) | H | M-H | M | H | M | M | ○ P2 |
| **L4** | 양손 stacking (물류) | H | M | M | H | M | M | △ P3 |
| **K1** | connector hold + cable routing (케이블) | H | **H** | M-H | M (cable 변형) | **H** | M | **○ P2** |
| **K2** | 양손 hose coupling (케이블) | H | H | M-H | M | H | M | ○ P2 |
| **K3** | 양손 wire harness 정리 (케이블) | H | M-H | M-H | L-M (얽힘) | H | M | △ P3 |
| **K4** | cable end + strain relief insertion (케이블) | H | H | H | L-M | H | M-H | △ Defer |
| **C1** | panel hold + screw driving (조립) | H | **H** | M-H | H (rigid) | H | M-H (torque) | ○ **P3** |
| **C2** | connector mating (조립) | H | H | M-H | M-H | H | M | ○ P3 |
| **C3** | peg-in-hole (조립, 정밀) | H | **H** | **H** (정밀도) | H | **H** (contact-rich 학습) | M-H (jam 위험) | △ Defer |
| **C4** | bolting (조립) | H | H | **H** (토크/회전) | M-H | H | **H** (torque) | × Defer |
| **C5** | threaded cap on/off (조립) | H | M-H | M-H | M-H | M | M | △ P3 |
| **H1** | 한 손 → 다른 손 hand-off | H | H | **L-M** | **H** (rigid) | **H** | **L** | **◎ P1** |
| **H2** | 재파지 re-orient (drop 없이) | H | H | M | H | H | M | ○ P2 |
| **H3** | 양손 도구 + 부품 | H | M-H | M-H | M-H | M | M | △ P3 |

---

## 4. Stage 1 추천 + 근거

### 4.1 P1 (Stage 2 feasibility 1차 대상)

- **L1 — 양손 box / 파우치 lift & place** (물류)
  - 양팔 필수성 H, 산업 가치 H, contact-rich 아님 → 운영 risk L.
  - 미니 reach 한계만 점검하면 안전. 산업 generalist 학습의 가장 깨끗한 entry.
- **H1 — 한 손 → 다른 손 부품 hand-off**
  - 양팔 본질 정의 그 자체. 산업 라인의 보편 동작.
  - rigid object 라 vision robustness 좋고, contact-rich 충돌 risk 작음.

이 두 태스크는 미니 도착 후 첫 short demo 로 즉시 검증 가능.

### 4.2 P2 (P1 안정화 후, Stage 2-3 동안)

- **K1 — connector hold + cable routing** (케이블, 산업 가치 매우 H).
- **K2 — 양손 hose coupling** (케이블).
- **L2 — 양손 bag manipulation** (물류).
- **L3 — large flat item 양손 운반** (물류).
- **H2 — 재파지 re-orient** (hand-off 확장).

### 4.3 P3 (Stage 3 mismatch 보정 + 정밀도 검증 후)

- **C1 — panel hold + screw driving** (조립, 산업 가치 매우 H, 정밀도 검증 필요).
- **C2 — connector mating** (조립).
- **C5 — threaded cap on/off** (조립).
- **K3 — wire harness 정리** (deformable 정리).

### 4.4 Defer / 제외

- **C3 peg-in-hole, C4 bolting, K4 cable insertion w/ strain relief** — 미니 리더 정밀도 / payload / torque 한계가 보일 가능성. Stage 2 short demo 에서 reach/precision 한계 확인 후 재평가.

---

## 5. 다음 단계와의 연결

- **`data_strategy_two_tracks.md`** 의 데이터 규모별 권장 (< 50 ep / ≥ 50 ep) 은 §4 의 우선순위 그대로 적용한다.
- **Stage 2 `feasibility_protocol.md`** 의 short demo 후보 = §4.1 의 L1 + H1.
- **Stage 3 `mismatch_quantification_plan.md`** 의 정밀도 영향 평가는 §4.3 (C-* 조립) 진입 직전 수행.
- **Stage 4 `dataset_collection_recipe.md`** 의 task string convention (PI0.5 multi-task language conditioning) 은 §4.1 ~ §4.2 의 통과 태스크 set 기준으로 설계.

---

## 6. Open questions

| ID | 질문 | 해소 시점 |
|---|---|---|
| OQ-M-1 | 미니 리더의 reach / payload 가 L1 box (예상 1-3kg 사이즈) 를 안정 lift 가능한가? | Stage 2 short demo |
| OQ-M-2 | H1 hand-off 의 grasp/release timing 이 chunk30 contract 안에서 안정적인가? | Stage 2 short demo |
| OQ-M-3 | K1 / K2 의 deformable cable / hose 가 카메라 미스매치 영향을 얼마나 받는가? | Stage 3 mismatch quantification |
| OQ-M-4 | C1 screw driving 시 발생하는 gripper 회전 torque 가 미니 리더 dm4310 gripper 한계 내인가? | Stage 3 |
| OQ-M-5 | task string convention 에 도메인 prefix (`industrial:logistics:`, `industrial:cable:`, ...) 를 둘지, 평탄한 자연어로 둘지 | Stage 4 dataset recipe |
| OQ-M-6 | C3/C4 정밀 조립 후보의 운영 risk 회피를 위해 jig 보조를 허용할지 (jig 가 양팔 본질성 A1 을 침해할 가능성) | Stage 3 |
