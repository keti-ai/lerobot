# D-42 Live Deploy — 적용 방법 총망라 (첫 banana grasp 성공 시점 박제)

**작성**: 2026-06-11
**상태 flag**: 🟡 **banana grasp 가 "가끔 한 번" 됨 (occasional, 불안정)**. 풀린 것 아님 —
움직임 여전히 안 부드러움(톡톡 잔여), grasp 각도/방향 커버리지 갭 큼. 여기서 deploy 설정만
고정, 본질(안정성·smoothness·grasp coverage)은 미해결로 추후.
**목표**: OpenArm 16D 양팔 + PI0.5 로 real-world handover pick & place. north star = N=20 중 70% (현재 거리 멂).

> **정직한 현실 (사용자 확인)**: deploy 튜닝으로 "한 번도 안 되던 것 → 가끔 됨" 까지 왔을 뿐.
> ① 성공률 매우 낮음(겨우 1회급) ② 움직임 거침(톡톡 spike 잔여) ③ **정책이 학습한 grasp
> 각도/방향 영역에 모르는 부분이 많음(커버리지 미측정 = 미지)**. 아래 "방법"은
> never→occasional 의 개선이지 task 해결이 아님. 다음 방향은 §5.5 열린 옵션 풀에서 추후 결정.

---

## 1. 시스템 아키텍처

```
[syhlabtop = robot client]                      [a6000 = policy server]
 bi_openarm_follower (CAN0/1, PEAK PCAN-USB FD)   PI0.5 α'' (030000)
 RealSense ×3 (left/right wrist + base)    ──gRPC──▶  RTC denoise + reanchor
 robot_client / k4_eval_runner            ◀─8081──   torch.compile, bf16
```
- **두 머신 분리 (robot=syhlabtop / GPU=a6000)** 라 rollout 불가 → **async_inference gRPC** 가
  유일 경로. client 는 thin (obs 전송 + action 실행), 추론·RTC 는 server.
- 모델 = **α''** = `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime` ckpt 030000
  (60ep clean handover 3-object: banana/olive cup/blue toothpaste, relstats relative-action chunk30).

---

## 2. 적용 방법 총망라 (카테고리별)

### A. 서빙 / 아키텍처
| 방법 | 내용 | 커밋/태스크 |
|---|---|---|
| async gRPC 파이프라인 | a6000 policy_server(8081) + syhlabtop robot_client | K1 |
| **RTC (Real-Time Chunking) 서버 통합** | PI0.5 내장 RTC 를 async server 에 이식: prev chunk reanchor(`reanchor_relative_rtc_prefix`) + guidance soft-blend. robot-folding 방법론 | K7 (e9cb3230) |
| 정책 재사용 guard | client handshake 시 이미 로드된 compiled 정책 재사용 (재warmup 회피, setup 0.876ms) | WB2 |

### B. Latency / smoothness — RTC feasibility window 복원
**핵심 이론 (RTC 논문)**: `d ≤ s ≤ H − d` (s=execution_horizon, d=inference delay[step], H=chunk 길이).
window 밖이면 chunk 경계 불연속(톡톡) + 미세 보정 댐핑.

| 방법 | 내용 | 결과 |
|---|---|---|
| 서버 warmup | autograd/CUDA cold 1-2회 discard | K8a |
| client IndexError 방어 | empty queue 안전 처리 | K8b |
| **action interpolation ×3** | 선형 보간으로 control rate 3배 → queue starvation 해소 | K10 (queue_empty 19→0) |
| latency breakdown | client(K12)/server(K13) — 병목 = forward 자체 | K12/K13 |
| **bf16 서빙** | autocast bf16 (vision/proj/norm fp32 유지) | K14 (413→396ms) |
| **torch.compile** | PI0.5 native compile (fused 커널) → forward↓ | K15 (→288ms) |
| **compile OOM fix** | prev_chunk_left_over 고정길이 pad → graph cache 안정 (재컴파일 0, mem flat) | MB2 (46c05ab2) |
| **execution_horizon 튜닝** | 20→10(K11, 깨진 구간 착시)→**15(WB1, bf16)**→**20(WB2, compile)** | WB1/WB2 |
| **최종 window 충족** | H=30, d≈9(compile), **s=20 → 9≤20≤21 ok_rate 1.0**, forward 210ms | WB2 (5b3ca18c) |

핵심: **compile 로 d 14→9 → window 천장 16→21 상승 → horizon 20 까지 길게 → 부드러움 + spike 여유.**

### C. Grasp geometry — per-joint cap (max_relative_target) 튜닝
**핵심 발견**: joint_4(손목) cap 이 top-down grasp 각을 throttle 하고 있었음.

| 방법 | 내용 | 결과 |
|---|---|---|
| cap = float | max_relative_target 정수 5 → TypeError, 5.0 필요 | K1 |
| **arm cap 15→65** | joint_4 손목 풀어 **top-down 각 재현** | D07j (clamp 0) |
| **gripper cap 65→20** | "팡" 급폐 → banana 쳐냄 → gentle close | D07k |
| **per-joint cap** | 손목(j4/5)=65 자유, 어깨/팔꿈치(j1/2/3)=25 smoothing, 전완(j6/7)=40 | D07l (diag_perjoint_smooth) |
| **handover 그리퍼 절충** | gripper cap 40 (pick gentle + handover 받기 decisive) | D07n (diag_handover_grip) — **왼손 받기 성공** |

### C-2. TS1 고주파 궤적 스트리밍 (2026-06-12 확정 — interp×3 대체)
| 방법 | 내용 | 결과 |
|---|---|---|
| **trajectory streamer 100Hz** | 전용 스레드가 VLA setpoint(30Hz)를 per-joint vel/acc 제한 trapezoidal 로 추적해 모터 명령 스트리밍 | **D07v before/after: interp×3 의 cmd qvel ±200-400°/s 스파이크 소멸 → ±120 사다리꼴 envelope** |
| **MIT 게인 튜닝 (스윕)** | 손목(j5/6/7) kp ×1.8 + 나머지 ×1.3 = [312×4, 43.2, 55.8, 45, 32.5] | operator 확정 (D07t) |
| **v-clip 120°/s** | 전관절 속도 클립 | operator 확정 (D07u) |
| 확정 profile | **`traj_trap_100_v120_kp18x13x`** — 새 기본 | `ts1_tuning_results_20260612.md` + results/ |

### D. 데이터 / 검증
| 방법 | 내용 |
|---|---|
| clean dataset | 60ep handover (banana 19/cup 23/toothpaste 18), 실패 ep 제외 |
| relstats 변환 | absolute→relative action chunk30 (gripper 절대값 유지) |
| **물리 replay 검증** | clean dataset 을 로봇에 open-loop 재생 → 데이터=유효 teacher 확인 (gripper close 정상 R-46/L-54) | LR (5ecfeb78) |

### E. 연구 근거 (RTC/VLA 트릭, 검증 완료 — 바꾸지 말 것)
- **EXP soft-mask** prefix attention schedule (hard 보다 우수).
- **max_guidance_weight = 10** (β=n, n-step flow 최적).
- **temporal ensembling 회피** (高-latency 에서 진동→protective stop; RTC 가 정답).
- interpolation×3 유지.
- 출처: `research_tricks_applicability_20260610.md` (RTC arXiv:2506.07339 등).

---

## 3. 진단으로 배제/확정한 것 (dead-end & confound)

| 항목 | 판정 |
|---|---|
| gripper mapping/cap | grasp 실패 주원인 **아님** (D07c: cmd→motor 도달 확정) |
| single-arm prompt | **막다른 길** — α'' handover-locked (왼손 무조건 받으러 옴), prompt 로 못 끔 |
| host CPU starvation (rustdesk load 13.68) | **minor** — 부하 떨궈도 fps 18 무변 (I/O-bound) |
| joint_2 packet drop / handshake fail | **단순 24V 전원 빠짐** (재연결로 해결, 하드웨어) |
| top-down 회귀 (D07o) | compile 아니라 **joint_2 전원 confound** 였음 |
| compile parity diff 0.19 | watch 중 (grasp 영향 시 bf16+s15 fallback) |

---

## 4. 현재 best config (occasional success — 풀린 것 아님)

**서버 (a6000, pid 797370, 8081, GPU1)**:
- α'' 030000, **bf16 + torch.compile on** (`LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`)
- RTC: **execution_horizon=20**, max_guidance_weight=10, prefix_attention_schedule=EXP
- forward ~210ms, d≈9, window 9≤20≤21 ✓, mem 9932MiB stable

**클라이언트 profile (stack v2, 2026-06-12) = `traj_trap_100_v120_kp18x13x`** (k4_eval_runner.py):
- **TS1 trajectory streamer 100Hz trapezoidal** (interp×3 대체), v-clip 120°/s 전관절
- **MIT kp [312,312,312,312,43.2,55.8,45,32.5]** (손목×1.8/나머지×1.3), kd 기본
- relative cap 없음 (profile v/a 한계 + joint_limits clip 이 안전층)
- chunk_size_threshold=0.5, aggregate_fn_name=weighted_average, actions_per_chunk=30, fps=30
- (구 v1 = `diag_handover_grip`: cap arm25/손목65/grip40 + interp×3 — D07v 비교로 대체됨)

**실행**: `uv run python audits/openarm_folding/k4_eval_runner.py --trial <id> --obj banana --task "Pick the banana, hand it over to the other arm, and place it at the target." --profile diag_handover_grip --duration-s 60`

---

## 5. 현 상태 — 미해결 3개 (방향 단정 없이 사실만)

**달성 (제한적)**: deploy 튜닝으로 **never → occasional** (banana 가 가끔 한 번 grasp). 성공률 매우 낮음.

**미해결 (operator 관찰 = 사실)**:
1. **안정성/성공률** — "겨우 한 번"급, 재현성 거의 없음.
2. **smoothness** — 여전히 안 부드러움. compile+h20(window 충족)로도 톡톡 spike 잔여
   (live d>10 순간, two-machine 네트워크 spike. H=30 이라 horizon 으론 더 못 키움).
3. **grasp 각도/방향 커버리지 — 미지(unknown)** (사용자 관찰): "학습된 그래스핑 각도나 방향
   영역이 아직 모르는 부분이 많다." 정책이 어떤 pose 영역을 커버하는지 **측정된 적 없음**.
   banana 를 학습 방향에 맞춰야 됐다는 정황은 있으나, **커버리지의 실제 모양(어느 각도/방향까지
   되는지)은 미지** — "데이터 천장" 단정은 아직 이름. 먼저 **커버리지를 알아내는 것** 자체가
   미해결 항목.

부차: compile parity diff 0.19 영향, 객체 일반화(toothpaste/cup).

## 5.5 열린 옵션 풀 (스터디 근거 — 방향 미확정, 추후 같이 결정)

스터디(`research_tricks_applicability_20260610.md` 트릭 표 + 이번 세션 준비물) 중 **아직
안 쓴 레버**가 deploy/학습 양쪽에 남아 있음. 어느 것도 단정하지 않고 풀로 보존:

**(가) grasp 커버리지 규명 (사용자 의견 — 모르는 영역을 먼저 안다)**
- dataset 시각화/통계로 학습된 grasp pose 분포(banana orientation·접근각) 매핑.
- live/replay probe 로 "되는 각도 vs 안 되는 각도" 경계 실측 → 천장인지, envelope 운영으로
  충분한지, data 보강이 필요한지 **측정 후** 판단.

**(나) deploy-side 잔여 트릭 (스터디 IF-FAIL 태그, 학습 0 — 아직 미적용)**
- **#6 guidance weight β 상향 (10→12-15)**: narrow prior 엔 더 강한 guidance (β=n 규칙,
  Soare). grasp 풀렸는데 receive/정밀 흐리면 finetune 전에 가장 싼 레버. ✅검증.
- **#8 chunk_size_threshold g 0.5→0.7 + aggregation**: 큐 트리거 cadence 튜닝. ✅검증(단 d>s
  구조는 못 고침 — 지금은 d≤s 라 cadence 효과 볼 만함).
- **latest_only aggregation A/B** (WC1 오프라인 probe + WD1 diag_no_blend profile, 준비물 있음):
  weighted_average 의 손목 댐핑 제거. 미실행.
- **LS0 시작자세 homing**: replay prealign 이 검증한 lever, live 이식 미실행 (t=0 OOD↓).
- **LS1 envelope steering / LS2 CFG**: denoise-loop steering (보류 중, 설계 있음).
- **#7 ACG (Action Coherence Guidance)**: training-free test-time guidance, flow-VLA 선행연구.
  ◐부분검증 — 적용 전 전문 확인 필요.
- smoothness 잔여: s=18 미세조정, two-machine 네트워크 spike 완화(QoS/유선 등) — 미탐구.

**(다) 학습-side (스터디 RETRAIN 태그 — 재학습을 한다면)**
- **#9 소규모 finetune (few-demo/LoRA)**: handover 미세협응·orientation 보강. ⬜신뢰도 미소싱.
- **#10 training-time RTC (action-prefix conditioning)**: 추론 delay 를 학습 때 시뮬 — 高-latency
  정조준, 재학습 시 inference-time RTC 보다 우수(✅검증). **재학습하게 되면 #9 와 콤보 권장.**
- data 보강 (orientation 다양성) — (가)의 측정 결과가 입력.

**결정 원칙(박제)**: (가)로 미지를 먼저 줄이고, (나)의 싼 레버와 (다)의 비용 큰 레버를
그 측정 위에서 비교 — **지금 단계에서 어느 쪽도 단정하지 않음.**

---

## 6. 참조

- 진단 체인: `feasibility_runs_20260609.md`, K6~K15 audit, WB1/WB2 audit, LR replay
- 연구: `research_tricks_applicability_20260610.md`
- SSOT: `docs/STATUS.md` 트랙 K/L/M/N
- plan: `~/.claude/plans/quizzical-petting-sundae.md` (§상단 ACTIVE)
- 주요 커밋: K7 e9cb3230, K15 eb32708a, MB2 46c05ab2, WB1 32d2b0b2, WB2 5b3ca18c

---

## 핵심 한 줄

**deploy 튜닝 = (1) RTC window 복원(compile d↓ + horizon20) + (2) per-joint cap(손목 top-down) +
gentle gripper 로 banana grasp 를 never→occasional 까지. 단 task 해결 아님 — 성공률 낮고
움직임 거칠고 grasp 각도/방향 커버리지는 미지. 다음 방향은 단정하지 않음: §5.5 열린 옵션 풀
(커버리지 규명 / deploy 잔여 트릭 #6·#8·latest_only·LS0-2·ACG / 재학습 시 #9+#10 콤보)에서
측정 기반으로 추후 결정.**
