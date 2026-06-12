# TS1 물리 튜닝 확정 결과 — 게인/속도/프로파일 스윕 (2026-06-12)

**판정**: 🟢 **TS1 (고주파 trajectory streamer) ≫ interp×3 — 확실한 물리적 개선 (operator + PNG 증거)**
**결과물**: `results/ts1_tuning_20260612/` (PNG 5 + CSV gz 2)
**확정 profile**: **`traj_trap_100_v120_kp18x13x`** (k4_eval_runner.py) — 새 기본 deploy profile

---

## 1. 스윕 narrative (D07s → D07v, operator 판정)

| trial | 변수 | 판정 |
|---|---|---|
| D07s_v120 / D07s_v120kp2x | TS1 첫 live + 손목 kp ×2 | TS1 동작 확인 |
| D07s_v120_gainA/B | 게인 default vs 손목×2 A/B | 게인 효과 확인 |
| D07t_default / D07t_kp2x14x | 손목×2+나머지×1.4 | 스윕 계속 |
| (operator 수렴) | **손목(j5/6/7) ×1.8 + 나머지 ×1.3** | **게인 확정** |
| D07u_v120 / D07u_v90 | v-clip 120 vs 90 (게인 고정) | **v120 확정** |
| **D07v_interp3 / D07v_ts1** | **before(interp×3) vs after(TS1)** | **TS1 확정** |

## 2. 핵심 증거 — D07v before/after PNG 판독

- **`traj_trial_D07v_interp3.png` (before)**: cmd qvel 에 **±200~400°/s 순간 스파이크**
  — VLA chunk/step 전환마다 선형 보간이 만드는 폭력적 속도 불연속. 그동안 "덜컥/톡톡"
  으로 관찰된 것의 그래프 실체.
- **`traj_trial_D07v_ts1.png` (after)**: cmd qvel 이 **±120°/s 안 사다리꼴 envelope**
  (trapezoidal profile), current q(readback)가 cmd q 를 타이트하게 추종. 스파이크 소멸.
- **`traj_compare_interp3_vs_ts1.png` (A/B overlay)**: 같은 task 궤적(q 곡선 유사)에서
  속도 스파이크만 제거 — 동작 의미 보존 + 실행 품질 개선.

보조: `traj_compare_v120_vs_v90.png` (v-clip 스윕), `traj_compare_default_vs_kp2x14x.png`
(게인 스윕). 원데이터: `traj_trial_D07v_{interp3,ts1}.csv.gz` (per-tick 16관절
setpoint/cmd q/cmd qvel/readback q/readback qvel).

## 3. 확정 deploy stack v2

```
[a6000 서버]  α'' 030000, bf16+torch.compile, RTC execution_horizon=20 (d≈9≤20≤21)
[syhlabtop]   TS1 trajectory streamer 100Hz trapezoidal  ← interp×3 대체
              v-clip 120°/s 전관절
              MIT kp = [312, 312, 312, 312, 43.2, 55.8, 45, 32.5]
                      (기본 [240×4, 24, 31, 25, 25] 에서 손목 j5/6/7 ×1.8, 나머지 ×1.3)
              kd 기본 유지 [5, 5, 3, 5, 0.3, 0.3, 0.3, 0.3]
              relative cap 없음 (profile v/a 한계 + joint_limits clip 이 안전층)
profile:      traj_trap_100_v120_kp18x13x
```

실행:
```bash
uv run python audits/openarm_folding/k4_eval_runner.py \
  --trial <id> --obj banana \
  --task "Pick the banana, hand it over to the other arm, and place it at the target." \
  --profile traj_trap_100_v120_kp18x13x --duration-s 60
```

## 4. 도구 (이번 스윕에서 구축)

| 도구 | 역할 |
|---|---|
| `src/lerobot/utils/joint_trajectory.py` | OnlineTrajectoryGenerator — trapezoidal/S-curve 온라인 궤적 (lead-compensated jerk-limited) |
| `robot_client.py` trajectory streamer | 전용 100Hz 스레드, VLA setpoint 추적, per-tick 로깅(trajectory_log_csv) |
| legacy 로깅 | interp/direct 경로도 동일 스키마 per-send 로깅 (before/after 비교 가능) |
| `ts1_wrist_probe.py` | 단일 관절 profile 이동 디버그 (target/cmd/readback, --kp/--kd) |
| `traj_log_plot.py` | run별 PNG + A/B overlay + 추적오차 요약 |
| ProfileSpec `position_kp/kd` | MIT per-packet 게인 override (비영구) |

## 5. 한계 / 다음

- 이건 **execution 품질 개선** — grasp 각도/방향 커버리지(미지, 데이터 영역)는 별개로 남음.
- 다음: ① stack v2 로 full-task 반복 trial (성공률이 occasional 에서 움직였나) →
  ② 오르면 N=20, 안 오르면 커버리지 규명 → data/finetune 분기 (`d42_methods_summary` §5.5).
