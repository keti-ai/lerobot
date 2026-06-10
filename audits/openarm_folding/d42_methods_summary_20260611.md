# D-42 Live Deploy — 적용 방법 총망라 (첫 banana grasp 성공 시점 박제)

**작성**: 2026-06-11
**상태 flag**: 🟢 **첫 banana grasp 성공** (compile+horizon20 서버 + per-joint cap). 여기서
설정 고정, 남은 작업(안정화·N=20·일반화)은 추후.
**목표**: OpenArm 16D 양팔 + PI0.5 로 real-world handover pick & place. north star = N=20 중 70%.

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

## 4. 현재 고정(frozen) 설정 — 첫 성공 config

**서버 (a6000, pid 797370, 8081, GPU1)**:
- α'' 030000, **bf16 + torch.compile on** (`LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`)
- RTC: **execution_horizon=20**, max_guidance_weight=10, prefix_attention_schedule=EXP
- forward ~210ms, d≈9, window 9≤20≤21 ✓, mem 9932MiB stable

**클라이언트 profile = `diag_handover_grip`** (k4_eval_runner.py):
- max_relative_target: `{arm joints:25, joint_4:65, joint_5:65, joint_6:40, joint_7:40, gripper:40}`
- action_interpolation_multiplier=3, chunk_size_threshold=0.5, aggregate_fn_name=weighted_average
- actions_per_chunk=30, fps=30

**실행**: `uv run python audits/openarm_folding/k4_eval_runner.py --trial <id> --obj banana --task "Pick the banana, hand it over to the other arm, and place it at the target." --profile diag_handover_grip --duration-s 60`

---

## 5. 현 상태 + 남은 작업 (추후)

**달성**: 🟢 **첫 banana grasp 성공** (top-down 각 + 손목 회전 + handover 받기 + 부드러움 대폭 개선).
**잔여**:
1. **안정성** — 아직 "겨우 한 번" (랜덤성). 톡톡 spike 잔여 (live d>10 순간) → s 미세조정 또는 two-machine 네트워크.
2. **compile parity diff 0.19** 영향 정밀 검증 (geometry 무해/실해).
3. **객체 일반화** — toothpaste/cup 검증 (D07r_tp 등).
4. **execution-layer blending 잔여 댐핑** — `aggregate_fn_name=latest_only`(no-damping) A/B (WC1 오프라인 + WD1 profile).
5. **operator N=20** — banana 7 + cup 7 + toothpaste 6, 14+/20 = 70% (본 게임).
6. (천장) orientation 다양성 부족 시 data 보강 + finetune.

---

## 6. 참조

- 진단 체인: `feasibility_runs_20260609.md`, K6~K15 audit, WB1/WB2 audit, LR replay
- 연구: `research_tricks_applicability_20260610.md`
- SSOT: `docs/STATUS.md` 트랙 K/L/M/N
- plan: `~/.claude/plans/quizzical-petting-sundae.md` (§상단 ACTIVE)
- 주요 커밋: K7 e9cb3230, K15 eb32708a, MB2 46c05ab2, WB1 32d2b0b2, WB2 5b3ca18c

---

## 핵심 한 줄

**async PI0.5 handover 를 실제 로봇에서 처음 grasp 성공시킨 방법 = (1) RTC feasibility window
복원(compile 로 d↓ + execution_horizon 20) + (2) per-joint cap 으로 손목 top-down 각 확보 +
gentle gripper. 진단으로 latency/cap/host/joint_2 전원/single-arm 을 한 겹씩 벗겨 도달.**
