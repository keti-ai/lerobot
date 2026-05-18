# Track A RTC ON repeat3 120s 실행 기록

## 요약

- 실행 시각: 2026-05-18 19:00~19:02 KST
- trial: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_185509_rtc_on_repeat3`
- checkpoint: level2 corrected `004000`
- serving: `http://10.252.205.103:8766`
- RTC health: `rtc_enabled=true`, `rtc_execution_horizon=20`, `rtc_max_guidance_weight=10.0`, `rtc_prefix_attention_schedule=EXP`, `use_relative_actions=true`
- approval phrase: `APPROVE_LIVE_ROLLOUT_SESSION_ROLLOUT_TRIAL_20260518_185509_RTC_ON_REPEAT3`
- command path: `DamiaoMotorsBus guarded MIT batch`
- auxiliary recording: `../realsense_live` HTTP API 로 rollout 앞뒤에서 start/stop

## 실행 판정

- stop_reason: `max_session_duration_s`
- motion_status: `ROLLOUT_SESSION_ACTIVE`
- 막힘 발생 여부: 없음. `hard_block` 이벤트 없음, proposal validation warning 없음.
- actions_executed: `3031`
- chunks_accepted: `142`
- hard_readback_streak: `0`
- readback: `--readback-stride 0` 이므로 per-action readback 은 수행하지 않음.
- clipped_features: `735`
- gripper_saturated_features: `647`
- joint4_saturated_features: `2280`
- joint_limit_saturated_features: `7368`
- cleanup_errors: `[]`
- torque_disable_complete: `true`

action cadence:

- action 실행 구간 길이: `114.949s`
- action interval mean: `0.037937s`
- action interval p95: `0.039083s`
- action interval max: `0.072620s`
- event-derived max commanded delta mean: `4.875 deg`
- event-derived max commanded delta p95: `7.174 deg`
- event-derived max commanded delta max: `30.000 deg`

## 보조 RealSense 녹화

`../realsense_live` API 로 robot `--execute` 직전에 녹화를 시작하고 rollout 종료 직후 stop 했다.

- start 기록: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_185509_rtc_on_repeat3/live_session/realsense_record_start.json`
- stop 기록: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_185509_rtc_on_repeat3/live_session/realsense_record_stop.json`
- 녹화 파일: `/home/syhlabtop/workspace/realsense_live/recordings/rollout_trial_20260518_185509_rtc_on_repeat3.avi`
- 녹화 길이: `128.386s`
- 녹화 프레임: `3821`
- 파일 크기: `141,974,578 bytes`

판정: 보조 녹화 start/stop wrapper 는 정상 동작했다. 이후 robot execute recipe 에 포함해 항상 같은 방식으로 기록한다.

## RTC 반복 비교

events 에 full 16D action vector 가 기록되지 않으므로 실제 벡터 jerk `Δaction / Δt` 는 재구성할 수 없다.
아래 값은 이 문서에서 동일한 방식으로 재계산한 `max_abs_commanded_delta_deg` 기반 proxy 다.

| 항목 | RTC OFF first | RTC ON second | RTC ON repeat3 |
|---|---:|---:|---:|
| actions_executed | `2992` | `2907` | `3031` |
| chunks_accepted | `149` | `135` | `142` |
| action interval mean | `0.037985s` | `0.037979s` | `0.037937s` |
| event max-delta mean | `5.319 deg` | `4.662 deg` | `4.875 deg` |
| event max-delta p95 | `12.798 deg` | `7.112 deg` | `7.174 deg` |
| chunk 직후 첫 5 action max-delta mean | `8.415 deg` | `5.590 deg` | `5.939 deg` |
| chunk 직후 첫 5 action velocity proxy mean | `122.442 deg/s` | `42.625 deg/s` | `40.384 deg/s` |
| chunk 직후 첫 5 action jerk proxy mean | `5472.991` | `1470.131` | `1335.294` |
| chunk 직후 첫 5 action jerk proxy p95 | `18380.796` | `5413.840` | `5156.567` |

판정: repeat3 도 RTC ON second 와 같은 smoothness 개선 방향이다. RTC OFF 대비 chunk 직후 scalar jerk proxy 는 낮고, RTC ON second 대비도 mean/p95 가 소폭 더 낮다. 다만 joint4/joint_limit saturation 은 repeat3 에서 증가했으므로, 시각 결과와 함께 판단해야 한다.

## 시각 검증

eval frame 경로:

```text
/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_185509_rtc_on_repeat3/live_session/eval_frames/
```

샘플:

- `obs_000000`
- `obs_000030`
- `obs_000060`
- `obs_000090`
- `obs_000120`

operator post-review 는 아직 별도 기록 전이다. 직전 리뷰는 RTC ON 적용 후 chunk lip 이 일부 감소했다는 판정이었다. 이번 repeat3 는 보조 D415 녹화가 있으므로, eval frames 와 AVI 를 같이 보며 chunk lip 과 fold 진행도를 다시 판정한다.

## 다음 권장

1. repeat3 보조 AVI 와 eval frames 를 기준으로 operator 시각 리뷰를 기록한다.
2. chunk lip 이 여전히 남으면 `max_guidance_weight 5 vs 10 vs 15` 를 먼저 비교한다.
3. saturation 이 결과 품질에 영향을 준다고 보이면 joint4/joint_limit saturation 시점과 eval frame 구간을 맞춰 본다.
4. 실제 벡터 jerk 분석이 필요하면 `events.ndjson` 에 full 16D action 또는 per-feature delta summary 를 추가한다.
