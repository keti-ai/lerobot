# Track A 첫 closed-loop 120s 실행 결과

## 요약

- 실행 시각: 2026-05-18 13:14~13:16 KST
- trial: `/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_131245_level2_messy_shirt_retry_no_readback_fix`
- checkpoint: level2 corrected `004000`
- serving: `http://10.252.205.103:8766`
- approval phrase: `APPROVE_LIVE_ROLLOUT_SESSION_ROLLOUT_TRIAL_20260518_131245_LEVEL2_MESSY_SHIRT_RETRY_NO_READBACK_FIX`
- command path: `DamiaoMotorsBus guarded MIT batch`
- forbidden paths: `send_action=false`, `lerobot-rollout=false`, `OpenArmFollower.connect=false`

## 실행 판정

- stop_reason: `max_session_duration_s`
- motion_status: `ROLLOUT_SESSION_ACTIVE`
- 막힘 발생 여부: 없음. `hard_block` 이벤트 없음, proposal validation warning 없음.
- actions_executed: `2992`
- chunks_accepted: `149`
- hard_readback_streak: `0`
- readback: `--readback-stride 0` 이므로 per-action readback 은 수행하지 않음.
- clipped_features: `805`
- gripper_saturated_features: `648`
- joint4_saturated_features: `0`
- joint_limit_saturated_features: `3049`
- cleanup_errors: `[]`
- torque_disable_complete: `true`

## 시각 검증

eval frame 경로:

```text
/home/syhlabtop/openarm_folding_20260512/rollout_trial_20260518_131245_level2_messy_shirt_retry_no_readback_fix/live_session/eval_frames/
```

샘플: `obs_000000`, `obs_000030`, `obs_000060`, `obs_000090`, `obs_000120`.

판정:

- `obs_000000` 에서 셔츠는 테이블 중앙부에 뭉친 상태로 보인다.
- `obs_000030` 이후 base/right_wrist view 에서 양팔 접근과 셔츠 접촉이 확인된다.
- `obs_000060`~`obs_000120` 사이에 셔츠 위치와 형태 변화가 계속 보인다.
- 5개 obs 샘플 중 시작 이후 4개 샘플에서 가시적 접촉/폴딩 시도 동작이 관찰된다. 관찰 샘플 기준 80%다.
- 완성 fold 로 보기는 어렵다. 첫 목표였던 “120초 closed-loop가 막힘없이 흐르는지”는 충족했다.

## 이전 시도 메모

같은 날 직전 trial `rollout_trial_20260518_130413_level2_messy_shirt` 는 첫 chunk 수신 뒤
`ValueError('max() iterable argument is empty')` 로 중단됐다. 원인은
`--readback-stride 0` 에서 readback map 이 비어 있는데 max readback log 를 계산한 코드 버그였다.
수정 커밋: `20ec9a05 tools(rollout): handle no-readback execution logging`.

## 다음 권장

1. 같은 120s/180chunk 설정은 유지한다. 이번 실행은 runtime 막힘 해소 목적을 통과했다.
2. joint limit saturation 이 높으므로 다음 실행 전 events 에서 상위 saturation feature 를 집계하고,
   필요하면 arm/gripper delta cap 또는 시작 자세를 조정한다.
3. fold 품질 개선은 checkpoint 교체보다 먼저 scene 초기조건과 base/wrist view 에서 shirt 중심 위치를
   더 일관되게 맞추는 쪽을 우선한다.
