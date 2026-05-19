# Data Strategy — 두 트랙 운용 (산업 신규 데이터셋 ↔ 기존 폴딩 자산)

**Status:** Stage 1 draft (2026-05-19)
**Scope:** 미니 리더로 수집할 산업 양팔 데이터셋과, 이미 보유한 폴딩 데이터 자산 (`level2_final_quality3_t_0_hil_data_c`, `lerobot/full_folding`, A6000 학습 산출물) 의 **운용 관계** 를 정의한다. 폴딩-종속 블랜딩 가정은 폐기. cloth vs industrial 의 분포 차이를 인지한 투트랙 운용으로 정리.
**관련 산출물:** `task_universe_survey.md`, `industrial_bimanual_task_matrix.md`.

---

## 0. TL;DR — Stage 1 추천

| 데이터 규모 | 추천 트랙 | 정책 후보 | 폴딩 자산 활용 |
|---|---|---|---|
| < 50 ep / task | **Track 2 — Pretrained-init reuse** | PI0.5 (`level2 corrected 004000` init), SmolVLA pretrain | weights 만, dataset 은 학습에 미사용 |
| ≥ 50 ep / task | **Track 1 — Clean separation** | PI0.5 (scratch / 산업 init), SmolVLA, ACT | 미사용 (완전 분리) |

**Cross-domain mixing** (cloth folding ↔ industrial) 은 **권장 안 함**. 근거 §3. 따라서 두 트랙 모두 폴딩 데이터셋을 학습 데이터로 직접 섞지 않는다. 차이는 "폴딩에서 학습된 weights 를 init 으로 쓰는가" 한 가지뿐.

---

## 1. 두 트랙 정의

### Track 1 — Clean Separation

```
[ 산업 데이터셋 신규 ]  ──► [ scratch 또는 industrial-only pretrain ]  ──► [ 산업 generalist policy ]
[ 폴딩 데이터셋 / 모델 ]  ─── 운영 분리 (영향 없음)
```

- 산업 데이터셋만으로 정책 학습 (scratch 또는 industrial-only init).
- 폴딩 데이터셋과 폴딩 학습 산출물 모두 학습 데이터/init 에 안 씀.
- PI0.5 일 경우 task string 으로 multi-task language-cond → 산업 generalist.
- ACT / SmolVLA 도 동일 dataset 위에서 baseline 으로 비교 가능.

### Track 2 — Pretrained-init Reuse

```
[ A6000 level2 corrected 004000 weights ]  ──► [ 산업 데이터셋 신규 ]  ──► [ fine-tune ]  ──► [ 산업 generalist policy ]
[ 폴딩 데이터셋 ]  ─── 학습 데이터 미사용 (영향 없음)
```

- A6000 level2 corrected 004000 (또는 동급 PI0.5 / SmolVLA pretrained checkpoint) 의 **weights** 를 init 으로 사용.
- 폴딩 데이터셋 자체는 학습 데이터에 포함하지 않음.
- 산업 데이터로 fine-tune (full / LoRA / partial layer 옵션).
- 효과는 vision encoder 의 manipulation prior + chunk30 action expert prior 재활용.

> Track 1 도 Track 2 도 **폴딩 데이터셋을 학습 데이터로 섞지 않는다** 는 점이 공통. 차이는 init weights 의 출처뿐.

---

## 2. 6축 채점 (Task Matrix 와 동일 축)

| Axis | Track 1 (Clean separation) | Track 2 (Pretrained-init reuse) |
|---|---|---|
| **A1 (≡ data efficiency)** ↑ | M (scratch 라 더 많은 데이터 필요) | **H** (init prior 가 산업 데이터 small set 에서 빠르게 수렴) |
| **A2 (≡ cross-embodiment robustness)** ↑ | M (산업 새 데이터로만 학습 → 미니 ↔ follower kinematic 학습이 부족할 수 있음) | M-H (PI0.5 init 이 follower 분포 친근) |
| **A3 (≡ task coverage / generalization)** ↑ | H (산업 분포 단일 학습 → 산업 generalist 가 깨끗) | M (cloth prior 가 잔존, 산업 새 태스크 학습 중 forget 위험 있음) |
| **A4 (≡ implementation complexity)** ↓ | L-M (단순 scratch, 산업 data 만) | L-M (init load 만 추가) |
| **A5 (≡ operational risk)** ↓ | M (initial epochs 동안 random action 시 first motion risk) | L (init 이 안정 manipulation 분포에서 시작) |
| **A6 (≡ gate/replay 호환)** ↑ | M (new model, gate/replay 새 baseline 필요) | M-H (PI0.5 contract 동일하므로 gate/replay 재사용 가능) |

**해석:** 작은 데이터 (< 50 ep / task) 환경에서는 A1, A5, A6 모두 Track 2 가 유리. 큰 데이터 (≥ 50 ep / task) 에서는 A3 의 cloth bias 문제와 forget 위험이 부각되어 Track 1 이 유리.

---

## 3. Cross-domain mixing 권장 안 함 — 근거

다음 4 근거로 폴딩 데이터셋 + 산업 데이터셋의 **단순 mixing** (sampler 합치기, naive blending) 은 Stage 1 에서 채택하지 않는다.

1. **분포 차이가 매우 큼.** cloth (T-shirt 옷감, soft, deformable, contact-rich-but-light, language: fold) 와 산업 (rigid box / cable / panel, hard contact, language: pick/place/insert/route) 은 vision, action style, 언어 라벨 모두 다르다. RT-2 / RT-X / Open-X 의 ablation 들이 일관되게 보여주는 결론은 **분포가 너무 다른 domain 의 단순 mixing 은 학습 신호 노이즈** 다 (`task_universe_survey.md` §5.4).

2. **현재 폴딩 데이터셋의 gate 상태.** `lerobot/full_folding` 은 replay FAIL 상태이며, level2 corrected 만 replay PASS 다. 분포 자체가 학습 신호로서 noisy 한 가능성이 있는 데이터셋을 산업 데이터와 mix 하면, 신규 산업 학습의 gate 통과 자체가 어려워진다. (`docs/STATUS.md` §1.)

3. **임바디먼트 mismatch 가 cross-domain mixing 의 noise 와 결합한다.** 미니 리더 ↔ follower 의 vision/bicep mismatch 가 있는 상태에서 cross-domain mix 까지 추가하면, 학습 모델이 분리해야 할 신호 축이 3개 (domain × embodiment × task) 로 증가. 신호 대비 noise 가 급격히 나빠진다.

4. **multi-task language-cond 만으로 generalist 가능.** PI0.5 / SmolVLA / OpenVLA 모두 task string 으로 분기 학습. 폴딩과 산업이 같은 모델에 들어가야 한다면 **task string 으로 분기** 하면 되고, 데이터셋 sampler 를 합칠 필요는 없다. 그러나 Stage 1 의 목표는 **산업 generalist** 형성이며 폴딩 학습 자산 (deploy 후보 정책) 은 이미 별도 트랙으로 운영 중이라 산업 학습에 폴딩 데이터를 끌어들일 이유가 없다.

> **결론:** mixing 은 안 한다. weights init 재사용 (Track 2) 만 허용한다. Stage 2/3 이후 산업 데이터셋이 충분히 크고 산업 generalist 가 안정화되면, 그때 폴딩 + 산업 multi-domain 학습을 별도 트랙으로 재검토할 수 있다 (현 단계 Out of scope).

---

## 4. 데이터 규모별 권장 트랙

| 산업 데이터 규모 | 권장 트랙 | 권장 정책 | 보조 권고 |
|---|---|---|---|
| 1 ~ 10 ep / task (탐색용) | **Track 2** | ACT per-task baseline + PI0.5 init fine-tune | language-cond 도입 보류, single-task baseline 만 |
| 10 ~ 50 ep / task (소규모 generalist) | **Track 2** | PI0.5 (`level2 corrected 004000` init) fine-tune | 2-3 산업 태스크 task string 으로 묶기 |
| 50 ~ 200 ep / task (중규모 generalist) | **Track 1** (or hybrid) | PI0.5 / SmolVLA scratch 또는 industrial-only init | task string multi-task 학습 본격화 |
| 200+ ep / task (full generalist) | **Track 1** | PI0.5 / OpenVLA scale-up | industrial pretrain 자체 형성 |

`industrial_bimanual_task_matrix.md` §4.1 의 P1 (L1, H1) 부터 수집 시작 → 초기 규모는 자연스럽게 < 50 ep / task 구간에 진입 → **Stage 1 추천 = Track 2** 로 시작한다.

---

## 5. 임바디먼트 mismatch 처리 옵션

`README.md §2` 의 mismatch (바이셉 kinematic, 카메라 vision) 를 두 트랙 어디에서나 처리해야 한다. 옵션:

| 옵션 | 적용 | 비용 | 권장 단계 |
|---|---|---|---|
| **M-A. State-level 흡수** (16D action label 그대로, bicep delta 는 정책이 학습) | 별도 처리 없음 | 0 | 항상 디폴트 |
| **M-B. Camera intrinsic / extrinsic 측정 + dataset-level metadata** | 측정 후 metadata 만 기록 | L | Stage 3 |
| **M-C. Camera aug (FOV crop / perspective jitter / color jitter)** | dataloader online aug 또는 dataset prep offline aug | L-M | Stage 4 |
| **M-D. Embodiment id conditioning** (state vector 에 1-hot `{follower, mini-leader}` 추가) | processor / RABC 입력 schema 변경 필요 | M-H | Stage 3 이후, mismatch 영향이 명확할 때만 |
| **M-E. Robot id-aware 별도 dataset 등록** (`bi_openarm_follower` vs `bi_openarm_mini_leader`) | dataset metadata level | L | Stage 4 |

**Stage 1 디폴트:** M-A (state-level 흡수) + M-E (robot id metadata 분리 기록). M-C 는 Stage 4 dataset recipe 에서 도입. M-D 는 Stage 3 mismatch 측정 후 영향이 큰 경우만.

---

## 6. Multi-task language-cond 적용 옵션

`industrial_bimanual_task_matrix.md` 의 P1 + P2 + P3 통과 태스크가 같은 미니 리더로 모이므로, 한 정책에 multi-task 학습이 자연스러움.

### 6.1 PI0.5 (Track 2 init reuse 의 자연스러운 선택)

- task string per episode 지원 (Phase 1 Explore 결과).
- `level2 corrected 004000` weights 가 follower 16D, chunk30, RABC processor 와 호환.
- 학습 변경 최소.

### 6.2 SmolVLA (lerobot 내장 generalist VLA)

- lerobot 내 정책 (`src/lerobot/policies/`), compact 모델, fine-tune 비용 낮음.
- language conditioning native.
- 산업 데이터 prototyping baseline 으로 PI0.5 보다 GPU 비용 ↓.
- 양팔 16D action head 의 native 지원 여부는 Open question (`task_universe_survey.md` OQ-S-1).

### 6.3 ACT (single-task baseline)

- bimanual default, lerobot `src/lerobot/policies/act/`.
- language conditioning 없음. single task per model.
- Stage 2 single-task quick baseline 으로만 사용.

### 6.4 task string convention (draft)

산업 4도메인을 일관된 format 으로 표기.

```
Task: bimanual <domain>:<action> of <object>, [<modifier>]
예시:
- "bimanual logistics:lift_and_place of cardboard_box"
- "bimanual handoff:transfer of m6_screw from right_arm to left_arm"
- "bimanual cable:route of usb_cable through left_clamp"
- "bimanual assembly:screw_driving of panel_assembly_1"
```

domain prefix vs 평탄 자연어 선택은 Stage 4 dataset recipe 에서 확정 (`industrial_bimanual_task_matrix.md` OQ-M-5 와 연결).

---

## 7. 운영 / 인프라 영향

| 항목 | 영향 |
|---|---|
| gate/replay (`stage22_dataset_replay_and_ablation.py`, `stage29_candidate_recipe_gate.py`) | 산업 데이터셋은 새 corpus 이므로 gate baseline 재설정 필요. Track 2 의 경우 PI0.5 init 이 PASS 이므로 fine-tune 후 회귀만 평가. Track 1 은 새 baseline. |
| A6000 학습 venv | 동일 venv (`venv312_torch27_20260515`) 재사용 가능. torch 2.7.1+cu126, pyav video backend. |
| A6000 서빙 (port 8766/8765) | 현재 운영 중인 폴딩 정책 미영향. 산업 정책은 별도 port 또는 별도 endpoint 로 분리 운용 권장 (Stage 4 결정). |
| HF cache | `HF_HOME=/mnt/nas/huggingface` 유지. 산업 데이터셋은 별도 namespace 권장. |
| Stage 2 의존성 | feasibility 프로토콜이 L1/H1 short demo 수집을 마쳐야 < 10 ep 시작점 확보. |
| Stage 3 의존성 | mismatch quantification 결과가 M-C/M-D 옵션 채택 여부를 결정. |
| Stage 4 의존성 | dataset_collection_recipe 가 §6.4 task string convention 과 §5 robot id metadata 분리를 dataset prep 단계에서 구현. |

---

## 8. Open questions

| ID | 질문 | 해소 시점 |
|---|---|---|
| OQ-D-1 | A6000 `level2 corrected 004000` weights 의 init reuse 가 cloth bias 를 산업 데이터 학습 중 얼마나 빠르게 잊는가 (forget curve) | Stage 4 첫 fine-tune 실험 후 |
| OQ-D-2 | SmolVLA / OpenVLA 가 우리 16D action head 와 RABC / SARM processor 호환 가능한가 | Stage 4 직전 (`task_universe_survey.md` OQ-S-1 과 동일) |
| OQ-D-3 | M-D embodiment id conditioning 을 도입한다면, 추론 시 follower 와 mini-leader 데이터 모두 사용한다는 가정인가, mini-leader teleop 으로만 수집해 follower 와 같은 robot id 로 표기할지 | Stage 3 |
| OQ-D-4 | Cross-domain mixing 을 미래에 검토한다면, 그 트리거 조건은 무엇인가 (산업 ep 수 임계, task string namespace 통합 등) | Stage 4 이후 별도 검토 |
| OQ-D-5 | A6000 학습 venv 에서 SmolVLA / OpenVLA fine-tune 이 GPU 4x RTX A6000 으로 가능한 모델 크기인가 | Stage 4 직전 |
