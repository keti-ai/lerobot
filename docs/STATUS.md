# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-06-01 (α′ relstats 30k 학습 PASS but shortlist 5/5 REJECTED, 분기 결정 = U→P→Q→R)
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop live rollout | **BLOCKED** | 8766 serving 정지 (D-29 갱신). PASS 후보 확보까지 라이브 X |
| **B** — full_folding 재학습 | **D-8a relaware COMPLETE, no deploy candidate** | Phase 2 Dataset/Model Registry 이후 D-8b 방향 결정 |
| **C** — full_folding ckpt replay 비교 | **COMPLETE** | 002000/003000/004000 모두 replay FAIL |
| **D** — 축/카메라 진단 | **custom 후속 폐기** | 첫 official rollout 시각 리뷰로 통합 평가 |
| **E** — banana handover 데이터 수집 | **COMPLETE (v0)** | 20 ep, KETI-IRRC/openarm_handover_v0_20260521_202117. v1 = D-38 (R 단계) |
| **F** — PI0.5 handover α/α′ fine-tune | **BOTH REJECTED** | α REJECTED (D-32 case α). α′ relstats 30k REJECTED (M4, b7897a06). 다음 = D-35 분기 |
| **G** — adaptation 미니 레포 (D-34) | **P2 COMPLETE, P0/P1 보류** | S1 scaffold + S2 relstats_transform 완료 (ca532645). P0 vision/P1 proprio 은 D-35 분기 끝나고 |
| **H** — D-35 분기 (U→P→Q→R) | **OPEN** | (U) episode 분포 진단 → (P) handover gate → (Q) threshold → (R) v1 50-100 ep 수집 |

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

   **다음 분기 = D-35 (사용자 결정 2026-06-01)**:
   - (U) episode 분포 진단 — 모든 ep replay, magnitude 일관성 확인 (~30min Codex a6000)
   - (P) handover-specific recipe gate — stage29 folding lock 완화 (~2-3h Codex syhlabtop)
   - (Q) replay threshold task-specific — stage22 threshold 재정의 (~2-3h Codex syhlabtop)
   - (R) handover v1 50-100 ep 추가 수집 — 사용자 직접 3-5h + 재학습 14h
   - **순차 진행** (U 결과가 P/Q 디자인 input)

   **운영**: 8766 일단 정지 (D-29 갱신). 다음 사이클 GPU 확보.

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

## 다음 N개 작업 (우선순위 순, D-35 분기)

1. **(U) episode 분포 진단 — Codex a6000, ~30min**
   - stage22 replay 를 모든 ep (0-19) 에 대해 실행, ratio 분포 + raw norm err 표 작성
   - 목적: magnitude 문제가 ep 0 만인지 전체인지 확인
   - GPU 안 씀. 8766 정지 후 진행
   - 산출물: `audits/openarm_folding/a6000_handover_v0_relstats_episode_distribution_<TS>.md`
   - 입력: U 결과 → P 디자인 + 다음 결정

2. **8766 serving 정지 (Codex a6000, ~5min)**
   - 현재 GPU0 에 8766 (level2 corrected 004000). 정지로 GPU 확보
   - 명령: a6000_live_policy_server.py 프로세스 kill 또는 systemd 정지
   - baseline 라이브 없어지지만 D-29 갱신 결정 (사용자 동의)

3. **(P) handover-specific recipe gate (Codex syhlabtop, ~2-3h)**
   - stage29 의 folding lock 3 항목 완화 또는 별도 gate
   - 변경: robot_type list 확장 (`bi_openarm_follower` 포함), camera shape lock 자유화, RABC optional
   - 위치: `audits/openarm_folding/stage29_candidate_recipe_gate.py` task-aware path 또는 신규 `handover_recipe_gate.py`
   - U 진단 결과 본 뒤 진행

4. **(Q) replay threshold task-specific (Codex syhlabtop, ~2-3h)**
   - stage22 의 ratio/raw threshold 를 handover 분포 기준으로 재정의
   - U 진단의 분포 표가 입력
   - P 와 병행 가능

5. **(R) handover v1 50-100 ep 추가 수집 (사용자 직접, 3-5h)**
   - 미니 리더 + bi_openarm_follower + 동일 카메라
   - lerobot-record 명령 = handover_v0 와 동일, `--dataset.repo_id=KETI-IRRC/openarm_handover_v1_<TS>`
   - 사용자 일정 별도 결정
   - 수집 후 변환 (S2 도구) + 재학습 (a6000 14h GPU)

6. **D-34 P0 vision/P1 proprio (DEFERRED)**
   - D-35 분기 끝나고 진행
   - P0 vision (resize_align, color_match) 가 라이브 시점에 필요

7. **Phase 2 Dataset Registry / Model Registry v2 본문 보강 (DEFERRED)**

8. **operator 입회 official rollout (DEFERRED — D-35 PASS 후보 확보 후)**

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
