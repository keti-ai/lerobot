# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-05-21 (banana handover dataset 수집 완료, OpenArm record safety 패치 적용)
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop live rollout | **official `lerobot-rollout` baseline 전환 준비** | Phase 3 OpenArm connect side-effect 패치 + preflight |
| **B** — full_folding 재학습 | **D-8a relaware COMPLETE, no deploy candidate** | Phase 2 Dataset/Model Registry 이후 D-8b 방향 결정 |
| **C** — full_folding ckpt replay 비교 | **COMPLETE** | 002000/003000/004000 모두 replay FAIL |
| **D** — 축/카메라 진단 | **custom 후속 폐기** | 첫 official rollout 시각 리뷰로 통합 평가 |
| **E** — banana handover 데이터 수집 | **COMPLETE** | rerun replay 시각 확인 후 학습/eval 방향 결정 |

---

## 미해결 이슈

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

5. **RESOLVED — D-9 cuDNN 환경 결정 완료, option (i), D-8a no-candidate**
   - A6000 torch `2.11.0+cu128` / CUDA `12.8` / cuDNN `91900` 환경에서 cuDNN enabled Conv2d 가 `CUDNN_STATUS_NOT_INITIALIZED` 로 실패했다.
   - 사용자 결정: option (i) torch 2.7.x + 호환 cuDNN 새 venv.
   - 새 venv: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
   - torch `2.7.1+cu126`, CUDA `12.6`, cuDNN `90501`, torchvision `0.22.1+cu126`
   - cuDNN enabled Conv2d smoke: PASS
   - 1-step train smoke: PASS with `dataset.video_backend=pyav`
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

1. **Phase 1 follow-up: feasibility 목표 재정의 + §7-bis 판정 기준**
   - 이 commit 으로 종결한다.

2. **Phase 2 Dataset Registry 총망라 작성**
   - `level2_final_quality3_t_0_hil_data_c`, `lerobot/full_folding`, A6000 relstats datasets, D-8a continuation dataset/config 를 한 표로 정리한다.
   - fps, camera, action/state contract, relative/absolute semantics, curation, SARM/RABC, gate/replay 결과를 포함한다.

3. **Phase 2 Model Registry v2 재스터디**
   - A6000 level2 corrected 004000, A6000 8766/8765 serving, `lerobot/folding_latest`, public folding 후보, base/pretrain 후보를 tier 로 분류한다.
   - 각 모델을 `official rollout 후보`, `serving truth source`, `metadata/gate only`, `reference only`, `not deploy` 로 구분한다.

4. **Phase 3 OpenArm follower connect side-effect 최소 패치**
   - `configure_on_connect`, `set_zero_position_on_connect`, `enable_torque_on_connect` config flag 를 추가한다.
   - 기본값은 upstream 동작 유지, OpenArm folding 실험 명령에서만 side effect 를 끈다.

5. **Phase 3 공식 `lerobot-rollout` preflight/load test**
   - `uv run lerobot-rollout --help`, config parse, policy metadata load, camera config, A6000 checkpoint local materialization 여부를 확인한다.
   - 실제 모션 없이 수행한다.

6. **operator 입회 후 official rollout 첫 모션 테스트**
   - operator 현장 입회, power abort, E-stop 준비를 확인한 뒤 실행한다.
   - 첫 실행 결과는 visual/task success, chunk transition, grasp 안정성, camera cable risk 중심으로 평가한다.

---

## 최근 핵심 결과

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
