# Phase 3-1 — OpenArmFollower safety trace

작성일: 2026-05-19

머신: a6000 / `ketiserver` / `syh`
범위: 읽기 전용 코드 trace. 모션, 학습, 서빙 재기동, ckpt 변경 없음.

## 결론

`send_action()` 등가성 판정: **DIFFERENT**

OpenArm 단일 arm 의 `send_action()` 자체는 MIT batch command 구조를 사용하므로 archive guarded harness 와 일부 하위 write primitive 는 닮아 있다. 그러나 공식 `lerobot-rollout` 전체 경로는 `OpenArmFollower.connect()` 와 strategy teardown, wrapper, control loop 를 포함한다. 이 전체 runtime side effect 는 archive guarded harness 와 다르다.

핵심 차이:

- upstream `connect()` 는 `configure()`, `set_zero_position()`, `enable_torque()` 를 호출한다.
- `bi_openarm_follower.connect()` 는 left/right arm 각각의 `connect()` 를 호출하므로 side effect 가 양팔에 적용된다.
- rollout strategy 는 control loop 에서 `robot.send_action()` 을 호출하고, 기본 `return_to_initial_position=True` 에서는 teardown 중에도 보간된 `send_action()` 을 반복 호출할 수 있다.
- archive guarded harness 는 `DamiaoMotorsBus.connect(handshake=False)` + 명시 approval + 직접 guarded MIT batch 를 사용한 별도 path 였다.

## 1. 확인 파일

- `src/lerobot/robots/openarm_follower/openarm_follower.py`
- `src/lerobot/robots/openarm_follower/config_openarm_follower.py`
- `src/lerobot/robots/bi_openarm_follower/bi_openarm_follower.py`
- `src/lerobot/rollout/context.py`
- `src/lerobot/rollout/robot_wrapper.py`
- `src/lerobot/rollout/strategies/core.py`
- `src/lerobot/rollout/strategies/base.py`
- `docs/_archive/openarm_folding/syhlabtop_live_guarded_rollout.py` 및 Stage35-40 archive 기록

## 2. `OpenArmFollower` side effect trace

| 함수 | 확인된 동작 | actuator / persistent side effect |
|---|---|---|
| `connect(calibrate=True)` | CAN bus connect, 필요 시 calibration, camera connect, `configure()`, calibrated 상태면 `set_zero_position()`, 이후 `enable_torque()` | 있음. zero position write 및 torque enable 가능 |
| `calibrate()` | torque disable, 사용자 자세 입력, `set_zero_position()`, calibration range 생성, `write_calibration()`, calibration file save | 있음. motor calibration / zero 관련 persistent write 가능 |
| `configure()` | `with self.bus.torque_disabled(): self.bus.configure_motors()` | 있음. motor configuration write 가능 |
| `send_action(action, custom_kp=None, custom_kd=None)` | `.pos` target 추출, joint limit clipping, optional `Present_Position` read, MIT command tuple 생성, `_mit_control_batch(commands)` 호출 | 있음. actuator command write |
| `disconnect()` | `self.bus.disconnect(self.config.disable_torque_on_disconnect)`, camera disconnect | 있음. default 로 torque disable 가능 |

`OpenArmFollowerConfig` 기본값:

- `disable_torque_on_disconnect=True`
- `max_relative_target=None`
- `position_kp=[240, 240, 240, 240, 24, 31, 25, 25]`
- `position_kd=[5, 5, 3, 5, 0.3, 0.3, 0.3, 0.3]`
- default joint limits 는 좁은 safety range 이며, `side` 설정 또는 CLI override 로 바뀔 수 있음.

## 3. `bi_openarm_follower` side effect trace

`bi_openarm_follower.connect()` 는 다음 순서로 호출한다.

1. `self.left_arm.connect(calibrate)`
2. `self.right_arm.connect(calibrate)`

따라서 단일 arm `connect()` 의 `configure()`, `set_zero_position()`, `enable_torque()` side effect 가 양팔에 적용될 수 있다.

`bi_openarm_follower.send_action()` 은 입력 dict 를 `left_` / `right_` prefix 로 분리하고, 각 arm 의 `send_action()` 을 호출한 뒤 prefixed result 를 합친다. dataset feature order 는 right first, then left 로 정리되어 있다.

## 4. `lerobot-rollout` actuator path

공식 rollout context 는 다음 순서다.

1. policy local load
2. pre/postprocessor 준비
3. `robot = make_robot_from_config(cfg.robot)`
4. `robot.connect()`
5. `robot.get_observation()` 으로 initial position 저장
6. strategy run

runtime 중 action write path:

- strategy loop 가 observation 을 처리
- inference engine 에서 action tensor 반환
- action dict 로 변환
- `ThreadSafeRobot.send_action(processed)`
- underlying `robot.send_action(action)`
- OpenArm 의 경우 `_mit_control_batch(commands)`

teardown side effect:

- `RolloutConfig.return_to_initial_position=True` 가 기본값이다.
- strategy teardown 에서 initial position 으로 돌아가는 보간 action 을 여러 번 `robot.send_action(interp)` 로 보낼 수 있다.

## 5. Archive guarded harness 와 비교

archive guarded harness 의 핵심 운영 원칙:

- `OpenArmFollower.connect()` 미사용
- `DamiaoMotorsBus.connect(handshake=False)` 로 readback 또는 guarded write path 구성
- exact target table / approval phrase / operator approval 을 session artifact 로 기록
- 직접 MIT batch 는 한 session 의 승인된 target 에 한정
- `send_action()` / `lerobot-rollout` path 미사용

비교표:

| 동작 | upstream `send_action()` / rollout | archive harness | 일치? |
|---|---|---|---|
| connect side effect | `OpenArmFollower.connect()` 가 configure, zero, torque enable 가능 | `DamiaoMotorsBus.connect(handshake=False)` 중심 | 다름 |
| kp/kd 값 | `OpenArmFollowerConfig.position_kp/kd` 기본 또는 custom | Stage harness 에서 명시 command 구성 | 부분 일치 가능 |
| command 구조 | `(kp, kd, target_deg, 0.0, 0.0)` MIT batch | guarded MIT batch | 하위 primitive 는 유사 |
| target clipping | `joint_limits`, optional `max_relative_target` | artifact 별 limit / envelope 검증 | 다름 |
| motor write timing | strategy loop + optional interpolation + teardown return | 승인된 1회/제한 write 중심 | 다름 |
| torque assumption | `connect()` 가 torque enable 가능 | torque / motion approval 을 session 조건으로 분리 | 다름 |
| teardown motion | default return-to-initial interpolation 가능 | 승인 밖 추가 motion 없음 | 다름 |
| operator approval | code path 자체에는 없음 | artifact / approval phrase 중심 | 다름 |

판정: **DIFFERENT**

`send_action()` 내부 write primitive 만 보고 등가라고 볼 수 없다. 공식 rollout path 는 connect, loop, teardown side effect 를 포함하므로 Phase 3 에서는 별도 safety default 결정이 필요하다.

## 6. D-12 결정 입력

추천은 하지 않는다. 사용자가 선택해야 한다.

| 축 | upstream default 유지 | safe default 도입 |
|---|---|---|
| 기존 LeRobot 사용자 영향 | 가장 작음 | OpenArm 사용자 외 영향 범위 검토 필요 |
| OpenArm 첫 사용 안전성 | 사용자가 명시적으로 안전 옵션을 꺼야 함 | 기본적으로 위험 side effect 를 줄일 수 있음 |
| `lerobot-rollout` 호환 | upstream behavior 와 같음 | config / CLI / docs 업데이트 필요 |
| hidden motion risk | `connect()` / teardown / `send_action()` 경로를 사용자가 이해해야 함 | default 가 보수적이면 감소 |
| Phase 3 구현 부담 | 낮음 | OpenArm config flag 와 tests 필요 |

### 안전 플래그 명세 초안

Phase 3 에서 OpenArm 전용 config 로 검토할 flag:

- `configure_on_connect: bool`
  - `False` 일 때 `connect()` 에서 `configure()` 호출 생략.
- `set_zero_position_on_connect: bool`
  - `False` 일 때 calibrated 상태여도 `set_zero_position()` 생략.
- `enable_torque_on_connect: bool`
  - `False` 일 때 `connect()` 에서 `enable_torque()` 생략.
- `allow_send_action: bool`
  - `False` 일 때 `send_action()` 이 actuator write 전에 명시 오류로 중단.
- `return_to_initial_position`
  - 이미 rollout config 에 존재. OpenArm safety profile 에서는 default 또는 required setting 을 별도 결정 필요.

결정 필요:

- 위 flag 를 upstream-compatible opt-in 으로 둘지, OpenArm 계열에서 safe default 로 둘지.
- safe default 가 `openarm_follower` 단일 arm 과 `bi_openarm_follower` 양팔 모두에 적용되어야 하는지.
- `allow_send_action` 같은 hard gate 를 robot config 에 둘지, rollout strategy / adapter 쪽에 둘지.

## 7. 작업 중 변경 없음

- 모션 실행 없음
- 학습 실행 없음
- 서빙 재기동 없음
- ckpt 변경 없음
- `src/` 코드 패치 없음
