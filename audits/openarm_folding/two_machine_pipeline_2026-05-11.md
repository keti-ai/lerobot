# OpenArm Folding Two-Machine Pipeline

Date prepared: 2026-05-10
Execution date: 2026-05-11
Scope: `syhlabtop` + A6000 server

## 목적

이 문서는 두 기기 기준 전체 작업 파이프라인을 시간순으로 정리한다.

각 작업은 반드시 아래 중 하나의 실행 기기를 명시한다.

| 기기 표기 | 의미 |
| --- | --- |
| `BOTH` | `syhlabtop`과 A6000 서버에서 모두 수행 |
| `A6000` | A6000 서버에서만 수행 |
| `syhlabtop` | 로봇 작업용 PC에서만 수행 |
| `OPERATOR` | 사람이 물리적으로 확인 |
| `SAFETY` | 안전 담당자가 확인 |

2026-05-11 목표는 자율 folding이 아니다. 목표는 no-motion/shadow readiness다.

## 전체 원칙

1. `syhlabtop`만 로봇 IO 권한을 가진다.
2. A6000은 모델 로드, offline inference, action proposal만 담당한다.
3. A6000 output은 actuator command가 아니다.
4. 첫 테스트에서는 policy output을 robot `send_action()`으로 보내지 않는다.
5. `lerobot-rollout`, `lerobot-record`, `lerobot-replay`는 첫 액션으로 실행하지 않는다.
6. motion gate는 이 문서의 마지막 단계이며, 기본 목표가 아니다.

## 시간순 파이프라인

### 0. 작업 시작 선언

| 순서 | 실행 기기 | 작업 | 산출물 | 다음 단계 조건 |
| ---: | --- | --- | --- | --- |
| 0.1 | OPERATOR | 오늘 목표를 "no-motion/shadow readiness"로 선언 | 구두 확인 또는 작업 로그 첫 줄 | 모두 동의 |
| 0.2 | SAFETY | E-stop, 전원 차단 위치, 물리 workspace 확인 | safety 확인 메모 | 불명확하면 중단 |

### 1. Repo Preflight

| 순서 | 실행 기기 | 작업 | 명령/확인 | 산출물 |
| ---: | --- | --- | --- | --- |
| 1.1 | A6000 | repo 위치 확인 | `cd /home/syh/workspace/lerobot` | 현재 경로 확인 |
| 1.1b | syhlabtop | repo 위치 확인 | `cd /home/syhlabtop/workspace/lerobot` | 현재 경로 확인 |
| 1.2 | BOTH | branch 확인 | `git branch --show-current` | `audit/openarm-folding-baseline` |
| 1.3 | BOTH | worktree 확인 | `git status --short --branch` | 예상 외 변경 없음 |
| 1.4 | A6000 | repo root 확인 | `git rev-parse --show-toplevel` | `/home/syh/workspace/lerobot` |
| 1.4b | syhlabtop | repo root 확인 | `git rev-parse --show-toplevel` | `/home/syhlabtop/workspace/lerobot` |

기록 파일:

```text
A6000:    /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/2026-05-11_preflight_a6000.md
syhlabtop:<syhlabtop-work-root>/audits/2026-05-11_preflight_syhlabtop.md
```

Gate 1:

- 두 기기 모두 의도한 branch와 repo root가 확인되어야 한다.
- 예상 외 source 변경이 있으면 변경 내용을 먼저 기록한다.

### 2. 공유 기준 문서 확인

| 순서 | 실행 기기 | 작업 | 확인 파일 | 다음 단계 조건 |
| ---: | --- | --- | --- | --- |
| 2.1 | BOTH | shared baseline 읽기 | `audits/openarm_folding/shared_baseline.md` | body/camera/processor contract 이해 |
| 2.2 | BOTH | robot test spec 읽기 | `audits/openarm_folding/robot_test_work_spec_2026-05-11.md` | 금지 작업 이해 |
| 2.3 | BOTH | 본 pipeline 읽기 | `audits/openarm_folding/two_machine_pipeline_2026-05-11.md` | 기기별 작업 분리 이해 |

Gate 2:

- `send_action()` 금지, split-host live inference 금지, no-motion 목표를 모두 확인해야 한다.

### 3. A6000 모델 asset 준비

| 순서 | 실행 기기 | 작업 | 명령/확인 | 산출물 |
| ---: | --- | --- | --- | --- |
| 3.1 | A6000 | 모델 저장 디렉터리 생성 | `mkdir -p /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest` | 디렉터리 |
| 3.2 | A6000 | 허용된 model/config asset만 다운로드 | 아래 명령 | local model dir |
| 3.3 | A6000 | 파일 목록 확인 | `find /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest -maxdepth 1 -type f -printf "%f %s\n" \| sort` | asset 목록 |

허용 다운로드 명령:

```bash
huggingface-cli download lerobot/folding_latest \
  --include "model.safetensors" \
  --include "config.json" \
  --include "train_config.json" \
  --include "policy_preprocessor.json" \
  --include "policy_postprocessor.json" \
  --include "policy_preprocessor_step_3_normalizer_processor.safetensors" \
  --include "policy_postprocessor_step_0_unnormalizer_processor.safetensors" \
  --local-dir /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/models/folding_latest
```

금지:

- full dataset download
- video shard download
- training

기록 파일:

```text
A6000: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/2026-05-11_policy_asset_probe.md
```

Gate 3:

- `model.safetensors`와 processor safetensors가 있어야 한다.
- full dataset/video shard가 다운로드되지 않아야 한다.

### 4. A6000 offline policy load

| 순서 | 실행 기기 | 작업 | 확인 항목 | 산출물 |
| ---: | --- | --- | --- | --- |
| 4.1 | A6000 | robot 없이 policy config load | `type=pi05` | load log |
| 4.2 | A6000 | processor config 확인 | relative enabled, gripper excluded | processor log |
| 4.3 | A6000 | action feature order 확인 | 16개 exact order | action contract log |
| 4.4 | A6000 | CUDA/device 확인 | A6000 CUDA 사용 가능 | device log |

확인해야 할 action order:

```text
0  right_joint_1.pos
1  right_joint_2.pos
2  right_joint_3.pos
3  right_joint_4.pos
4  right_joint_5.pos
5  right_joint_6.pos
6  right_joint_7.pos
7  right_gripper.pos
8  left_joint_1.pos
9  left_joint_2.pos
10 left_joint_3.pos
11 left_joint_4.pos
12 left_joint_5.pos
13 left_joint_6.pos
14 left_joint_7.pos
15 left_gripper.pos
```

금지:

- `OpenArmFollower` instantiate
- `BiOpenArmFollower` instantiate
- robot connect
- robot action send

기록 파일:

```text
A6000: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/2026-05-11_policy_load_probe.md
```

Gate 4:

- policy load와 action contract가 통과해야 한다.

### 5. syhlabtop 카메라 discovery

| 순서 | 실행 기기 | 작업 | 명령/확인 | 산출물 |
| ---: | --- | --- | --- | --- |
| 5.1 | syhlabtop | OpenCV camera discovery | 아래 명령 | probe images |
| 5.2 | syhlabtop | RealSense 사용 시 discovery | 아래 명령 | probe images |
| 5.3 | OPERATOR | 각 이미지의 실제 물리 위치 확인 | 눈으로 확인 | camera map |
| 5.4 | syhlabtop | 정책 key로 mapping 문서화 | `left_wrist`, `right_wrist`, `base` | camera map md |

OpenCV:

```bash
cd /home/syhlabtop/workspace/lerobot
uv run lerobot-find-cameras opencv \
  --output-dir <syhlabtop-work-root>/camera_maps/2026-05-11_opencv_probe \
  --record-time-s 3
```

RealSense:

```bash
cd /home/syhlabtop/workspace/lerobot
uv run lerobot-find-cameras realsense \
  --output-dir <syhlabtop-work-root>/camera_maps/2026-05-11_realsense_probe \
  --record-time-s 3
```

필수 camera map:

| Policy key | syhlabtop device | Target resolution | 물리 위치 | 방향 확인 |
| --- | --- | --- | --- | --- |
| `left_wrist` | TBD | `1280x720` | left wrist | TBD |
| `right_wrist` | TBD | `1280x720` | right wrist | TBD |
| `base` | TBD | `640x480` | base view | TBD |

기록 파일:

```text
syhlabtop: <syhlabtop-work-root>/camera_maps/2026-05-11_camera_probe.md
```

Gate 5:

- 세 camera key가 모두 실제 물리 view와 연결되어야 한다.
- 좌우 wrist가 뒤바뀌었거나 orientation이 불명확하면 중단한다.

### 6. syhlabtop CAN, side, calibration 확인

| 순서 | 실행 기기 | 작업 | 확인 항목 | 산출물 |
| ---: | --- | --- | --- | --- |
| 6.1 | syhlabtop | CAN interface 식별 | left arm CAN, right arm CAN | CAN map |
| 6.2 | syhlabtop | side config 결정 | left는 `side=left`, right는 `side=right` | config snippet |
| 6.3 | syhlabtop | calibration ID 확인 | bimanual follower ID | calibration log |
| 6.4 | OPERATOR | gripper zero convention 확인 | closed = zero | gripper note |
| 6.5 | SAFETY | power/E-stop 확인 | 즉시 차단 가능 | safety signoff |

주의:

- 문서 예시의 `can0`/`can1` 순서는 신뢰하지 않는다.
- 실제 `syhlabtop` 배선과 장치 인식 결과를 기준으로 한다.

결정될 config 형태:

```bash
--robot.type=bi_openarm_follower \
--robot.left_arm_config.port=<LEFT_CAN> \
--robot.left_arm_config.side=left \
--robot.right_arm_config.port=<RIGHT_CAN> \
--robot.right_arm_config.side=right \
--robot.id=syhlabtop_openarm_folding_20260511
```

기록 파일:

```text
syhlabtop: <syhlabtop-work-root>/hardware/openarm/2026-05-11_can_calibration_probe.md
```

Gate 6:

- left/right CAN mapping이 명확해야 한다.
- calibration ID와 gripper zero convention이 기록되어야 한다.

### 7. no-send shadow 방식 선택

| 순서 | 실행 기기 | 작업 | 선택지 | 결과 |
| ---: | --- | --- | --- | --- |
| 7.1 | BOTH | 오늘 사용할 shadow 방식 결정 | Path A 또는 B | architecture decision |
| 7.2 | BOTH | 금지 방식 재확인 | Path C, D 금지 | stop condition |

선택지:

| Path | 실행 기기 | 설명 | 2026-05-11 권장 |
| --- | --- | --- | --- |
| A | A6000 + syhlabtop 분리 | A6000은 offline policy만, syhlabtop은 hardware mapping만 | Yes |
| B | syhlabtop snapshot + A6000 offline action | syhlabtop이 observation snapshot 저장, A6000이 action 계산, send 없음 | Yes, no-send script 검토 후 |
| C | syhlabtop live IO + A6000 live inference | remote inference bridge 필요 | No |
| D | syhlabtop live `lerobot-rollout` | policy action이 send될 수 있음 | No |

기록 파일:

```text
BOTH: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/2026-05-11_shadow_architecture_decision.md
```

Gate 7:

- Path A 또는 Path B만 허용한다.
- Path B는 snapshot capture와 action computation이 `send_action()`에 닿지 않는다는 리뷰가 필요하다.

### 8. syhlabtop observation snapshot, Path B 선택 시에만

| 순서 | 실행 기기 | 작업 | 확인 항목 | 산출물 |
| ---: | --- | --- | --- | --- |
| 8.1 | syhlabtop | 카메라 frame snapshot 저장 | 3 camera frames | image files |
| 8.2 | syhlabtop | 현재 `.pos` state 16개 저장 | exact order | state json/csv |
| 8.3 | syhlabtop | snapshot bundle 생성 | images + state + timestamp | bundle dir |
| 8.4 | syhlabtop | bundle을 A6000으로 전달 | rsync/scp/manual | transferred bundle |

필수 bundle 구조:

```text
snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

`state_16.csv` 순서:

```text
right_joint_1.pos,...,right_gripper.pos,left_joint_1.pos,...,left_gripper.pos
```

금지:

- policy action send
- autonomous rollout
- replay

기록 파일:

```text
syhlabtop: <syhlabtop-work-root>/shadow_snapshots/2026-05-11_snapshot_log.md
```

Gate 8:

- snapshot에 3 camera와 16 state가 모두 있어야 한다.
- timestamp와 camera mapping이 기록되어야 한다.

### 9. A6000 shadow action 생성, Path B 선택 시에만

| 순서 | 실행 기기 | 작업 | 확인 항목 | 산출물 |
| ---: | --- | --- | --- | --- |
| 9.1 | A6000 | syhlabtop snapshot load | 3 images + 16 state | load log |
| 9.2 | A6000 | policy preprocess 실행 | relative cache 정상 | preprocess log |
| 9.3 | A6000 | PI05 forward 실행 | action chunk 생성 | raw action tensor |
| 9.4 | A6000 | postprocess 실행 | absolute degree action | action csv |
| 9.5 | A6000 | action review table 생성 | finite, order, limits | review csv |

필수 review columns:

```text
timestamp,obs_id,action_id,key,current_deg,proposed_deg,clamped_deg,delta_deg,limit_min,limit_max,send_allowed
```

Gate 9:

- `send_allowed=false`가 모든 row에 있어야 한다.
- action length가 16이 아니면 중단한다.
- gripper가 absolute degree인지 확인한다.

### 10. syhlabtop action review 수신

| 순서 | 실행 기기 | 작업 | 확인 항목 | 산출물 |
| ---: | --- | --- | --- | --- |
| 10.1 | syhlabtop | A6000 action review 수신 | csv/md | local copy |
| 10.2 | OPERATOR | current vs proposed 값 검토 | joint별 delta | review note |
| 10.3 | SAFETY | motion 금지 상태 확인 | send 없음 | signoff |

기록 파일:

```text
syhlabtop: <syhlabtop-work-root>/shadow_reviews/2026-05-11_shadow_action_review_received.md
```

Gate 10:

- action은 검토만 한다.
- robot으로 전송하지 않는다.

### 11. 하루 종료 정리

| 순서 | 실행 기기 | 작업 | 산출물 |
| ---: | --- | --- | --- |
| 11.1 | BOTH | 결과 요약 작성 | summary md |
| 11.2 | A6000 | policy load/inference log 정리 | `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/` |
| 11.3 | syhlabtop | camera/CAN/snapshot log 정리 | `<syhlabtop-work-root>/` |
| 11.4 | BOTH | 다음 blocker 정리 | follow-up list |

최소 종료 산출물:

```text
2026-05-11_preflight_a6000.md
2026-05-11_preflight_syhlabtop.md
2026-05-11_policy_asset_probe.md
2026-05-11_policy_load_probe.md
2026-05-11_camera_probe.md
2026-05-11_can_calibration_probe.md
2026-05-11_shadow_architecture_decision.md
```

Path B를 했다면 추가:

```text
2026-05-11_snapshot_log.md
2026-05-11_shadow_action_review.csv
2026-05-11_shadow_action_review_received.md
```

## 병렬 가능 작업

아래 작업은 서로 독립적이므로 동시에 진행 가능하다.

| A6000 작업 | syhlabtop 작업 |
| --- | --- |
| Phase 3 model asset download | Phase 5 camera discovery |
| Phase 4 offline policy load | Phase 6 CAN/calibration documentation |

아래 작업은 순서 의존성이 있다.

| 먼저 해야 할 작업 | 이후 작업 |
| --- | --- |
| camera map 확정 | observation snapshot |
| CAN/state order 확정 | state_16.csv 작성 |
| policy load 통과 | shadow action 생성 |
| no-send 방식 결정 | snapshot/action review |

## 절대 금지 명령, 첫 테스트 기준

```bash
uv run lerobot-rollout ...
uv run lerobot-record ...
uv run lerobot-replay ...
```

이유:

- hardware connect와 action send path에 닿을 수 있다.
- `folding_latest`는 relative action policy라 sync rollout이 맞지 않는다.
- current RTC는 split-host remote inference가 아니다.

## Motion Gate는 별도 승인 필요

motion test는 이 pipeline의 기본 목표가 아니다.

motion을 하려면 다음이 먼저 있어야 한다.

1. `syhlabtop` no-send/live shadow implementation 리뷰
2. action clamp
3. per-joint delta/rate limit
4. stale action rejection
5. heartbeat timeout
6. action-order assertion
7. E-stop 확인
8. operator + safety observer 동시 확인
9. explicit approval before `send_action()`
