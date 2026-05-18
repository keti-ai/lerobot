# Track A RTC ON repeat 부분 실행 중단 기록

## 요약

- 실행 시각: 2026-05-18 18:45 KST
- trial: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_184402_rtc_on_repeat`
- checkpoint: level2 corrected `004000`
- RTC health: `rtc_enabled=true`, `rtc_execution_horizon=20`, `rtc_max_guidance_weight=10.0`, `rtc_prefix_attention_schedule=EXP`, `use_relative_actions=true`
- approval phrase: `APPROVE_LIVE_ROLLOUT_SESSION_ROLLOUT_TRIAL_20260518_184402_RTC_ON_REPEAT`
- command path: `DamiaoMotorsBus guarded MIT batch`

## 중단 원인

사용자/operator 확인:

- 오른팔이 기둥 쪽으로 가면서 right wrist 카메라 케이블이 물리적으로 빠졌다.
- 따라서 이 실행의 중단 원인은 RTC/정책 smoothness 문제가 아니라 카메라 케이블 탈락이다.

events 기준:

- `actions_executed`: `1118`
- `chunks_accepted`: `19`
- action 실행 구간 길이: `42.400s`
- 마지막 실행 step: `1117`
- `inference_error`: `right_wrist read failed after 2 attempts: wait_for_frames cannot be called before start()`
- event-derived max commanded delta max: `17.881 deg`
- event-derived max commanded delta mean: `3.270 deg`

## summary 기록 메모

이 실행은 카메라 cleanup 중 `pipeline.stop()` 예외가 발생하여 execute summary 를 덮어쓰지 못했다.
trial 의 `summary.json` 은 draft summary 상태로 남아 있다.

후속 수정:

- `5af32b7a tools(rollout): keep summary writing robust on camera cleanup errors`
- 내용: camera cleanup 예외가 발생해도 motor cleanup 뒤 summary 를 기록하도록 변경했다.
- 이 수정은 모션/정책/RTC 경로를 바꾸지 않는다.

## 다음 조치

1. right wrist 카메라 케이블을 재체결하고, 오른팔이 기둥 쪽으로 갈 때 당겨지지 않도록 cable slack/strain relief 를 만든다.
2. 같은 trial 은 재사용하지 않는다. 새 trial/envelope/approval phrase 로 재시도한다.
3. 다음 실행 전 RealSense enumerate 와 8766 health 를 다시 확인한다.
