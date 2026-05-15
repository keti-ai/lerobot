# OpenArm 폴딩 — 현재 상태

**마지막 갱신:** 2026-05-15  
**갱신 빈도:** PLAN.md 보다 자주. 매 작업 세션 직후 갱신 권장.

---

## 트랙별 현 상태

| Track | 상태 | 다음 행동 |
|---|---|---|
| **A** — syhlabtop level2 라이브 롤아웃 | UNBLOCKED | Track D 통과 후 messy shirt 첫 라이브 실행 |
| **B** — full_folding 재학습 | COMPLETE, replay FAIL | deploy 후보 아님. Track C 결과 기다림. |
| **C** — full_folding ckpt 002000/003000 replay 비교 | NOT STARTED | A6000 에서 `stage22_dataset_replay_and_ablation.py` 실행 |
| **D** — 축 probe + base 카메라 정렬 | NOT STARTED | `openarm_limit_axis_audit.py` 재실행 → operator probe |

---

## 미해결 이슈

1. **`full_folding` 004000 replay gate FAIL 원인 미확정**  
   - 측정값: model delta / recorded-delta ratio 0.128–0.282 (PASS 범위 0.25–4.0)  
   - 가설 A: underfit (step 부족) → 002000/003000 도 비슷하면 추가 학습 필요  
   - 가설 B: ckpt selection 문제 (특정 step 만 PASS) → 002000/003000 비교 필요  
   - 의존성: **Track C 실행 → 결정 D-3**

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

---

## 다음 N개 작업 (우선순위 순)

1. **Track C — full_folding ckpt 002000 replay gate**  
   - 위치: A6000  
   - 도구: `stage22_dataset_replay_and_ablation.py`  
   - 산출물: replay JSON + summary

2. **Track C — full_folding ckpt 003000 replay gate**  
   - 위 결과와 비교 → D-3 결정 입력

3. **Track D1 — `openarm_limit_axis_audit.py` read-only 재실행**  
   - 위치: syhlabtop  
   - 산출물: 현재 16D readback + 제한 마진 표

4. **Track D2 — left_joint_4 +1deg/-1deg 축 probe (operator 입회)**  
   - 위치: syhlabtop, operator 입회 필수  
   - 도구: 별도 단일 조인트 pulse 스크립트 (없으면 작성 = 결정 필요)

5. **Track D3 — base 카메라 alignment 확인**  
   - 위치: syhlabtop  
   - 도구: `syhlabtop_live_policy_input_viewer.py` + 데이터셋 mosaic 비교

6. **Track A — messy shirt 시나리오 첫 라이브 롤아웃**  
   - 사전조건: Track D1/D2/D3 통과, operator approval envelope 생성  
   - 명령: `trackA_level2_live_test_plan_2026-05-14.md` 의 템플릿

---

## 참조

- SSOT: `docs/PLAN.md`
- 운영 룰: `AGENTS.md` (= `CLAUDE.md` symlink)
- 운영 문서 인덱스: `audits/openarm_folding/README.md`
- 종료 작업 아카이브: `docs/_archive/openarm_folding/` + `docs/_archive/INDEX.md`
