# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-06-11 (🟡 **FLAG — banana grasp "가끔 한 번"(occasional, 불안정, 풀린 것 아님)** (D07r, compile+h20). 사실: ①성공률 매우 낮음 ②움직임 여전히 거침(톡톡 spike 잔여, H=30 한계) ③**grasp 각도/방향 커버리지 미지(측정된 적 없음, 사용자 관찰)**. **방법 총망라+열린 옵션 풀 = `audits/openarm_folding/d42_methods_summary_20260611.md` §5/§5.5**. best config: 서버 compile+horizon20 pid797370 8081, profile diag_handover_grip(arm25/j4-5=65/j6-7=40/grip40, interp3). **다음 방향 단정 안 함** — 옵션 풀: (가)커버리지 규명 먼저 (나)deploy 잔여 트릭(#6 guidance β↑, #8 g0.7, latest_only WC1/WD1, LS0 homing, LS1/2, ACG) (다)재학습 시 #9 finetune+#10 training-time RTC 콤보. 측정 기반으로 추후 같이 결정.)
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

> **[연구 재결론 박제, 2026-06-10]** `audits/openarm_folding/research_tricks_applicability_20260610.md` — 최신연구(RTC/VLA) 트릭 적용가능성 + 재결론. **핵심: 현 bf16/no-compile baseline 은 RTC 를 유효구간 밖(`d>s`, `d≈15–27 > s=10`)에서 돌리는 중 → 잔여 톡톡은 cap 이 아니라 latency(블로커 B). 블로커 A(grasp 각=per-joint cap/D07n)와 직교.** D07n 판정은 grasp 만 보고, 톡톡은 latency 컷(OOM-완화 compile 재도입 / `s=max(d,s_min)`)으로 별도 처리. temporal ensembling 회피·EXP soft-mask·interpolation×3 는 연구상 정답 확정.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop live rollout | **BLOCKED** | 8766 serving 정지 (D-29 갱신). PASS 후보 확보까지 라이브 X |
| **B** — full_folding 재학습 | **D-8a relaware COMPLETE, no deploy candidate** | Phase 2 Dataset/Model Registry 이후 D-8b 방향 결정 |
| **C** — full_folding ckpt replay 비교 | **COMPLETE** | 002000/003000/004000 모두 replay FAIL |
| **D** — 축/카메라 진단 | **custom 후속 폐기** | 첫 official rollout 시각 리뷰로 통합 평가 |
| **E** — handover 데이터 수집 | **EXPANDED (v0 multi3)** | 65 ep / 3 tasks (banana 0-19, olive green cup 20-44, blue toothpaste 45-64). 같은 stamped repo KETI-IRRC/openarm_handover_v0_20260521_202117 에 resume 누적. plate skip (작업성). 실패 ep clean 대기. |
| **F** — PI0.5 handover α/α′ fine-tune | **BOTH REJECTED** | α REJECTED (D-32 case α). α′ relstats 30k REJECTED (M4, b7897a06). 다음 = D-35 분기 |
| **G** — adaptation 미니 레포 (D-34) | **P2 COMPLETE, P0/P1 보류** | S1 scaffold + S2 relstats_transform 완료 (ca532645). P0 vision/P1 proprio 은 D-35 분기 끝나고 |
| **H** — D-35 분기 (U→P→Q→R) | **R 완료** | U partial (commit 31b42505), R 완료 (65 ep). P/Q/U-retry 트랙 J 로 흡수 |
| **I** — D-40 Wayland keyboard patch | **NEW (A5)** | pynput global listener Wayland 안 먹힘. A3 학습 중 병행. Codex syhlabtop ~2-3h |
| **J** — D-38 후속 (cleaning + α'' 학습) | **CLOSED** | α'' 030000 final ckpt = deploy target. A6 SKIP (사용자 결정). gate 도구 (P, commit 0e7bdd34) 는 future use 으로 보존 |
| **L** — D-42 VLA-steering (PIVOT2 2026-06-10) | **LS1+LS2 병행 착수** | 사용자 redirect: perception+IK 별도 파이프라인(OWLv2/SAM2/depth/URDF/캘리브) "갑자기 비전알고리즘" 이라 거부 → 구 L0~L3 폐기. 대신 **α''/PI0.5 a6000 서빙 그대로 + inference-time steering**, **학습 0**. hook = PI0.5 flow-matching denoise 루프(modeling_pi05.py:823-855, `x_t+=dt·v_t`), **RTC 가 이미 같은 자리서 guidance 주입(선례)**. num_inference_steps=10. 채택(①+② 병행): **LS1 envelope steering** — 실행 절대 관절 target 을 dataset 시연 envelope(observation.state q01/q99+margin, 16D)로 clip/유도 → desk-sweep(OOD) 직격, URDF·CV·캘리브 불필요(관절공간, dataset stats만), hard projection 1차→soft guidance 승급. **LS2 CFG** — denoise 조건/무조건 2회 v=v_uncond+s·(v_cond−v_uncond), guidance_scale config(1.0=no-op), 언어→action grounding sharpen, RTC composition 주의. 둘 다 config-gated(off=기존 보존, A/B). α'' handover policy 라 task=handover 유지(pick 단계 공통이라 효과). **LR replay 게이트(5ecfeb78) 통과**: scene-matched 물리 replay(retry2, prealign 3s)에서 gripper close 정상 도달(R readback -46.3/L -54.5) → 데이터=유효 teacher, cap/mapping/gripper 무관 확정 → 실패=순수 정책 grounding=steering 정당. replay 가 prealign(시작 자세 homing) 필요했던 점 → **LS0**: live rollout 도 dataset episode-start 자세에서 시작(t=0 OOD/desk-sweep 완화), wrapper(replay_runner --prealign-start-s) 로직을 k4_eval_runner live 경로에 이식. 순서: **LS0(homing)+LS1(envelope)+LS2(CFG)** → **L4(#32)** operator N=20 steering on/off 14+/20. **D07i(scene-matched baseline, FAIL but 유효)**: scene 정렬로 desk-sweep 해소(접근 OK), 잔여=**손목/팔꿈치 펴진 채 도착 → top-down grasp 각 안 나옴**. joint_4 cap(15°) 매 trial ~20회 clamp 수렴 = **joint_4 throttle 가설** (정책이 손목 bend >15°/step 명령하는데 cap+lag 로 펴진 채 도착). 재우선순위: **LS0/LS1(desk-sweep) 보류**, cap 검증 먼저. **D07j(diag_full_cap_smooth arm65/interp3) = joint_4 cap 가설 확정** (clamp 0 + top-down 각 재현, 모델 무수정으로 손목 해결). 새 증상 2개: (A) gripper cap65 라 팡 닫혀 banana 침 (B) 쫌 덜컥(arm65 큰 jump). → **D07k(diag_wrist_free_gentle_grip arm65/grip20/interp3, 2e26c072)**: gripper gentle close 로 A 해결 시도, arm65 유지. B 남으면 per-joint cap(joint_4/5 高, 나머지 中) 다음. grasp 안정되면 → N=20. LS2(CFG)는 cap 길 막히면. memory track-l-vla-steering |
| **N** — D-42 host CPU starvation (infra, 2026-06-10 확정) | **클린 baseline 재확립 중** | CAN 무결점(PEAK adapter, ip-stats 0 err/drop/missed) — "joint_2 packet drop"=damiao 10ms read timeout(damiao.py:63) 을 호스트가 놓친 것. host load avg 13.68(i7-10870H 16스레드), 주범 rustdesk 13.4%+Xwayland/i915/flush. control loop 16fps(목표30)+카메라 3대 동기 read 가 모터 창 밀어냄→joint_2 stale→top-down/톡톡/grasp 오염. **D07f~o 전부 오염된 evidence.** 계획(plan quizzical §상단): ①rustdesk 종료+DE 최소 ②chrt -f + taskset ③a6000 bf16(compile off, Q1) → D07p 측정(fps≥25, joint_2 drop≈0, top-down 복원) → 재판정. 안되면 desktop 이전. fallback: damiao timeout↑ / 카메라 background thread |
| **M** — D-42 블로커 B: inter-chunk smoothness (latency) | **신규 (연구노트 c64f3f9f)** | 톡톡의 구조적 원인 = `d>s` (RTC feasibility window `d≤s≤H−d` 위반). live forward `d≈15–27 step > s=10`. **interp×3 는 starvation 만 메움, boundary 불연속은 못 고침** (이전 "interp 가 캐리어" 판단 교정). compile-off(K15 OOM 회피)가 smoothness 막은 결정 — compile-on 이면 forward 288ms→d≈9≤s=10 회복. 트랙: **MB1**(#54) live d 로깅 d vs s 확정 → **MB2**(#55) OOM-완화 compile 재도입(leftover-prefix 길이 고정→graph cache 안정, 결정타) / **MB3**(#56, alt) s=max(d,s_min) horizon↑(H≥2d). 확정유지: TE 회피·EXP soft-mask·interp×3. note: research_tricks_applicability_20260610 |
| **K** — D-42 70% (latency 트랙, COMPLETE) | **K15 compile 완료, latency 종료** | latency 7겹 (K8~K15) 종료. K13: latency=forward 자체. K14 bf16 marginal (413→396). **K15 torch.compile (eb32708a)**: PI0.5 native compile_model=True + compile_mode="default" serving-load 주입 (reduce-overhead 는 standalone steady 12s 실패로 배제). **forward 413→396→288ms (32%↓), handler ready 315ms, synthetic 이 RTC window(h10=333ms) 진입.** post-warmup recompile/graph break 0. action sanity max abs diff 0.0066. server 재기동 (pid 4123765, 8081, GPU0 22.5GB used). bf16 autocast(K14)+compile 병행. **남은 변수 = synthetic→live gap (K13 때 ~140ms: 413 synth/552 live). K15 live = ~288+gap ≈ 430ms? → window 경계.** ★ **다음 = D07f operator live** (K15 server + h10 기준, banana 1 trial): live forward 실측 + chunk 경계 smoothness(툭툭 해소?) + grasp 도달. 해소 → K4 N=20 official. 미해소 → 끊겨도 70% 철학(§16)으로 N=20 강행 판단. plan §17 |
| **K** — D-41 open dataset replay sanity | **NEW** | (a) gate 도구 sanity (level2 known PASS), (b) PI0.5 base capability (folding_latest). α/α' 평가 전 했어야 한다는 회고. ~1h Codex a6000 |

---

## 미해결 이슈

0. **α/α′ 두 학습 모두 REJECTED → 분기 결정 D-35 (U→P→Q→R)**

   **α 학습 (2026-05-22, GPU0 20k)** — D-32 case α 확정으로 SKIP
   - shortlist 5/5 REJECTED. root cause = use_relative_actions=true ↔ handover absolute dataset 미스매치
   - 참조 commit: b8170de4, d3bf4f9a, ca6263f9, 0595f828 (a6000 측 박제)

   **α′ 학습 (2026-05-22~23, GPU1 30k, relstats variant)** — M4 REJECTED (b7897a06)
   - 학습 PASS: 30k step, final loss 0.012, 15 ckpts
   - shortlist 5/5 REJECTED (22k/24k/26k/28k/30k):
     - **D-32 root cause 해결됨** (`postprocessor_action_stats_are_relative_for_arm_joints` PASS)
     - 새 FAIL (A) recipe folding-task lock: `dataset_robot_type_openarms_follower`, `camera_keys_and_shapes_match_space_recipe`, `rabc_recorded_in_train_config`
     - 새 FAIL (B) replay magnitude mismatch: 모델 arm delta best ratio 0.141 (target ~1.0). raw normalized err ~4.84
   - 참조: `audits/openarm_folding/a6000_pi05_handover_alpha_relstats_shortlist_gate_20260526.md`

   **D-35 분기 진행 상황 (2026-06-01)**:
   - (U) **PARTIAL** (commit 31b42505): CPU fallback 너무 느려 (885초/cell) 100-cell 미완.
     ep 0 재현 + target-only 분포 완료. **카메라 staleness 가설 기각** (first 7 = 12.609,
     later 13 = 12.559 평균 recorded arm delta 거의 동일). ep 0 = outlier 아님 (overall mean
     12.576 안). normalized target outlier 는 ep 10-16 (max 9.702 @ ep 15).
     → **U-retry**: GPU 가용 시 5 ckpt × 20 ep replay 재실행 권장
   - (P) **READY** — U 부분 결과만으로 디자인 가능. stage29 의 folding lock 3 항목 완화. Codex syhlabtop ~2-3h
   - (Q) **BLOCKED** — U GPU 완료 결과 (실제 ratio 분포) 가 threshold 정의의 input. U-retry 후 진행
   - (R) handover v1 multi-object 50-100 ep — 사용자 직접 진행 가능 (P/Q 와 직교)

   **운영**:
   - 8766 이미 정지 상태 (D-29 갱신 의도와 일치, 별도 정지 명령 불필요 — 2026-06-01 확인)
   - 8765 정지 상태 유지
   - 2026-06-01 nvidia-smi 시점에 a6000 4 GPU 다 동료 KETI 멤버의 별도 DDP 학습으로 점유 (PID 1447660~1447663, lerobot venv, 100% util, ~26GB each). 본 세션 무관. U/P/Q 진행 시 GPU 가용성 영향 — U 는 CPU fallback 가능, P/Q 는 syhlabtop 측 코드라 직교.

1. **`full_folding` replay FAIL 원인 — checkpoint selection 가설 기각**
   - ckpt 002000: ratio 0.220-0.320, raw normalized max error 0.433 -> FAIL
   - ckpt 003000: ratio 0.142-0.348, raw normalized max error 0.402 -> FAIL
   - ckpt 004000: ratio 0.128-0.282, raw normalized max error 0.413 -> FAIL
   - D-8a continuation `001000`~`012000`: relaware recipe PASS, replay FAIL.
   - 결론: 단순 checkpoint selection 과 D-8a continuation 으로 deploy 후보를 만들지 못했다.
   - 다음 판정은 Phase 2 Dataset Registry / Model Registry v2 에서 데이터 품질, fold-only subset, curated mix 가능성을 함께 본 뒤 진행한다.
   - 참조:
     - `audits/openarm_folding/a6000_d8a_gate_summary_relaware.md`
     - `audits/openarm_folding/a6000_d8a_no_candidate_relaware.md`
     - `audits/openarm_folding/a6000_d10c_postprocessor_rabc_diagnosis_20260518.md`

2. **base 카메라 FOV/scale 미스매치 — official rollout 첫 실행 시각 리뷰로 통합 평가**
   - 기존 D3 read-only capture 는 정상 캡처였지만 dataset reference side-by-side 후속은 폐기했다.
   - 별도 mosaic/side-by-side 보고서는 재개하지 않는다.
   - 공식 `lerobot-rollout` 첫 실행에서 base/wrist view, shirt 위치, action response 를 보조 녹화와 함께 평가한다.

3. **left wrist / gripper axis-readback 의심 — official rollout 첫 실행 시각 리뷰로 통합 평가**
   - 기존 read-only limit audit 에서 16D readback 은 software limit 안이었다.
   - 단일 조인트 `+1deg/-1deg` probe 후속은 폐기했다.
   - 공식 `lerobot-rollout` 첫 실행에서 전체 시퀀스 흐름, saturation, readback, visual result 를 함께 본다.

4. **wrist 카메라 capture/training 해상도 차이**
   - syhlabtop 측 기존 capture 는 640x480 을 사용했고 server 는 1280x720 으로 resize 후 모델 입력을 구성했다.
   - 공식 `lerobot-rollout` baseline 에서는 training recipe 와 맞는 camera config 를 Phase 3 preflight 에서 다시 확정해야 한다.

5. **RESOLVED — D-9 cuDNN 환경 결정 갱신, D-8a no-candidate**
   - A6000 torch `2.11.0+cu128` / CUDA `12.8` / cuDNN `91900` 환경은 2026-05-15 cuDNN enabled Conv2d smoke 에서 `CUDNN_STATUS_NOT_INITIALIZED` 로 실패했었다.
   - 기본 검증 환경은 option (i) torch `2.7.1+cu126`, CUDA `12.6`, cuDNN `90501`, torchvision `0.22.1+cu126` venv 이며, 1-step train smoke 는 `dataset.video_backend=pyav` 로 PASS 했다.
   - 2026-05-21 현재 torch `2.11.0+cu128`, cuDNN `91900` 에서 cuDNN enabled Conv2d forward/backward multi-shape smoke 가 PASS 했다.
   - handover alpha 학습은 `uv run --no-sync` 로 환경 재동기화를 막고, 현재 torch 2.11 환경 사용을 허용한다.
   - D-8a relaware replay 는 `001000`~`012000` 모두 FAIL. deploy 후보 없음.

6. **RESOLVED — A6000 serving 복구 + Track A custom RTC ON repeat3 closed-loop 완주**
   - `http://10.252.205.103:8766/health`, `http://10.252.205.103:8765/health` 모두 OK.
   - 8766 live: level2 corrected 004000, `rtc_enabled=true`, `rtc_execution_horizon=20`, `rtc_max_guidance_weight=10.0`, `rtc_prefix_attention_schedule=EXP`, `use_relative_actions=true`.
   - custom repeat3 trial 은 120초 runtime 을 완주했지만 task success 는 미달이었다.
   - operator 리뷰: tabletop folding 방향성은 보이나 옷을 안정적으로 집지 못했고, chunk 사이 transition 이 시각적으로 남았다.
   - Phase 1 에서 custom rollout harness 와 Track A 결과 문서는 archive 로 이동한다.

7. **a6000(ketiserver) 측 워크트리 동기화 주의**
   - syhlabtop 워크트리 기준으로 Phase 1 archive 와 PLAN/STATUS 갱신을 수행한다.
   - a6000 측 작업 전에는 별도 세션에서 `git fetch && git checkout audit/openarm-folding-baseline` 확인이 필요하다.

---

## 다음 N개 작업 (우선순위 순, plan §13 trajectory)

0. **A1 — Cleaning review (사용자 직접) — COMPLETE 2026-06-04**
   - 실패 ep 확정 = `[13, 24, 25, 51, 55]` (banana 13 / olive green cup 24,25 / blue toothpaste 51,55)
   - 60 ep clean dataset 진행

0.5. **A1.5 — clean dataset 생성 — DONE 2026-06-04**
   - HF: `KETI-IRRC/openarm_handover_v0_20260521_202117_clean` (private, 41 files, sha 526acb21)
   - 60 ep / 53,851 frames / 3 tasks (task_index reindex: toothpaste=0, cup=1, banana=2; string 보존)
   - commit 3fb1c101 + 4ace9147

1. **A2 — D-38 65 ep relstats 변환 (Codex syhlabtop or a6000) — READY**
   - 도구: S2 `transform_dataset_to_relative_chunk` (commit ca532645)
   - source: `KETI-IRRC/openarm_handover_v0_20260521_202117` (현 65 ep)
   - target: `KETI-IRRC/openarm_handover_v0_multi3_relstats_chunk30`
   - target_root: 결정 필요 (syhlabtop local 또는 a6000 local)
   - chunk_size=30, exclude_joint_indices=(7,15)
   - verification PASS 후 사용자 결정으로 HF push
   - audit: `a6000_handover_v0_multi3_relstats_transform_<TS>.md`

2. **A3 — α'' 재학습 GPU 30k overnight (Codex a6000) — BLOCKED on A2 + GPU 자유**
   - 명령 = α' 와 동일 + `--dataset.repo_id`/`--output_dir`/`--policy.repo_id` 변경
   - init = level2 corrected 004000 (α 와 동일)
   - GPU: a6000 동료 학습 끝난 시점 또는 GPU2/3 가능 시
   - audit: status/result md

3. **A4 — P (handover-specific recipe gate) — A3 중 병행, Codex syhlabtop ~2-3h**
   - 새 도구 `audits/openarm_folding/handover_recipe_gate.py` 또는 stage29 task-aware path
   - folding lock 3 항목 (robot_type, camera shape, RABC) 완화

4. **A5 — D-40 Wayland keyboard patch — A3 중 병행, Codex syhlabtop ~2-3h**
   - pynput → stdin 권장 (가장 단순)
   - 위치: `src/lerobot/utils/control_utils.py` 의 `init_keyboard_listener`

5. **A6 — α'' shortlist gate + replay (Codex a6000, A3 끝난 후, ~1h)**
   - A4 의 P 가 active gate
   - stage22 replay 도 같이

6. **A7 — 결과 분기 (사용자 결정)**
   - PASS → D-28''/D-29''/D-30/D-13''
   - FAIL → D-39 (S/T/R-extend/V) 검토

7. **(Q + U-retry) — a6000 GPU 자유 시점**
   - Q (replay threshold task-specific) BLOCKED on U-retry
   - U-retry (5 ckpt × 20 ep GPU replay) BLOCKED on GPU

8. **D-34 P0 vision/P1 proprio (DEFERRED)** — A7 결과 후
9. **Phase 2 Dataset Registry / Model Registry v2 본문 보강 (DEFERRED)**
10. **operator 입회 official rollout (DEFERRED — A6 PASS 후보 확보 후)**

---

## 최근 핵심 결과

### PI0.5 handover α 20k 학습 + shortlist REJECTED + D-32 진단 (2026-05-22)

```text
run_dir:      a6000 local (pi05_handover_v0_alpha_*, 229 GB)
steps:        20,000 / 20,000 정상 종료 (2026-05-22 10:04:54 KST)
final loss:   0.010, grad_norm 0.426, lr 2.5e-06
checkpoints:  10개 (002000~020000)
HF push:      안 함 (D-28 RESOLVED)
TensorBoard:  http://10.252.205.103:6007
GPU 사용:     GPU0 단일 (lerobot-train default single-process)
init:         level2 corrected 004000
dataset:      KETI-IRRC/openarm_handover_v0_20260521_202117 (absolute action rows)
recipe:       use_relative_actions=true, relative_exclude_joints=["gripper"], chunk_size=30

shortlist gate (recipe + replay) — 5 ckpt 평가:
  step 10000: REJECTED
  step 12000: REJECTED
  step 14000: REJECTED
  step 16000: REJECTED
  step 18000: REJECTED

D-32 진단 (case α 확정):
  - train_config: use_relative_actions=true (level2 init 의 recipe)
  - dataset action stats: absolute-looking
  - alpha016 processor stats: q01/q99 ≈ -53.697..113.035, mean ~55 (absolute-like)
  - level2_004000 processor stats: q01/q99 ≈ -42.691..39.028, mean ~0 (relative-like)
  - gate auto: action_is_relative=false (relstats marker 없음)
  - 결론: dataset 과 학습 config 미스매치, processor 가 absolute 분포로 학습됨
  - shortlist 전체 같은 학습 → 모두 동일 결함, deploy 불가

판정: α 학습 자체 SKIP. 8766 = level2 corrected 004000 유지.

다음 사이클 = D-33 (X 옵션): handover dataset 의 relstats 변환본 만들기 + α 재학습.
```

### Banana handover dataset 수집

```text
repo_id: KETI-IRRC/openarm_handover_v0_20260521_202117
local_root: /home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117
episodes/frames: 20 / 17,944
task: Pick the banana, hand it over to the other arm, and place it at the target.
robot: bi_openarm_follower, can0=left, can1=right
teleop: openarm_mini, mini_set1
cameras: left_wrist 315122270766, right_wrist 230322273311, base 213622075840
```

첫 7 episodes 이후 right_wrist `230322273311` frame staleness timeout 이 있었지만
저장과 push 는 완료됐다. 나머지 13 episodes 는 stamped repo id 와 명시적
`--dataset.root` 를 사용해 `--resume=true` 로 append 했다. 기록 레시피와
handoff prompt 는 `docs/_archive/openarm_folding/` 의 2026-05-21 문서를 본다.

OpenArm record 안전 패치도 같이 적용했다: episode 시작/종료 시 follower gripper 를
천천히 닫고, Ctrl-C/부분 connect 실패 시 CAN bus cleanup 과 gripper torque-off pulse 를
강화했다. upstream 과의 차이는 OpenArm follower / Damiao / record script 로 제한한다.

### Track A custom closed-loop 결과 (archive 대상)

```text
first trial: /home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_131245_level2_messy_shirt_retry_no_readback_fix/
RTC ON trial: /home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_141401_rtc_on/
repeat3 trial: /home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_185509_rtc_on_repeat3/
repeat3 stop_reason: max_session_duration_s
repeat3 actions_executed: 3031
repeat3 chunks_accepted: 142
repeat3 aux_recording: /home/syhlabtop/workspace/realsense_live/recordings/rollout_trial_20260518_185509_rtc_on_repeat3.avi
```

판정: runtime 은 막힘 없이 완주했지만 fold 성공은 아니다. 이 결과는 official
`lerobot-rollout` baseline 전환 전 custom harness 의 참고 자료로 archive 한다.

### Track C / D-8a 결과

```text
full_folding 002000: replay FAIL
full_folding 003000: replay FAIL
full_folding 004000: replay FAIL
D-8a 001000-012000: relaware recipe PASS, replay FAIL
level2 corrected 004000: recipe PASS, replay PASS
```

판정: 현재 deploy 경로에는 level2 corrected 004000 만 남는다.

---

## 참조

- SSOT: `docs/PLAN.md`
- 운영 포인터: `AGENTS.md`
- audit index: `audits/openarm_folding/README.md`
- 종료 작업 아카이브: `docs/_archive/openarm_folding/` + `docs/_archive/INDEX.md`
- a6000 측 산출물 루트: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/`
