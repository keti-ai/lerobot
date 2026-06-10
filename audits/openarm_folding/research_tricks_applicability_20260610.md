# OpenArm 폴딩 — 최신연구 트릭 적용가능성 검토 + 재결론 (2026-06-10)

**스코프:** D07m 시점(STATUS.md 최신)의 막다른 길 진단을 *전제(re-derive 금지)* 로 두고, LeRobot async/RTC + VLA 최신연구(2024–2026)에서 적용가능한 트릭을 fan-out 웹리서치(6각도/21소스/98클레임) + adversarial 투표로 검증해 정리.
**독자:** 이 레포를 관장하는 Claude Code 에이전트 + 운영자(syh4661). 같이 판단·실행하라고 박제.
**관련 코드:** `src/lerobot/async_inference/policy_server.py:70-72` (RTC 상수), `audits/openarm_folding/k4_eval_runner.py:124-133` (`diag_handover_grip` 프로파일).
**선행 문서:** `docs/STATUS.md`(D07m), `audits/openarm_folding/feasibility_runs_20260609.md`, `audits/openarm_folding/lr_dataset_replay_20260610.md`, `docs/_archive/openarm_folding/a6000_k15_oom_recovery_20260610.md`.

---

## 0. 에이전트용 TL;DR

1. **현재 "안정 baseline(bf16/no-compile)"은 RTC를 *유효 구간 밖*에서 돌리고 있다.** 검증된 RTC 제약식 `d ≤ s ≤ H − d` 에 라이브 측정치를 넣으면 `d(15–27) > s(10)` 으로 위반. → **잔여 톡톡(tok-tok)의 구조적 원인은 cap 이 아니라 latency.**
2. **블로커가 두 개, 서로 직교한다.** (A) grasp 기하 = per-joint cap(D07n) 으로 처리, D07j 로 인과 확정. (B) inter-chunk smoothness = latency/RTC-window 문제, interpolation×3·horizon 튜닝으로 *못 고침*.
3. **D07n 의 성패를 톡톡으로 판정하지 마라.** D07n 은 블로커 A 전용. grasp 풀려도 톡톡 남는 게 정상(블로커 B 미해결).
4. **최고 레버 = latency `d` 를 `s=10` 아래로.** K15 compile(forward 288ms→`d≈9`)이면 `d≤s` 회복. OOM 완화 후 compile 재도입이 smoothness 의 결정타. 못 하면 `s` 를 측정 `d` 로 올리거나(요 `H≥2d`), 재학습 시 training-time RTC.
5. 검증된 트릭 표는 §3. **temporal ensembling 은 쓰지 마라(검증됨: 高-latency 에서 protective-stop 유발).** EXP soft-mask·interpolation×3·TE 회피는 *이미 정답*.

---

## 1. 핵심 발견 — RTC feasibility window 위반 (검증 3-0)

RTC 논문(Physical Intelligence, [arXiv:2506.07339](https://arxiv.org/abs/2506.07339) / [PDF](https://www.pi.website/download/real_time_chunking.pdf))의 제약식이 adversarial 3-0 으로 확정:

> execution horizon `s` 는 **`d ≤ s ≤ H − d`** 를 만족해야 한다. `d`=측정 inference delay(controller timestep), `H`=chunk 길이. 실제 per-chunk horizon = `max(d, s_min)`, `d = max(Q)`(최근 delay 버퍼 최댓값으로 보수적 추정).
> 원문: *"The execution horizon, s, is a hyperparameter constrained by d ≤ s ≤ H − d. … the actual horizon for a given chunk is max(d, s_min) where d is the delay … d = max(Q)."*

**우리 숫자 대입** (검증된 제약식 + 우리 측정치로부터의 산출):

| 항목 | 값 | 출처 |
|---|---|---|
| live forward latency `d` | 0.7–0.9 s | `feasibility_runs_20260609.md` (D07e max net latency 898ms 등) |
| 제어 루프 | ~21–30 FPS (dt 33–48 ms) | trial avg_fps 21.69 |
| **`d` (timestep 환산)** | **≈ 15–27 steps** | 0.7s/48ms ~ 0.9s/33ms |
| 현재 `execution_horizon` `s` | **10** | `policy_server.py:70` `_ROBOT_FOLDING_RTC_EXECUTION_HORIZON=10` |
| pi0.5 chunk `H` | ~50 | pi0/pi0.5 기본 action horizon |

→ **`d(15–27) > s(10)` → `d ≤ s` 위반.** frozen prefix(`d`)가 commit 한 실행 horizon(`s`)보다 길다 = 다음 chunk 도착 전에 큐가 inpainting 안 된 영역까지 소진. **interpolation×3 는 큐 starvation(되감김 느낌)만 메우고, RTC 가 부드럽게 이어붙일 overlap 자체가 degenerate 라 boundary 불연속(톡톡)은 못 고침.**

**K15 OOM 트레이드오프와의 연결 (코드 근거):**
- compile-on (K15, `eb32708a`): forward 288ms → 30fps `d≈9` → **`d≤s=10` 만족 ✓** (RTC 유효)
- compile-off (현 bf16, `policy_server.py:73-76` opt-in): live forward ~400–550ms → `d≈12–16` → **`d≤s=10` 위반 ✗**

> **결론: OOM 때문에 compile 을 끈 결정은 smoothness 에 중립이 아니라, smoothness 를 막는 바로 그 결정이다.** (K15 OOM recovery 문서는 latency 관점에서만 평가했고, RTC window 관점은 누락돼 있었음 — 이 노트가 그 갭을 채움.)

---

## 2. 재결론 — 두 개의 직교 블로커

이전 우선순위(STATUS.md 기조)는 cap 1순위 / latency 3순위. 연구 반영 시 **독립·동시 블로커 2개**로 재정리:

| 블로커 | 정체 | 상태 | 처리 | latency 의존? |
|---|---|---|---|---|
| **A — grasp 기하** | joint_4/wrist cap 이 top-down 각 throttle | **확정** (D07j arm65 로 각 재현) | per-joint cap = `diag_handover_grip`(D07n) | 무관 |
| **B — inter-chunk smoothness** | `d > s` 라 RTC 유효구간 밖 | **신규 확정(본 노트)** | latency `d` 컷 → `d≤s` 회복 | **본질** |

**D07n 은 블로커 A 만 건드린다.** grasp 가 풀려도 톡톡은 남을 공산이 크다 = D07n 실패가 아니라 블로커 B 미해결. **두 블로커를 같은 trial 성패로 묶지 말 것.**

이전 결론 중 *유지되는 것*: gripper mapping/cap 주원인 아님(LR replay 게이트), single-arm prompt 폐기(α'' handover-locked), interpolation×3 유지, horizon 10. *교정되는 것*: "톡톡은 cap/geometry/latency 혼재" → **톡톡은 거의 순수 latency(블로커 B)**, cap 은 grasp 각(블로커 A)에만 책임.

---

## 3. 트릭 적용가능성 표 (검증상태 + 태그 + 인용)

태그: **NOW**=지금 적용 / **IF-FAIL**=D07n 실패 또는 톡톡 잔존 시 / **RETRAIN**=어차피 재학습 시 / **AVOID**=쓰지 말 것.
검증: ✅=adversarial 투표 or 직접 fetch 대조 확정 / ⬜=primary 출처 확인됐으나 투표 미완(session limit) / ◐=부분.

| # | 트릭 | 태그 | 검증 | 근거 (출처/인용) |
|---|---|---|---|---|
| 1 | **latency `d` 를 `s=10` 아래로 — OOM 완화 compile 재도입(또는 동급 latency 컷: num_inference_steps↓, 입력해상도↓, KV-cache)** | **NOW** | ✅ | `d≤s` 제약 검증(3-0). K15 forward 288ms→`d≈9`. OOM 은 leftover-prefix 길이 변동→graph cache 폭증이 plausible → 입력 shape/prefix 길이 고정으로 재시도. **블로커 B 결정타.** |
| 2 | **execution_horizon 를 측정 `d` 에 맞춰 `s=max(d,s_min)`** | **NOW** | ✅ | 논문: 실제 horizon=`max(d,s_min)`, `d=max(Q)`(3-0). "10>20" 경험은 *둘 다 `d≤s` 위반인 깨진 구간*에서 나온 것. `d` 못 줄이면 `s≈d`(요 `H≥2d`). |
| 3 | **EXP soft-mask schedule 유지** | **NOW** | ✅ | soft>hard, 특히 `d` 작을 때(2-0). 현 `EXP`(`policy_server.py:72`)는 권장과 일치 — **건드리지 마라.** |
| 4 | **per-joint cap (D07n `diag_handover_grip`) 진행** | **NOW** | ✅(D07j) | 블로커 A. proximal 25 / wrist j4·5=65 / forearm j6·7=40 / gripper 40 (`k4_eval_runner.py:124-133`). **grasp 전용 해법으로만 기대.** |
| 5 | **temporal ensembling 회피(현행 유지)** | **AVOID** | ✅ | pi0.5 실기: TE(sparse/dense)는 +100/+200ms 에서 진동→로봇 protective stop, 실행 불가. RTC 는 +200ms robust(2-0). interpolation+RTC 채택·TE 미사용은 **정답.** |
| 6 | **guidance weight `β=n` 규칙 — narrow prior 엔 더 강하게** | **IF-FAIL** | ✅ | [Soare blog](https://alexander-soare.github.io/robotics/2025/08/05/smooth-as-butter-robot-policies.html): *"A narrower prior … requires a more aggressive guidance weight"*, *"rule of thumb … β=n scaling"*. 현 `n=10, max_guidance_weight=10` = **정확히 β=n**. handover=좁은 prior → grasp 풀렸는데 receive 흐리면 **finetune 전에 guidance 12~15 상향**부터 싸게. |
| 7 | **ACG (Action Coherence Guidance) — 학습 없는 test-time guidance** | **IF-FAIL** | ◐ | [arXiv:2510.22201](https://arxiv.org/abs/2510.22201): *"a training-free test-time guidance algorithm that improves action coherence"*, 제목 *"Flow-based VLA models"*, RoboCasa·DexMimicGen·real SO-101 평가 → LS2/CFG fallback 의 직접 선행연구. **단 "velocity field 를 CFG식 수정"이라는 메커니즘은 abstract 미기재 → 적용 전 전문 확인.** RTC guidance 와 같은 denoise loop → **off-by-default A/B 필수.** |
| 8 | **`chunk_size_threshold g≈0.7` cadence 튜닝 + aggregation(Replace/weighted-blend)** | **IF-FAIL** | ✅ | [async blog](https://huggingface.co/blog/async-robot-inference): *"send a new observation when queue length k drops below fraction g=k/H"*, *"g≈0.7 … set g=0.5 and tune"*, *"Replace: …newer predictions"*, *"temporal weights"*. **단 큐 트리거 시점일 뿐 `d>s` 구조는 못 고침** — #1 이 본질. |
| 9 | **소규모 finetune (LoRA/few-demo)로 handover 미세협응** | **IF-FAIL** | ⬜미소싱 | STATUS.md fallback 과 동일. few-demo 신뢰도/forgetting 은 연구가 session limit 으로 미도달 → 추후 검증 과제. |
| 10 | **Training-time RTC / action-prefix conditioning** | **RETRAIN** | ✅ | [arXiv:2512.05964](https://arxiv.org/abs/2512.05964) "Training-Time Action Conditioning for Efficient Real-Time Chunking": *"simulating inference delay at training time and conditioning on action prefixes directly, eliminating any inference-time overhead"*, *"training-time RTC outperforms inference-time RTC at higher inference delays"*. **우리 0.7–0.9s 高-latency 정조준.** #9 재학습과 **한 번에 합칠 수 있는 콤보**(재학습할 거면 inference-time RTC 보다 우수). |

**폐기/회피 유지:** single-arm prompt(handover-locked), uniform arm cap 65(jump/snap), TE.

---

## 4. 다음 행동 (재정렬)

1. **D07n 예정대로 실행 — 단 판정은 grasp(블로커 A)만.** 톡톡 잔존은 D07n 실패 아님.
2. **블로커 B 를 별도 트랙으로 분리.** k4_eval_runner 에 **live forward latency 를 controller-step `d` 로 로깅** 추가 → `s=10` 과 비교. `d>10` 확인(거의 확실)되면 RTC 무효구간 명시.
3. **최고 레버: OOM-완화 compile 재도입** (입력 shape/leftover-prefix 길이 고정으로 graph cache 폭증 차단) → forward ~330ms 아래 → `d≤s=10` 회복. 안 되면 `s` 를 측정 `d`(~15–25)로 올리고 `H≥2d` 확인(#2).
4. **D07n PASS + 톡톡 잔존** → CFG/guidance(#6/#7) 이전에 **먼저 latency(#1/#3) 를 보라.** 톡톡은 grounding 이 아니라 RTC window.
5. **D07n FAIL** → handover 미세협응을 #9(소규모 finetune) 또는 #10(training-time RTC, 재학습 겸). #9+#10 콤보 권장.

---

## 5. 검증 메타데이터 (신뢰도 경계)

- **방법:** deep-research 워크플로(6각도 WebSearch fan-out → 21소스 fetch → 98클레임 추출 → 25클레임 3-vote adversarial 검증). 6 confirmed / 19 killed. **단 19 killed 중 18 은 genuine refute 가 아니라 session-limit 으로 인한 abstain(0-0)** — "거짓"이 아니라 "미검증". 1건만 약한 refute(beta-clipping 메커니즘 설명, 1-0).
- **synthesis 단계는 session limit(7:40pm KST 리셋)으로 중단** → 본 노트의 synthesis 는 메인 에이전트가 직접 수행.
- **표 #6/#7/#8/#10 은 워크플로 후 메인 에이전트가 4회 직접 WebFetch 대조로 확정**(토큰 절약 위해 워크플로 재실행 대신).
- **adversarial 투표로 확정된 6 클레임:** RTC inference-time/no-retrain 적용성(3-0), RTC overlap 동작(3-0), plain chunking→boundary jerk(2-1), `d≤s≤H−d` 제약(3-0), soft>hard mask(2-0), TE 高-latency 실패/RTC robust(2-0).
- **미해결 검증:** #9(few-demo finetune 신뢰도), action-space 대안(EE-space vs joint-space) 상세, BID/streaming diffusion 비교 — session limit 으로 미도달. 필요 시 추가 1-fetch.
- **`d≤s` 위반 산출은 검증된 제약식 + 우리 측정치로부터의 메인 에이전트 계산**(논문이 우리 숫자를 직접 말한 게 아님). `d` 의 실제 timestep 환산은 라이브 로깅(#4-2)으로 확정 권장.
- Soare blog 의 inpainting soft-mask 가 "RTC prefix attention 과 동일 메커니즘"이라는 등치는 메인 에이전트 추론(블로그 직접 진술 아님). 메커니즘 유사성은 사실.

## 6. 출처

- [arXiv:2506.07339](https://arxiv.org/abs/2506.07339) — Real-Time Action Chunking with Large Models (RTC, primary)
- [pi.website RTC PDF](https://www.pi.website/download/real_time_chunking.pdf) — `d≤s≤H−d`, soft-mask, TE 비교 (primary)
- [arXiv:2512.05964](https://arxiv.org/abs/2512.05964) — Training-Time Action Conditioning for Efficient RTC
- [arXiv:2510.22201](https://arxiv.org/abs/2510.22201) — Action Coherence Guidance (flow-VLA, training-free)
- [Soare: Smooth as butter robot policies](https://alexander-soare.github.io/robotics/2025/08/05/smooth-as-butter-robot-policies.html) — β=n, narrow-prior guidance
- [HF: async-robot-inference](https://huggingface.co/blog/async-robot-inference) — chunk_size_threshold g, aggregation
- [arXiv:2408.17355](https://arxiv.org/abs/2408.17355) — Bidirectional Decoding (consistency-reactivity tradeoff, 미검증)
