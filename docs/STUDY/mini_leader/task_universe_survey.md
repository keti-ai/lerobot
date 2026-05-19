# Task Universe Survey — 양팔 데이터 수집/정책 프로젝트 4선

**Status:** Stage 1 draft (2026-05-19)
**Scope:** 미니 리더 산업 양팔 데이터 수집 플랫폼 설계에 참고할 외부 양팔 프로젝트 4선의 5요소 정리 + cross-cutting 인사이트.
**원칙:** 정확한 수치 (episode 카운트, 데이터셋 크기, DoF) 가 불확실하면 `≈`, 범위, 또는 `(확인 필요)` 로 표기. fabrication 금지.

---

## 1. Physical Intelligence — PI0 / PI0.5

| 요소 | 내용 |
|---|---|
| **Bimanual setup** | PI0/PI0.5 는 ALOHA-style bimanual (≈14-DoF, 6+gripper × 2) 와 Franka-class single arm 모두에서 시연. PI0 paper 는 다중 embodiment 포함. OpenArm (우리 16D = 7+gripper × 2) 보다 약간 작은 DoF 의 ALOHA 셋업이 대표. |
| **Task universe** | Multi-task generalist. 발표 시연: 옷 폴딩 (T-shirt, shorts), dish loading / unloading, packing groceries, table cleanup, drink pouring. soft (cloth) + rigid mixed. |
| **Data scale** | PI0 paper: 자체 + OpenX + 추가 데이터 합쳐 ≈ 10k hours scale (정확한 양팔 전용 ep 수 비공개). PI0.5 는 PI0 위에서 multi-task 확장 학습. |
| **Policy** | Vision-Language-Action (VLA), PaliGemma-class backbone + flow matching action expert. Task string per episode 로 language conditioning. action chunk 단위 출력. |
| **미니 리더 스터디 인사이트** | (a) 현재 우리 베이스 = `level2 corrected 004000` PI0.5 정책. task string conditioning 으로 산업 multi-task generalist 학습 자연스럽게 확장 가능. (b) PI0/PI0.5 의 large pretrain 이 vision/proprio prior 를 강하게 잡고 있으므로 init reuse fine-tune 이 효과적. (c) flow matching action expert + chunk30 contract 그대로 산업 데이터에 적용 가능. |

---

## 2. ALOHA / Mobile-ALOHA (Stanford)

| 요소 | 내용 |
|---|---|
| **Bimanual setup** | ALOHA = 14-DoF (ViperX-300 6-DoF + gripper × 2), low-cost leader-follower teleop (ViperX-200 leader). Cameras: top + bottom + wrist × 2 = 4개 (paper 기준). Mobile-ALOHA 는 동일 양팔 + AgileX mobile base. |
| **Task universe** | Cooking (egg flip, shrimp sauté), cleaning (wipe spill), Velcro fastening, putting on shoes, folding shorts, cup stacking, opening cabinet, picking up plates. Long-horizon contact-rich daily tasks. |
| **Data scale** | ALOHA paper: 태스크당 ≈ 50 demos, 총 6-10 태스크. Mobile-ALOHA: 태스크당 ≈ 50 demos, static ALOHA 데이터와 co-training. |
| **Policy** | ACT (Action Chunking Transformer, transformer encoder + CVAE), Diffusion Policy 변형. chunk_size ≈ 100. Per-task model 위주 (language conditioning 없음). lerobot `src/lerobot/policies/act/` 는 bimanual default 로 표기됨. |
| **미니 리더 스터디 인사이트** | (a) 우리 미니 리더 그 자체가 ALOHA leader-follower 패턴. teleop 방식이 거의 그대로 적용. (b) 50 demos / task 가 양팔 단일 태스크 baseline 의 기준점. industrial peg-in-hole / bolting 같은 contact-rich 태스크는 이 정도 규모로 ACT baseline 학습 가능. (c) PI0.5 이전 baseline 으로 ACT 가 빠른 prototyping 에 적합. (d) Mobile-ALOHA co-training 패턴 (static + mobile) 은 우리 case 의 follower 데이터 + 미니 리더 데이터 결합 운용에 시사점. |

---

## 3. RT-2 / RT-X / Open X-Embodiment (Google DeepMind + 다기관)

| 요소 | 내용 |
|---|---|
| **Bimanual setup** | RT-1 / RT-2 자체는 Everyday Robots 단일팔 위주. **Open X-Embodiment** (Open-X) 는 21+ 기관의 22+ embodiment 합본 데이터셋이며, 그 중 ALOHA, Bimanual UR5, 양팔 Franka 등 양팔 데이터 일부 포함. RT-X = RT-1-X / RT-2-X 는 Open-X 위에서 cross-embodiment 학습. |
| **Task universe** | 540+ skill labels, 1.1M+ episodes, manipulation 위주 generalist. 양팔 비중은 전체의 일부 (정확 비율 확인 필요). |
| **Data scale** | Open-X ≈ 1.1M episodes, 60+ 개별 데이터셋, 22 embodiments. |
| **Policy** | RT-2 = PaLI-X / PaLM-E 기반 VLA, action 을 token sequence 로 출력. RT-X = RT-1-X (smaller, more 실용), RT-2-X (큰 VLA). action discretization 으로 다른 embodiment 통합. |
| **미니 리더 스터디 인사이트** | (a) cross-embodiment mixing 의 가장 큰 사례. 결론: mixed pretrain 이 새 embodiment 에 zero-shot 을 보장하지는 않지만, 분포 친근성 (similar arm geometry, similar viewpoint) 이 클수록 transfer 효율이 큼. (b) 우리 follower vs 미니 리더 mismatch (16D 동일, bicep 만 다름) 는 Open-X 사례 평균 대비 **매우 작은 mismatch** → cross-embodiment 가 아닌 same-embodiment with kinematic 보정 수준. (c) **cross-domain mixing (cloth folding vs industrial)** 의 위험은 RT-X 가 다양한 robot 을 mix 한 것과 별개 축이며, 분포 차이가 큰 도메인의 단순 mixing 은 학습 신호를 오염시킨다 (RT-2/RT-X 의 일관된 관찰). (d) action discretization 자체는 우리 contract (`abs deg 16d`) 와 직교 — 차용할 필요 없음. |

---

## 4. Generalist VLA — Octo / SmolVLA / OpenVLA

| 요소 | 내용 |
|---|---|
| **Bimanual setup** | Octo, OpenVLA 모두 single-arm 7-DoF 위주 pretrain 이지만 fine-tune 으로 양팔 head 부착 가능. SmolVLA 는 lerobot 내 정책 (`src/lerobot/policies/` 영역). lerobot 내 bimanual robots (`bi_rebot_b601_follower`, `bi_openarm_*`) 와 호환 가능. |
| **Task universe** | OpenX 위 generalist (pick / place / open / pour / wipe 등). VLA 특성 상 language instruction 으로 태스크 분기. |
| **Data scale** | Octo: OpenX 800k+ trajectories pretrain. OpenVLA: 970k OpenX episodes. SmolVLA: compact 모델, fine-tune dataset 작아도 작동하도록 설계 (≈ 50-200 ep / task 권장 범위). |
| **Policy** | VLA (vision encoder + language encoder + action head). language conditioning native. action chunking 지원. SmolVLA 는 lightweight (수 B 파라미터 미만) 로 양팔 16D head 부착이 PI0.5 대비 빠르고 GPU 비용 낮음. |
| **미니 리더 스터디 인사이트** | (a) PI0.5 외의 후보 정책으로 **SmolVLA** 가 가장 매력적 — lerobot 내장 + language-cond + 작은 모델 → 산업 multi-task generalist 의 빠른 prototyping baseline 으로 적합 (정확한 양팔 16D 호환은 `src/lerobot/policies/` 확인 필요, Open question). (b) OpenVLA / Octo 는 OpenX pretrain 의 vision prior 가 강해 산업 환경 zero-shot 시각 distractor 에 robust. fine-tune init 후보. (c) generalist VLA 패턴 = 우리가 미니 리더로 산업 데이터를 모은 뒤 task string 으로 단일 정책 multi-task 학습하는 방향의 가장 직접적 baseline. |

---

## 5. Cross-cutting Takeaways

### 5.1 양팔 본질 태스크 공통 set

4 프로젝트 모두에서 양팔이 **실질적으로 필요한** 태스크는 다음 카테고리로 수렴.

1. **양손 안정화 + 한 손 정밀 조작** — peg-in-hole, connector mating, Velcro fastening, cap on/off.
2. **양손 동시 운반 / 운반 중 변형** — 큰 box lift, cloth lift, panel positioning, fabric flatten.
3. **Hand-off / 재파지** — 한 손 → 다른 손 전달, drop 없이 자세 변경.
4. **한 손 hold + 한 손 path** — cable routing, wire harness, hose coupling.
5. **양손 협조 도구 사용** — 도구 + 부품 동시 사용 (드라이버 + 스크류, 컵 + 따르기).

산업 도메인 매트릭스 (다음 산출물) 의 후보는 이 5 카테고리 안에 들어와야 한다.

### 5.2 데이터 효율 best practice

| 정책 | 태스크당 권장 ep | 학습 비용 | 비고 |
|---|---|---|---|
| ACT (per-task) | 50 ~ 100 | 작음 | 빠른 single-task baseline |
| PI0.5 fine-tune | 50 ~ 200 (init 후) | 중간 | language-cond multi-task 가능 |
| SmolVLA fine-tune | 50 ~ 200 | 작음 | lerobot 내장, 빠른 prototyping |
| OpenVLA fine-tune | 100 ~ 500 | 큼 | 큰 모델, GPU 비용 큼 |
| scratch (no pretrain) | 500 ~ 1000+ | 매우 큼 | 권장 안 함 |

산업 단일 태스크 ACT baseline 50-100 ep, multi-task generalist 의 경우 태스크당 50-200 ep × N tasks 가 reasonable starting envelope.

### 5.3 Multi-task language-cond 의 강점

PI0.5 / SmolVLA / OpenVLA 모두 task string 으로 분기 학습. 미니 리더로 산업 4 도메인의 여러 태스크를 모으면, **단일 정책에 모든 태스크 합쳐 학습** 가능. 태스크 별 별도 모델 N 개 운용 대비 운영 단순. 단, task string convention 사전 설계 필요 (예: `"Task: bimanual peg insertion of red peg into left hole, State: ..."`).

### 5.4 Cross-embodiment / Cross-domain mixing risk

- **Cross-embodiment** (다른 robot geometry mixing): RT-X / Open-X 사례. 분포 친근성 클수록 transfer 효율 큼. 우리 follower ↔ 미니 리더 는 16D contract 동일이라 cross-embodiment 위험 매우 작음 (=kinematic 보정 수준).
- **Cross-domain** (다른 task 분포 mixing, e.g. cloth folding vs industrial peg-in-hole): RT-2 / RT-X 의 ablation 들이 일관되게 보여주는 결론은 **분포가 너무 다른 domain 단순 mixing 은 학습 신호 노이즈** → 우리 case 에 적용하면 폴딩 데이터와 산업 신규 데이터의 단순 mixing 은 권장 안 함. 데이터 운용 전략 (다음 산출물 `data_strategy_two_tracks.md`) 의 핵심 결정 근거.

### 5.5 우리 case 에 적용

- **베이스 정책 1순위:** PI0.5 (현재 운용, language-cond, level2 init reuse 가능).
- **베이스 정책 2순위:** SmolVLA (빠른 prototyping, GPU 비용 ↓), ACT (single-task baseline).
- **데이터 수집 규모 기준:** 단일 산업 태스크 50-100 ep, multi-task generalist 시 태스크당 50-200 ep × 3-5 tasks.
- **임바디먼트 보정:** 16D contract 동일이라 작은 kinematic 보정만 필요. cross-embodiment 학습으로 처리할 수준 아님.
- **Cross-domain:** 폴딩 데이터셋 ↔ 산업 데이터셋 단순 mixing 권장 안 함. 자세한 운용은 `data_strategy_two_tracks.md`.

---

## 6. Open questions (다음 Stage 에서 해소)

| ID | 질문 | 해소 시점 |
|---|---|---|
| OQ-S-1 | SmolVLA 가 OpenArm 16D action head / language conditioning 을 native 로 지원하는가, head 확장이 필요한가? | Stage 4 dataset recipe 직전 |
| OQ-S-2 | PI0.5 fine-tune 시 chunk30 + 16D action contract 가 산업 contact-rich (peg-in-hole) 에서도 안정적인가? | Stage 2 short demo 후 |
| OQ-S-3 | ALOHA-style leader-follower 의 ViperX 보다 우리 미니 리더의 reach / payload 가 작을 가능성 — 산업 부품 무게 한계 | Stage 2 feasibility |
| OQ-S-4 | Open-X 의 양팔 부분만 추출해 우리 fine-tune init 보조로 쓸 수 있는가 (license, format) | Stage 4 직전 |
