# Phase 3-1 — lerobot-rollout ↔ A6000 `/predict_live` 호환 검증

작성일: 2026-05-19

머신: a6000 / `ketiserver` / `syh`
범위: 읽기 전용 코드 trace. 모션, 학습, 서빙 재기동, ckpt 변경 없음.

## 결론

판정: **ADAPTABLE**

공식 `lerobot-rollout` 은 현재 두 가지 추론 경로가 확인된다.

- 기본 rollout 경로: syhlabtop 같은 실행 머신에서 policy 를 로컬 로드하고 `robot.connect()` 뒤 `robot.send_action()` 으로 직접 actuator write.
- `async_inference` 경로: gRPC + pickle 기반의 원격 policy server/client 구조이며, client 쪽 `RobotClient` 가 robot 을 직접 connect 하고 `send_action()` 을 호출.

현재 A6000 server 는 `POST /predict_live` HTTP JSON endpoint 이다. 입력 observation 과 출력 action chunk 의 의미는 맞출 수 있지만, wire protocol 과 request/response schema 가 다르므로 그대로 호환되지는 않는다. 얇은 adapter 한 곳이 필요하다.

`uv run lerobot-rollout --help` 는 help-only 로 실행했지만 optional `datasets` 미설치 때문에 entry import 단계에서 실패했다.

```text
ImportError: 'datasets' is required but not installed. Install it with: pip install 'lerobot[dataset]' (or uv pip install 'lerobot[dataset]')
```

이번 작업 범위는 문서 trace 이므로 dependency 설치는 하지 않았다.

## 1. 공식 `lerobot-rollout` 경로

확인 파일:

- `src/lerobot/scripts/lerobot_rollout.py`
- `src/lerobot/rollout/context.py`
- `src/lerobot/rollout/inference/rtc.py`
- `src/lerobot/async_inference/robot_client.py`
- `src/lerobot/async_inference/configs.py`
- `src/lerobot/policies/rtc/configuration_rtc.py`

### 1-A. entrypoint

`lerobot-rollout` 의 CLI entry 는 `src/lerobot/scripts/lerobot_rollout.py` 의 `rollout(cfg)` 이다.

실행 흐름:

1. `build_rollout_context(cfg, shutdown_event)`
2. `create_strategy(cfg.strategy)`
3. `strategy.setup(ctx)`
4. `strategy.run(ctx)`
5. `strategy.teardown(ctx)`

`build_rollout_context()` 는 policy 를 먼저 로드한 뒤 hardware 를 연결한다. policy path 오류는 robot connect 전에 실패하도록 설계되어 있지만, 정상 path 에서는 이후 `robot.connect()` 를 호출한다.

### 1-B. local rollout inference

`src/lerobot/rollout/context.py` 에서 policy 는 다음 형태로 로컬 materialization 된다.

- `policy_class.from_pretrained(policy_config.pretrained_path, config=policy_config)`
- `policy.to(cfg.device)`
- RTC 인 경우 `policy.config.rtc_config = cfg.inference.rtc`
- `policy.init_rtc_processor()` 가 있으면 호출

이후 `robot = make_robot_from_config(cfg.robot)` 와 `robot.connect()` 가 실행된다.

RTC inference 는 `src/lerobot/rollout/inference/rtc.py` 의 `RTCInferenceEngine` 이 담당한다. background thread 가 observation 을 받아 `policy.predict_action_chunk(preprocessed, inference_delay=delay, prev_chunk_left_over=prev_actions)` 를 로컬 호출하고, postprocessor 결과를 local action queue 에 넣는다.

### 1-C. async inference 경로

`src/lerobot/async_inference/robot_client.py` 의 `RobotClient` 는 gRPC 기반이다.

- `grpc.insecure_channel(server_address, ...)`
- `services_pb2_grpc.AsyncInferenceStub`
- observation 전송: `SendObservations`
- action 수신: `GetActions`
- payload: pickled `TimedObservation` / `TimedAction`
- robot side effect: `RobotClient.__init__()` 에서 `self.robot.connect()`, control loop 에서 `self.robot.send_action(...)`

이 경로도 현재 A6000 `/predict_live` 의 HTTP JSON schema 와 직접 호환되지 않는다.

## 2. 현 A6000 `/predict_live` schema

확인 파일:

- `audits/openarm_folding/a6000_live_policy_server.py`

### Request body

`POST /predict_live` 는 JSON body 를 받는다.

필수 또는 사실상 필수 필드:

- `send_action`: 반드시 `false`
- `state`: 16개 float, OpenArm 16D degrees
- `state_names`: 있으면 `ACTION_NAMES` 와 정확히 일치해야 함
- `images`: dict
  - `left_wrist`
  - `right_wrist`
  - `base`
  - 각 image entry 는 `encoding`, `data`, optional `sha256`
- `obs_seq`

선택 필드:

- `obs_timestamp`
- `obs_checksum`
- `task`
- `robot_type`
- `prev_leftover_abs_action_chunk`
- `inference_delay_steps`
- `execution_horizon`

### Response body

주요 응답 필드:

- `schema`: `openarm_folding_live_action_proposal_v1`
- `obs_seq`, `obs_timestamp`, `obs_checksum`, `image_sha256`
- `model_dir`, `model_id`, `checkpoint_id`
- `robot_config_id`, `action_normalization_id`
- `action_space_version`, `joint_order`, `action_units`
- `is_absolute_action`: `true`
- `action_shape`
- `predicted_abs_action`
- `predicted_abs_action_chunk`
- `delta_deg`, `max_abs_arm_delta_deg`, `rows`
- `rtc.enabled`
- `rtc.execution_horizon_default`
- `rtc.max_guidance_weight`
- `rtc.prefix_attention_schedule`
- `rtc.prev_leftover_supplied`
- `rtc.inference_delay_steps`
- `rtc.execution_horizon`
- `send_allowed`: `false`
- `motion_allowed`: `false`
- `actuator_commands_sent`: `false`
- `server_latency_ms`

### `/health`

`GET /health` 응답 핵심 필드:

- `status`
- `mode`
- `model_dir`
- `model_id`
- `checkpoint_id`
- `robot_config_id`
- `action_normalization_id`
- `rtc_enabled`
- `rtc_execution_horizon`
- `rtc_max_guidance_weight`
- `rtc_prefix_attention_schedule`
- `use_relative_actions`
- `action_space_version`
- `joint_order`
- `action_units`
- `device`
- `send_allowed`: `false`
- `motion_allowed`: `false`

## 3. Compatibility Matrix

| 항목 | `lerobot-rollout` 기대 | A6000 `/predict_live` 제공 | 호환? |
|---|---|---|---|
| entry method | local CLI process 또는 gRPC `async_inference` | HTTP `POST /predict_live` JSON | diff |
| policy forward 위치 | 기본 rollout 은 실행 머신 local; async path 는 gRPC server | A6000 server local GPU | adaptable |
| request body schema | local dict/tensor observation 또는 pickled `TimedObservation` | JSON: 16D state + 3 camera images + RTC leftover metadata | diff |
| response body schema | local action tensor 또는 pickled `TimedAction` list | JSON: absolute action chunk + metadata + motion flags | diff |
| RTC config 적용 위치 | local policy config / local RTC engine | server policy config + request metadata | adaptable |
| chunk shape | PI0/PI0.5 chunk action, 일반적으로 `[1, chunk, action_dim]` | `predicted_abs_action_chunk`, 현재 OpenArm `[1, 30, 16]` 계열 | match at semantic level |
| action representation | policy/postprocessor 결과를 `send_action()` 으로 전달 | server 에서 relative→absolute postprocess 후 absolute chunk 반환 | adaptable |
| robot write | `robot.send_action()` | 없음. `send_allowed=false`, `motion_allowed=false` | intentional diff |
| auth / streaming / timeout | 공식 HTTP JSON adapter 없음. gRPC path 는 별도 streaming 구조 | 단발 HTTP request/response | diff |

## 4. D-11 결정 입력 (사용자 사전 결정 반영)

사용자 결정 (2026-05-19):

- 정책 forward 는 무조건 A6000 GPU 고정.
- ckpt local materialization, 즉 syhlabtop 직접 inference 옵션은 사전 폐기.
- 잔여 옵션은 `server-side adapter` 와 `client-side adapter` 두 가지뿐이다.

따라서 아래 비교는 두 옵션만 다룬다. 추천은 하지 않는다.

| 축 | server-side adapter | client-side adapter |
|---|---|---|
| 변경 위치 | A6000 HTTP server 쪽에 `lerobot-rollout` 호환 endpoint 추가 | syhlabtop/rollout client 쪽에 A6000 `/predict_live` 호출 wrapper 추가 |
| policy forward 위치 | A6000 GPU 고정 | A6000 GPU 고정 |
| syhlabtop local ckpt materialization | 없음 | 없음 |
| 기존 A6000 `/predict_live` 보존 | 가능. endpoint 추가 방식이면 기존 path 유지 | 가능. server 변경 최소화 |
| 공식 rollout 수정 범위 | server 가 공식 client schema 를 맞추면 rollout 쪽 변경 감소 | rollout/robot client 쪽 adapter 필요 |
| 향후 다른 client 호환 | A6000 server 가 표준 endpoint 를 제공하면 유리 | 해당 client wrapper 에 종속 |
| a6000 운영 부담 | server schema 추가 및 테스트 필요 | server 유지, client 변환 책임 증가 |
| syhlabtop 안전 통제 | client 에서 motion gate 와 `send_action` 차단을 함께 다루기 쉬움 | client 쪽 책임이 명확함 |
| 실패 시 rollback | server endpoint 비활성/기존 server 재기동 | wrapper 미사용으로 rollback |

## 5. Dry-run / Mock 확인

검색:

```text
rg -n "mock|dry.run|dry_run|no.actuation|no_actuation|fake" src/lerobot/scripts/lerobot_rollout.py src/lerobot/robots
```

확인 결과:

- `src/lerobot/robots/utils.py` 에 `mock_robot` factory 분기는 존재한다.
- `lerobot-rollout` 에서 실제 OpenArm follower 를 연결하지 않고 같은 config path 를 dry-run 하는 명시적 `dry-run`, `no-actuation`, `no_actuation` flag 는 확인되지 않았다.
- `uv run lerobot-rollout --help` 는 optional `datasets` 미설치로 실패하여 CLI help 에서 추가 dry-run flag 존재 여부를 확정하지 못했다.

판정: **부분**

Phase 3-3 에서 실제 `lerobot-rollout` OpenArm path 를 쓰려면 no-actuation/dry-run 또는 mock binding 의 명시적 검증이 별도 필요하다.

## 6. 작업 중 변경 없음

- 모션 실행 없음
- 학습 실행 없음
- 서빙 재기동 없음
- ckpt 변경 없음
- `src/` 코드 패치 없음
