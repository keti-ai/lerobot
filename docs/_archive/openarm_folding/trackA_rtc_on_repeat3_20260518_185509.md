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

## operator 리뷰

사용자/operator post-review:

- 정책이 tabletop folding 태스크를 수행하려는 방향성은 보인다.
- 그러나 실제 작업 수행력은 아직 부족하다. 옷을 안정적으로 집지 못했고, fold 성공으로 보기는 어렵다.
- 끊김은 아직 남아 있다. RTC ON 으로 일부 감소했지만, chunk 사이 transition 이 시각적으로 여전히 보인다.
- 다음에는 chunk size, action Hz, execution horizon, queue refresh 조건의 최적점을 찾아야 한다.
- 기본 pi0.5 대비 folding demo/robot execution 쪽에 추가로 들어간 trick 이 무엇인지 확실히 분석해야 한다.
- 현재 정책은 작업 수행력과 OOD 영역이 모두 넓어 보인다. scene/garment 초기조건 변화에 대한 견고성도 아직 부족하다.

판정: repeat3 는 runtime closed-loop 인프라 검증은 PASS 이지만, task success 는 PASS 가 아니다. 다음 단계는 무작정 재실행이 아니라 execution cadence/queue tuning 과 pi0.5 folding 운영 trick 분석이다.

## 다음 권장

1. pi0.5/OpenArm folding reference 에서 execution trick 을 정리한다. 특히 chunk handoff, action repeat/interpolation, receding horizon, inference cadence, camera/record timing, safety/hold behavior 를 확인한다.
2. chunk size / action Hz / execution horizon / refresh threshold sweep 설계를 만든다. 우선 동일 checkpoint 에서 runtime 변수만 바꿔 chunk lip 을 줄일 수 있는지 본다.
3. 실제 벡터 jerk 분석이 필요하면 `events.ndjson` 에 full 16D action 또는 per-feature delta summary 를 추가한다.
4. saturation 이 결과 품질에 영향을 준다고 보이면 joint4/joint_limit saturation 시점과 eval frame 구간을 맞춰 본다.
5. 재실행은 tuning 가설을 먼저 세운 뒤 같은 messy-shirt setup 으로 비교한다.
