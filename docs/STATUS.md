# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-05-18 (Track A 첫 closed-loop 120s 완주 + A6000 RTC health 노출 + D-8a relaware 재판정)
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop level2 라이브 롤아웃 | **첫 120s closed-loop 완주** | 실행 로그/시각 결과 기반 다음 파라미터 조정 |
| **B** — full_folding 재학습 | **D-8a relaware COMPLETE — no deploy candidate** | D-8b fold-only 또는 추가 step 여부 결정 |
| **C** — full_folding ckpt 002000/003000 replay 비교 | **COMPLETE** | ckpt 002000/003000/004000 모두 replay FAIL → deploy 후보 없음 |
| **D** — 축 probe + base 카메라 정렬 | read-only 결과 보존, 단일 조인트 probe/side-by-side 후속 폐기 | closed-loop 긴 타임시퀀스 평가로 전환 |

---

## 미해결 이슈

1. **`full_folding` replay FAIL 원인 — checkpoint selection 가설 기각**
   - ckpt 002000: ratio 0.220–0.320, raw normalized max error 0.433 → FAIL
   - ckpt 003000: ratio 0.142–0.348, raw normalized max error 0.402 → FAIL
   - ckpt 004000: ratio 0.128–0.282, raw normalized max error 0.413 → FAIL
   - 결론: 단순 checkpoint selection 으로 해결 불가. D-9 torch 2.7 smoke는 통과했고, D-8a 003000 continuation 도 deploy 후보를 만들지 못했다.
   - 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/full_folding_dataset_replay_{002000,003000}.{md,json}`
   - D-8a config: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/d8a_full_folding_continue_003000_torch27_pyav_config_20260515.json`
   - D-8a command: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/d8a_full_folding_continue_003000_torch27_pyav_command_20260515.md`
   - D-8a current gate: `001000`~`012000` 모두 recipe FAIL, replay SKIPPED. D-10c에서 false-negative로 판정.
   - D-8a relstats-aware 재판정: `001000`~`012000` 모두 recipe PASS, replay FAIL. ratio 0.125–0.468, arm raw max err 0.361–0.513. deploy 후보 없음.
   - D-10c 결론: full_folding 003000과 D-8a 012000의 postprocessor stats diff는 0.0. RABC는 `sample_weighting` 에 기록되어 있다. current `stage29/stage22` gate가 relstats-aware contract와 맞지 않는다.
   - D-8a summary: `audits/openarm_folding/a6000_d8a_gate_summary.md`, `audits/openarm_folding/a6000_d8a_no_candidate.md`
   - D-8a relaware summary: `audits/openarm_folding/a6000_d8a_gate_summary_relaware.md`, `audits/openarm_folding/a6000_d8a_no_candidate_relaware.md`
   - D-10c diagnosis: `audits/openarm_folding/a6000_d10c_postprocessor_rabc_diagnosis_20260518.md`

2. **base 카메라 FOV/scale 미스매치 — side-by-side 후속 폐기**
   - D3 live capture: `/tmp/openarm_folding_policy_input_viewer/policy_input_view_20260515_144933/`
   - 세 카메라 모두 `640x480@30`, `/status.json` 오류 없음, `read_only=true`, `robot_io=false`
   - base 캡처는 테이블과 셔츠를 넓게 포함하나, a6000 `full_folding_visual_refs_manifest_20260514.json` 이 syhlabtop 로컬에 없고 `ssh 10.252.205.103` 접근이 거부되어 dataset reference side-by-side 판정은 완료하지 않았다
   - 운영 결정: 별도 mosaic/side-by-side 보고서는 재개하지 않는다. 실제 의미 있는 검증은 120초 closed-loop 타임시퀀스에서 수행한다.

3. **`left_joint_{4,5,6,7}` + 양 gripper 축 sign 미검증 — 단일 조인트 probe 폐기**
   - 라이브 롤아웃에서 left wrist 키들의 saturation 빈도 높음
   - D1 read-only audit: `/home/syhlabtop/openarm_folding_20260512/audits/limit_axis_audit_20260515_144443.{md,json}`
   - 현재 16D readback 은 모두 software limit 안. 최저 마진: `right_joint_4.pos` 4.492 deg, `left_gripper.pos` 5.451 deg, `left_joint_4.pos` 5.606 deg, `right_joint_2.pos` 8.727 deg, `right_gripper.pos` 8.841 deg, `left_joint_2.pos` 11.284 deg
   - rollout 로그 증상은 계속 left wrist 중심: hard readback key top = `left_joint_7.pos` 26, `left_joint_5.pos` 22, `left_joint_4.pos` 14, `left_joint_1.pos` 12
   - 운영 결정: 단일 조인트 `+1deg/-1deg` probe 는 재개하지 않는다. operator 입회 closed-loop 실행에서 전체 시퀀스 흐름, saturation, readback, visual result 를 함께 본다.

4. **wrist 카메라 capture/training 해상도 차이**
   - syhlabtop 측 640×480 캡처 → server 가 1280×720 으로 resize 후 모델 입력
   - 서버 측 resize 가 정확히 training 분포와 일치하는지 검증 안 됨

5. **RESOLVED — D-9 cuDNN 환경 결정 완료, option (i), D-8a no-candidate**
   - A6000 torch `2.11.0+cu128` / CUDA `12.8` / cuDNN `91900` / driver `570.133.20` 환경에서 cuDNN enabled Conv2d 가 `CUDNN_STATUS_NOT_INITIALIZED` 로 실패
   - 사용자 결정: **(i) torch 2.7.x + 호환 cuDNN 새 venv**
   - 새 venv: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
   - torch `2.7.1+cu126`, CUDA `12.6`, cuDNN `90501`, torchvision `0.22.1+cu126`
   - cuDNN enabled Conv2d smoke: PASS
   - 1-step train smoke: PASS with `dataset.video_backend=pyav` (`loss=0.191`, `grad_norm=2.538`)
   - torchcodec backend: FAIL. `torchcodec 0.6.0` imports but LeRobot file-like `VideoDecoder` path fails at `torchcodec_ns::_convert_to_tensor`
   - D-8 config must use `dataset.video_backend=pyav` unless torchcodec compatibility is fixed
   - current repo `AdamWConfig` does not accept `optimizer.foreach`; D-8 config must remove that field or make an explicit config/code decision
   - 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/cudnn_env_review_20260515_140817.md`
   - smoke 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/d9_torch27_train_smoke_20260515.{md,json}`
   - D-8a 시작: `20260515_163251`
   - D-8a 최신 상태 파일: `audits/openarm_folding/a6000_d8a_status.md`
   - 현재 상태: 012000 checkpoint까지 저장 후 step 12120 부근에서 `FrameTimestampError` 로 종료.
   - 실패 파일: `videos/observation.images.right_wrist/chunk-000/file-557.mp4`, queried timestamp 1352.2334 vs loaded 1352.2333 근방, tolerance 0.0001 초과.
   - 생성된 001000~012000 checkpoint는 current gate 기준 recipe FAIL이었으나 relaware gate 기준 recipe PASS로 복구.
   - relaware replay는 001000~012000 모두 FAIL. deploy 후보 없음.

6. **RESOLVED — A6000 serving 복구 + Track A 첫 closed-loop 완주**
   - `http://10.252.205.103:8766/health`, `http://10.252.205.103:8765/health` 모두 OK
   - 8766 live: level2 corrected 004000, `send_allowed=false`, `motion_allowed=false`
   - 8766 RTC: `rtc_enabled=true`, `rtc_execution_horizon=20`, `rtc_max_guidance_weight=10.0`, `rtc_prefix_attention_schedule=EXP`, `use_relative_actions=true`
   - 8765 snapshot: level2 corrected 004000, `send_allowed=false`, `motion_allowed=false`
   - 산출물: `audits/openarm_folding/a6000_serving_restored_20260518.md`
   - RTC 산출물: `audits/openarm_folding/a6000_rtc_status_20260518.md`
   - 첫 성공 trial: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_131245_level2_messy_shirt_retry_no_readback_fix/`
   - 결과: `stop_reason=max_session_duration_s`, `actions_executed=2992`, `chunks_accepted=149`, `torque_disable_complete=true`, `cleanup_errors=[]`
   - 이벤트: `hard_block=0`, proposal validation warning `0`
   - saturations: clipped `805`, gripper `648`, joint4 `0`, joint_limit `3049`
   - 결과 문서: `audits/openarm_folding/trackA_first_closed_loop_run_20260518_131627.md`

7. **a6000(ketiserver) 측 워크트리 동기화 부재 — 참고만**
   - a6000 Codex 세션이 본 워크트리에는 audits/openarm_folding/ 의 현역 md/py 일부가 untracked/누락 상태였음
   - 이는 a6000 측 클론의 동기화 문제로, syhlabtop 워크트리 (= 현재) 에는 해당 없음
   - 향후 작업 전 a6000 측에서 `git fetch && git checkout audit/openarm-folding-baseline` 후 작업 권장

---

## 다음 N개 작업 (우선순위 순)

1. **Track A 실행 로그 분석 — saturation 상위 feature/구간 집계**
   - 입력: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_131245_level2_messy_shirt_retry_no_readback_fix/live_session/events.ndjson`
   - 목표: joint_limit/gripper saturation 이 높은 원인을 feature 별로 나눠 다음 파라미터 조정을 정한다.

2. **Track B 다음 방향 결정**
   - D-8a relaware 결과도 no-candidate.
   - D-8b fold-only subset 재학습 또는 D-8a 추가 step 중 하나를 사용자 결정으로 선택한다.

3. **Track A 두 번째 120s 실행 준비**
   - 같은 120s/180chunk 설정을 기본값으로 유지한다.
   - scene 초기조건과 shirt 중심 위치를 더 일관되게 맞춘 뒤 새 envelope 를 생성한다.

4. **full_folding gate 산출물 기준 정리**
   - D-8a relaware 결과를 README/PLAN 의 다음 결정 항목과 일치시킨다.

---

## Track A closed-loop 120s 준비 결과 (syhlabtop 세션, 2026-05-15)

```text
rollout_code_commit: ff30a8ba
trackA_template_commit: 0be660e8 + 6ab128a0
syntax_check: uv run python -c ast.parse(...) → OK
chunk_contract: proposal shape [1, 30, 16], 30 Hz, max action horizon 20
session_shape: 120s, max_chunks=180, readback_stride=0, hold_last_action=true
dry_run_trial: /home/syhlabtop/openarm_folding_20260512/rollout_trial_20260515_164553_closed_loop_dryrun/
```

판정: 코드/템플릿 인프라는 준비됐다. A6000 serving 이 내려가 있어 health 기반
`session_envelope.{json,md}` 는 아직 생성되지 않았다. dry-run summary 는 모션 없이
생성됐고 actuator command 는 없었다.

---

## Track A 첫 closed-loop 120s 실행 결과 (syhlabtop 세션, 2026-05-18)

```text
trial: /home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_131245_level2_messy_shirt_retry_no_readback_fix/
report: audits/openarm_folding/trackA_first_closed_loop_run_20260518_131627.md
rollout_fix_commit: 20ec9a05
stop_reason: max_session_duration_s
actions_executed: 2992
chunks_accepted: 149
torque_disable_complete: true
cleanup_errors: []
```

판정: 첫 120초 closed-loop 는 runtime 막힘 없이 완주했다. eval frame 5개 샘플 중
시작 이후 4개 샘플에서 양팔 접근/접촉과 셔츠 형태 변화가 보인다. 완성 fold 는
아니며, 다음 작업은 saturation feature 분석과 scene 초기조건 개선이다.

---

## Track D read-only 결과 (syhlabtop 세션, 2026-05-15)

### D1 — limit/axis readback audit

```text
artifact_md:   /home/syhlabtop/openarm_folding_20260512/audits/limit_axis_audit_20260515_144443.md
artifact_json: /home/syhlabtop/openarm_folding_20260512/audits/limit_axis_audit_20260515_144443.json
read_path:     DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states()
actuation:     false
send_action:   false
```

판정: 현재 16D readback 은 모두 software limit 안이다. 다만 최저 마진이
`right_joint_4.pos`, `left_gripper.pos`, `left_joint_4.pos` 에 몰려 있고,
기존 rollout log 의 hard readback top 이 `left_joint_7/5/4/1` 에 집중되어
closed-loop 실행에서 saturation/readback/visual 흐름을 함께 관찰한다. 단일 조인트
probe 는 재개하지 않는다.

### D3 — live policy input capture

```text
capture_dir: /tmp/openarm_folding_policy_input_viewer/policy_input_view_20260515_144933/
profiles:    left_wrist=640x480@30, right_wrist=640x480@30, base=640x480@30
status:      errors=[], read_only=true, robot_io=false, actuator_commands_sent=false
```

판정: live camera capture 자체는 정상이다. a6000 visual reference manifest 가
syhlabtop 로컬에 없고 현재 ssh 접근이 거부되어 `full_folding` reference 와의
side-by-side 판정은 완료하지 않았다. 별도 mosaic 비교는 재개하지 않고,
120초 closed-loop 타임시퀀스에서 의미를 본다.

---

## Track C 결과 (a6000 세션, 2026-05-15)

```
ckpt 002000: recipe PASS, replay FAIL
  ratio 0.220–0.320 (threshold 0.25–4.0)
  raw normalized max error 0.433 (threshold 0.25)
  max global delta 4.799 deg

ckpt 003000: recipe PASS, replay FAIL
  ratio 0.142–0.348
  raw normalized max error 0.402   ← 셋 중 가장 낮음
  max global delta 2.026 deg

ckpt 004000: recipe PASS, replay FAIL (기존)
  ratio 0.128–0.282
  raw normalized max error 0.413
  max global delta 2.086 deg
```

결론: 003000 이 raw error 면에서 가장 양호하지만 threshold 0.25 와 격차 큼.
checkpoint selection 만으로는 deploy 후보 확보 불가. **underfit 가설이 유력** —
추가 학습 또는 데이터 큐레이션 (fold-only) 이 다음 단계.

산출물 커밋: `378e2bd9 docs: record full_folding checkpoint replay comparison`

---

## D-9 cuDNN 환경 리뷰 (a6000 세션, 2026-05-15)

```
확인 환경:
  host: ketiserver (a6000)
  GPU:    RTX A6000 × 4
  driver: 570.133.20
  torch:  2.11.0+cu128
  CUDA:   12.8
  cuDNN:  91900

결과:
  cuDNN enabled Conv2d → CUDNN_STATUS_NOT_INITIALIZED (FAIL)
  torch.backends.cudnn.enabled=False → 같은 Conv2d 통과 (우회 가능)

판정:
  option (i) 선택 전에는 D-8 추가 학습 시작 금지.
  cuDNN 우회 설정은 학습에 사용 금지 (속도 치명적 + 결과 신뢰성).
```

사용자 결정:
- **(i) torch 2.7.x + 호환 cuDNN 새 venv**

현재 상태:
- D-9 option (i) torch 2.7 venv smoke PASS.
- D-8a 003000 continuation 은 step 12120 부근에서 `FrameTimestampError` 로 종료. checkpoint 012000까지 저장됨.
- D-8a 001000~012000 recipe gate 모두 FAIL, replay SKIPPED, deploy 후보 없음.
- "병행 작업"은 syhlabtop Track D1/D3 쪽 작업을 뜻한다.
- 세부 run path, checkpoint 목록, gate 결과는 `audits/openarm_folding/a6000_d8a_gate_summary.md` 참조.

산출물 커밋: `33ee0da4 docs: record cudnn environment review`

---

## 참조

- SSOT: `docs/PLAN.md`
- 운영 룰: `AGENTS.md` (= `CLAUDE.md` symlink)
- 운영 문서 인덱스: `audits/openarm_folding/README.md`
- 종료 작업 아카이브: `docs/_archive/openarm_folding/` + `docs/_archive/INDEX.md`
- a6000 측 산출물 루트: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/`
