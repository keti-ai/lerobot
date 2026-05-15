# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-05-15 (D-9 option i 선택 + syhlabtop 병행 작업 의미 정정)  
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop level2 라이브 롤아웃 | UNBLOCKED | Track D 통과 후 messy shirt 첫 라이브 실행 |
| **B** — full_folding 재학습 | **IN_PROGRESS** | A6000 D-8 추가 재학습 산출물 수신 후 recipe/replay gate |
| **C** — full_folding ckpt 002000/003000 replay 비교 | **COMPLETE** | ckpt 002000/003000/004000 모두 replay FAIL → deploy 후보 없음 |
| **D** — 축 probe + base 카메라 정렬 | IN_PROGRESS (syhlabtop 병행 작업) | D1 read-only audit, D3 camera alignment 확인 |

---

## 미해결 이슈

1. **`full_folding` replay FAIL 원인 — checkpoint selection 가설 기각**  
   - ckpt 002000: ratio 0.220–0.320, raw normalized max error 0.433 → FAIL  
   - ckpt 003000: ratio 0.142–0.348, raw normalized max error 0.402 → FAIL  
   - ckpt 004000: ratio 0.128–0.282, raw normalized max error 0.413 → FAIL  
   - 결론: 단순 checkpoint selection 으로 해결 불가. D-8 추가 재학습 진행/산출물 대기.  
   - 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/full_folding_dataset_replay_{002000,003000}.{md,json}`

2. **base 카메라 FOV/scale 미스매치**  
   - 현 카메라 height 에서 shirt 보이지만 팔 크기가 dataset 보다 작음  
   - 의존성: 결정 D-6 (물리 raise vs preprocessing transform)

3. **`left_joint_{4,5,6,7}` + 양 gripper 축 sign 미검증**  
   - 라이브 롤아웃에서 left wrist 키들의 saturation 빈도 높음  
   - 진단: software limit 안 vs 실제 물리 sign 불일치 둘 다 가능  
   - 의존성: 결정 D-7 (operator 입회 probe)

4. **wrist 카메라 capture/training 해상도 차이**  
   - syhlabtop 측 640×480 캡처 → server 가 1280×720 으로 resize 후 모델 입력  
   - 서버 측 resize 가 정확히 training 분포와 일치하는지 검증 안 됨

5. **D-9 cuDNN 환경 결정 완료 — option (i)**  
   - A6000 torch `2.11.0+cu128` / CUDA `12.8` / cuDNN `91900` / driver `570.133.20` 환경에서 cuDNN enabled Conv2d 가 `CUDNN_STATUS_NOT_INITIALIZED` 로 실패  
   - 사용자 결정: **(i) torch 2.7.x + 호환 cuDNN 새 venv**  
   - 우회 `torch.backends.cudnn.enabled=False` 는 추론에만 사용. 학습에는 사용 금지  
   - 산출물: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/cudnn_env_review_20260515_140817.md`

6. **a6000(ketiserver) 측 워크트리 동기화 부재 — 참고만**  
   - a6000 Codex 세션이 본 워크트리에는 audits/openarm_folding/ 의 현역 md/py 일부가 untracked/누락 상태였음  
   - 이는 a6000 측 클론의 동기화 문제로, syhlabtop 워크트리 (= 현재) 에는 해당 없음  
   - 향후 작업 전 a6000 측에서 `git fetch && git checkout audit/openarm-folding-baseline` 후 작업 권장

---

## 다음 N개 작업 (우선순위 순)

1. **D-8 학습 모니터링** — A6000 추가 재학습 산출물 대기  
   - 세부 run path, checkpoint 목록, smoke 결과는 A6000 산출물 수신 후 기록

2. **D-8 gate 실행** — 각 산출 checkpoint 에 대해 recipe gate + dataset replay gate 실행

3. **D-8 결과 판정** — replay PASS checkpoint 가 있으면 deploy 후보 검토, 없으면 데이터/recipe 재설계 결정

4. **Track D1 병행 작업** — `openarm_limit_axis_audit.py` read-only 재실행  
   - 위치: syhlabtop (a6000 에서는 실행 불가)  
   - 모션 없음, CAN 읽기만

5. **Track D3 병행 작업** — base 카메라 alignment 확인  
   - 위치: syhlabtop  
   - 도구: `syhlabtop_live_policy_input_viewer.py` + a6000 측 `full_folding_visual_refs_manifest` 비교

6. **Track D2** — left_joint_4 +1deg/-1deg 축 probe (operator 입회 필수)

7. **Track A** — messy shirt 시나리오 첫 라이브 롤아웃 (D1+D3 통과 + operator approval 후)

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

사용자 결정:
- **(i) torch 2.7.x + 호환 cuDNN 새 venv**

현재 상태:
- D-8 추가 재학습 진행/산출물 대기.
- "병행 작업"은 syhlabtop Track D1/D3 쪽 작업을 뜻한다.
- 세부 run path, checkpoint 목록, gate 결과는 A6000 산출물 수신 후 기록.

산출물 커밋: `33ee0da4 docs: record cudnn environment review`

---

## 참조

- SSOT: `docs/PLAN.md`
- 운영 룰: `AGENTS.md` (= `CLAUDE.md` symlink)
- 운영 문서 인덱스: `audits/openarm_folding/README.md`
- 종료 작업 아카이브: `docs/_archive/openarm_folding/` + `docs/_archive/INDEX.md`
- a6000 측 산출물 루트: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/`
