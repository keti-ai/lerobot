# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-05-22 (PI0.5 handover α 20k step 학습 완료, shortlist REJECTED, D-32 case α 진단 확정)
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop live rollout | **BLOCKED** | D-33 재학습 PASS 후보 확보까지 보류 |
| **B** — full_folding 재학습 | **D-8a relaware COMPLETE, no deploy candidate** | Phase 2 Dataset/Model Registry 이후 D-8b 방향 결정 |
| **C** — full_folding ckpt replay 비교 | **COMPLETE** | 002000/003000/004000 모두 replay FAIL |
| **D** — 축/카메라 진단 | **custom 후속 폐기** | 첫 official rollout 시각 리뷰로 통합 평가 |
| **E** — banana handover 데이터 수집 | **COMPLETE** | 20 ep, KETI-IRRC/openarm_handover_v0_20260521_202117 |
| **F** — PI0.5 handover α fine-tune | **REJECTED (D-32 case α)** | D-33 = handover relstats 변환 후 α 재학습 (사용자 결정 X 옵션) |
| **G** — adaptation 미니 레포 (사이드, D-34) | **PROPOSED** | vision P0 → proprio P1 → action contract P2 순서. 위치/구조 사용자 결정 대기 |

---

## 미해결 이슈

0. **PI0.5 handover α 20k 학습 → shortlist 5개 모두 REJECTED → D-32 진단 case α 확정**
   - 학습: `pi05_handover_v0_alpha_*` 20,000 step 정상 종료, final loss 0.010
   - shortlist gate (recipe + replay) 의 5 ckpt (10k/12k/14k/16k/18k) 모두 REJECTED
   - 진단 (D-32):
     - `train_config.json`: `use_relative_actions=true`, `relative_action_chunk_size=null`, `relative_exclude_joints=["gripper"]`
     - dataset = absolute action rows (lerobot-record default, `KETI-IRRC/openarm_handover_v0_20260521_202117`)
     - alpha016 processor stats = absolute-like (q01/q99 ≈ -53.697..113.035, mean ~55)
     - level2_004000 processor stats = relative-like (mean ~0, q01/q99 ≈ -42.691..39.028)
     - dataset row 값 = position-like, relative storage 증거 없음
   - 결론: 학습 config 와 dataset action 분포가 미스매치 → processor 가 absolute 분포로 학습됨
   - α step 016000 deploy 불가 = 정당. shortlist 전체 같은 학습이라 동일 결함
   - **다음 = D-33 (X) handover dataset 의 relstats 변환본 만들기 + α 재학습**
   - 8766 = level2 corrected 004000 유지 (D-29 RESOLVED)
   - α HF push 안 함 (D-28 RESOLVED)
   - 참조 (a6000 측 commit 5개, origin 박제):
     - `b8170de4 docs(a6000): start pi05 handover alpha overnight training`
     - `d3bf4f9a docs(a6000): review pi05 handover alpha training result`
     - `ca6263f9 ops(a6000): pi05 handover alpha shortlist 5 ckpt recipe + replay gate`
     - `0595f828 docs(a6000): D-32 alpha postprocessor/action representation diagnosis`
     - 산출물: `audits/openarm_folding/a6000_pi05_handover_alpha_{status,result,shortlist_gate_20260522,d32_diagnosis_20260522}.md`
   - M1 (별도 통합 postmortem) SKIP — 위 5 commit 으로 사실관계 박제 완료

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

## 다음 N개 작업 (우선순위 순)

1. **D-33 handover dataset relstats 변환 (Codex, a6000)**
   - source: `KETI-IRRC/openarm_handover_v0_20260521_202117` (20 ep, absolute action)
   - target: 같은 chunk30 + arm relative + gripper excluded recipe (level2 와 동일)
   - 도구 위치 후보: a6000 측 level2 relstats 만든 스크립트 (도구 path 확인 필요)
   - 산출물: 새 dataset (slug 후보 `KETI-IRRC/openarm_handover_v0_relstats_chunk30`) + relstats marker
   - 보고서: `audits/openarm_folding/a6000_handover_v0_relstats_transform_<TS>.md`

2. **D-33 α 재학습 (Codex, a6000, overnight)**
   - 기존 α 명령에서 `--dataset.repo_id` 만 새 relstats dataset 으로 변경
   - 같은 init (level2 corrected 004000) + 같은 `use_relative_actions=true` recipe
   - steps=20k (또는 10k 단축 후 결과 보기)
   - output: `pi05_handover_v0_alpha_relstats_<TS>`
   - 학습 후 shortlist 같은 방식으로 gate + replay

3. **D-32 진단 보고서 commit (Codex, a6000)**
   - 사전 확인 데이터 (train_config, processor stats 비교, dataset sample) 그대로 보고서로
   - 산출물: `audits/openarm_folding/a6000_pi05_handover_alpha_postmortem_case_alpha_20260522.md`
   - 메시지: `ops(a6000): D-32 postmortem — α case α (relative config vs absolute dataset)`

4. **D-34 adaptation 미니 레포 사이드 트랙 — 위치/구조 결정 + 첫 함수 set (사용자 + Codex)**
   - 메인 트랙 (D-33) 과 병행 가능
   - 위치 후보: `src/lerobot/openarm_adaptation/` (모듈 + ProcessorStep) vs `docs/STUDY/openarm_adaptation/` (스터디 문서)
   - P0 vision: camera FOV/scale/color/exposure normalize
   - P1 proprio: joint offset/range, gripper unit, degrees↔radians
   - P2 action contract: D-33 의 relstats 변환을 일반화 (any 16D dataset → chunk_N relative)

5. **Phase 2 Dataset Registry / Model Registry v2 본문 보강 (DEFERRED)**
   - D-33 결과 row 추가 시점에 같이 진행
   - 메인 트랙 (D-33) 우선

6. **operator 입회 official rollout 첫 모션 테스트 (DEFERRED — D-33 PASS 후보 확보 후)**
   - D-33 재학습이 recipe + replay PASS 받으면 진입
   - 그때 D-30 operator 일정 + D-13 큐 재정의

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
