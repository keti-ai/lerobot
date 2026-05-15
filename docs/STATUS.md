# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-05-15 (syhlabtop D1/D3 read-only 결과 반영)  
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop level2 라이브 롤아웃 | UNBLOCKED | Track D 통과 후 messy shirt 첫 라이브 실행 |
| **B** — full_folding 재학습 | **DECISION_PENDING** | D-9 cuDNN 환경 결정 후 D-8a/D-8b 진행 |
| **C** — full_folding ckpt 002000/003000 replay 비교 | **COMPLETE** | ckpt 002000/003000/004000 모두 replay FAIL → deploy 후보 없음 |
| **D** — 축 probe + base 카메라 정렬 | D1 완료, D3 캡처 완료/참조 비교 대기 | a6000 visual refs manifest 확보 후 side-by-side, 이후 operator probe |

---

## 미해결 이슈

1. **`full_folding` replay FAIL 원인 — checkpoint selection 가설 기각**  
   - ckpt 002000: ratio 0.220–0.320, raw normalized max error 0.433 → FAIL  
   - ckpt 003000: ratio 0.142–0.348, raw normalized max error 0.402 → FAIL  
   - ckpt 004000: ratio 0.128–0.282, raw normalized max error 0.413 → FAIL  
   - 결론: 단순 checkpoint selection 으로 해결 불가. 다음은 **underfit 추가 학습(D-8a)** 또는 **fold-only 재학습(D-8b)** 결정 필요.  
   - 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/full_folding_dataset_replay_{002000,003000}.{md,json}`

2. **base 카메라 FOV/scale 미스매치**  
   - D3 live capture: `/tmp/openarm_folding_policy_input_viewer/policy_input_view_20260515_144933/`  
   - 세 카메라 모두 `640x480@30`, `/status.json` 오류 없음, `read_only=true`, `robot_io=false`  
   - base 캡처는 테이블과 셔츠를 넓게 포함하나, a6000 `full_folding_visual_refs_manifest_20260514.json` 이 syhlabtop 로컬에 없고 `ssh 10.252.205.103` 접근이 거부되어 dataset reference side-by-side 판정은 남음  
   - 의존성: 결정 D-6 (물리 raise vs preprocessing transform)

3. **`left_joint_{4,5,6,7}` + 양 gripper 축 sign 미검증**  
   - 라이브 롤아웃에서 left wrist 키들의 saturation 빈도 높음  
   - D1 read-only audit: `/home/syhlabtop/openarm_folding_20260512/audits/limit_axis_audit_20260515_144443.{md,json}`  
   - 현재 16D readback 은 모두 software limit 안. 최저 마진: `right_joint_4.pos` 4.492 deg, `left_gripper.pos` 5.451 deg, `left_joint_4.pos` 5.606 deg, `right_joint_2.pos` 8.727 deg, `right_gripper.pos` 8.841 deg, `left_joint_2.pos` 11.284 deg  
   - rollout 로그 증상은 계속 left wrist 중심: hard readback key top = `left_joint_7.pos` 26, `left_joint_5.pos` 22, `left_joint_4.pos` 14, `left_joint_1.pos` 12  
   - 진단: current readback 은 안전 범위 안이지만, 실제 물리 sign/zero/comfortable range 불일치 가능성은 아직 남음  
   - 의존성: 결정 D-7 (operator 입회 probe)

4. **wrist 카메라 capture/training 해상도 차이**  
   - syhlabtop 측 640×480 캡처 → server 가 1280×720 으로 resize 후 모델 입력  
   - 서버 측 resize 가 정확히 training 분포와 일치하는지 검증 안 됨

5. **D-9 cuDNN 환경 미해결**  
   - A6000 torch `2.11.0+cu128` / CUDA `12.8` / cuDNN `91900` / driver `570.133.20` 환경에서 cuDNN enabled Conv2d 가 `CUDNN_STATUS_NOT_INITIALIZED` 로 실패  
   - 우회 `torch.backends.cudnn.enabled=False` 는 추론에만 사용. 학습은 환경 결정 전 금지  
   - 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/cudnn_env_review_20260515_140817.md`

6. **a6000(ketiserver) 측 워크트리 동기화 부재 — 참고만**  
   - a6000 Codex 세션이 본 워크트리에는 audits/openarm_folding/ 의 현역 md/py 일부가 untracked/누락 상태였음  
   - 이는 a6000 측 클론의 동기화 문제로, syhlabtop 워크트리 (= 현재) 에는 해당 없음  
   - 향후 작업 전 a6000 측에서 `git fetch && git checkout audit/openarm-folding-baseline` 후 작업 권장

---

## 다음 N개 작업 (우선순위 순)

1. **D-9 사용자 결정** — cuDNN 환경 정비 옵션 선택  
   - (i) torch 2.7.x + 호환 cuDNN 새 venv (가장 안정적)  
   - (ii) torch 2.11.0 유지 + cuDNN 별도 정비  
   - (iii) Docker 격리

2. **D-9 후속** — 선택한 환경에서 cuDNN enabled Conv2d + 짧은 train smoke 검증

3. **D-8a (B 재오픈)** — 003000 에서 8000/16000 step 추가 학습으로 underfit 가설 검증  
   - 위치: A6000, D-9 해결 후

4. **D-8b (B 재오픈, 병행 가능)** — fold-only subset (4100 eps) 생성 및 별도 재학습  
   - 위치: A6000, D-9 해결 후

5. **Track D3 후속** — base 카메라 alignment side-by-side 판정  
   - 위치: syhlabtop  
   - 입력: live capture `/tmp/openarm_folding_policy_input_viewer/policy_input_view_20260515_144933/`  
   - 필요: a6000 측 `full_folding_visual_refs_manifest_20260514.json` 및 `visual_refs/` 접근 또는 syhlabtop 전송

6. **Track D2** — 단일 조인트 축 probe 스펙 확정 및 operator 입회 실행  
   - 스펙: 한 joint 씩 selected motor torque only, 시작값 기준 `+1deg → return → -1deg → return`  
   - 우선 대상: `left_joint_{4,5,6,7}` + `right_gripper.pos` + `left_gripper.pos`  
   - 금지: operator 입회 없이 실행, `OpenArmFollower.connect()`, `send_action()`, `lerobot-rollout`, Damiao persistent setting 변경

7. **Track A draft** — messy shirt 시나리오 approval envelope 생성  
   - 사전조건: D3 reference 비교 또는 operator visual 판정, D2 방향 probe 결정  
   - 단독 실행 가능 범위: `trackA_level2_live_test_plan_2026-05-14.md` 첫 번째 커맨드 블록의 draft envelope 생성만, `--execute` 없음

8. **Track A execute** — messy shirt 첫 라이브 롤아웃  
   - 사전조건: operator 입회 + draft approval phrase + safety envelope 확인

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
D2 tiny direction probe 는 계속 필요하다.

### D3 — live policy input capture

```text
capture_dir: /tmp/openarm_folding_policy_input_viewer/policy_input_view_20260515_144933/
profiles:    left_wrist=640x480@30, right_wrist=640x480@30, base=640x480@30
status:      errors=[], read_only=true, robot_io=false, actuator_commands_sent=false
```

판정: live camera capture 자체는 정상이다. a6000 visual reference manifest 가
syhlabtop 로컬에 없고 현재 ssh 접근이 거부되어, `full_folding` reference 와의
side-by-side 판정은 manifest/visual_refs 전송 후 다시 수행해야 한다.

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
  D-8 추가 학습은 환경 결정 전 시작 금지.
  cuDNN 우회 설정은 학습에 사용 금지 (속도 치명적 + 결과 신뢰성).
```

선택지 (사용자 결정 대기):
- (i) torch 2.7.x + 호환 cuDNN 새 venv
- (ii) torch 2.11.0 유지 + cuDNN 별도 정비
- (iii) Docker 격리

산출물 커밋: `33ee0da4 docs: record cudnn environment review`

---

## 참조

- SSOT: `docs/PLAN.md`
- 운영 룰: `AGENTS.md` (= `CLAUDE.md` symlink)
- 운영 문서 인덱스: `audits/openarm_folding/README.md`
- 종료 작업 아카이브: `docs/_archive/openarm_folding/` + `docs/_archive/INDEX.md`
- a6000 측 산출물 루트: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/`
