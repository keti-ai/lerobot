# Open Arms Mini 리더 작업 How-To

날짜: 2026-05-14
대상: Open Arms Mini 양팔 리더 텔레오퍼레이터

## 0. 현재 상태

출력은 완료된 것으로 본다.

완성 페어 기준 필수 출력물:

| 부품 | 수량 |
| --- | ---: |
| `J1 v5.stl` | 2 |
| `J2 v2.stl` | 2 |
| `J3 v2.stl` | 2 |
| `J4 v3.stl` | 2 |
| `J5 v4.stl` | 2 |
| `J6 v6.stl` | 2 |
| `J7 v4.stl` | 2 |
| `J1_holder v1.stl` | 2 |
| `J2_holder v1.stl` | 2 |
| `J4_holder v1.stl` | 2 |
| `J7_holder v1.stl` | 2 |
| `J6 holder with strap v4.stl` | 2 |
| `J Handle v12.stl` | 2 |
| `J8 L v4.stl` | 1 |
| `J8 R v10.stl` | 1 |
| `J8 holder L v2.stl` | 1 |
| `J8 holder R v6.stl` | 1 |
| `J trigger L v2.stl` | 1 |
| `J trigger R v2.stl` | 1 |
| `WaveShare_Mounting_Plate_SO101 v1.stl` | 기존 출력품 사용 |
| `arducam_holder v6.stl` | 2, optional |

## 1. 후가공

먼저 모든 부품을 조립 전 상태로 정리한다.

- 서포트 제거.
- 나사 구멍 안쪽 찌꺼기 제거.
- 모터가 들어가는 사각 포켓의 실밥, 돌기 제거.
- `J6 holder with strap`의 스트랩 통과면을 손으로 만져서 날카로운 부분 제거.
- `J Handle`의 손 닿는 면 support scar 제거.
- `J8` gripper와 trigger는 움직이는 면을 특히 깨끗하게 정리.

중지 조건:

- 모터 삽입 시 부품이 벌어지거나 휘면 억지로 넣지 않는다.
- M2/M3 나사 체결 중 보스가 하얗게 변하면 멈춘다.
- gripper trigger가 손으로 움직였을 때 걸리면 조립 전에 다시 다듬는다.

## 2. 모터 준비 원칙

Mini 리더는 SO-ARM100처럼 리더 모터 기어를 제거하지 않는다.

- 기어박스 열지 않기.
- 기어 제거하지 않기.
- 토크 테스트를 느슨한 모터 상태에서 하지 않기.
- ID 설정 중에는 한 번에 모터 하나만 보드에 연결.

현재 혼합 모터 배치:

| Side | ID 1 | ID 2 | ID 3 | ID 4 | ID 5 | ID 6 | ID 7 | ID 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Right | C018 | C044 | C044 | C001 | C046 | C046 | C046 | C018 |
| Left | C018 | C044 | C044 | C001 | C046 | C046 | C046 | C018 |

라벨:

- Right: `R1-C018`, `R2-C044`, `R3-C044`, `R4-C001`, `R5-C046`, `R6-C046`, `R7-C046`, `R8-C018`
- Left: `L1-C018`, `L2-C044`, `L3-C044`, `L4-C001`, `L5-C046`, `L6-C046`, `L7-C046`, `L8-C018`

## 3. 모터 ID 설정

포트 확인:

```bash
uv run lerobot-find-port
```

빠른 확인:

```bash
ls -l /dev/serial/by-id/
```

ID 설정 명령 예시:

```bash
uv run lerobot-setup-motors \
  --teleop.type=openarm_mini \
  --teleop.port_right=/dev/ttyUSB0 \
  --teleop.port_left=/dev/ttyUSB0
```

`/dev/ttyUSB0`는 실제 포트로 바꾼다. 한 개 보드로 순차 세팅하면 `port_right`와 `port_left`를 같은 포트로 줘도 된다.

프롬프트 순서와 연결할 모터:

| 순서 | 프롬프트 | 연결 모터 | 설정 후 라벨 |
| ---: | --- | --- | --- |
| 1 | RIGHT `gripper` | C018 | `R8-C018` |
| 2 | RIGHT `joint_7` | C046 | `R7-C046` |
| 3 | RIGHT `joint_6` | C046 | `R6-C046` |
| 4 | RIGHT `joint_5` | C046 | `R5-C046` |
| 5 | RIGHT `joint_4` | C001 | `R4-C001` |
| 6 | RIGHT `joint_3` | C044 | `R3-C044` |
| 7 | RIGHT `joint_2` | C044 | `R2-C044` |
| 8 | RIGHT `joint_1` | C018 | `R1-C018` |
| 9 | LEFT `gripper` | C018 | `L8-C018` |
| 10 | LEFT `joint_7` | C046 | `L7-C046` |
| 11 | LEFT `joint_6` | C046 | `L6-C046` |
| 12 | LEFT `joint_5` | C046 | `L5-C046` |
| 13 | LEFT `joint_4` | C001 | `L4-C001` |
| 14 | LEFT `joint_3` | C044 | `L3-C044` |
| 15 | LEFT `joint_2` | C044 | `L2-C044` |
| 16 | LEFT `joint_1` | C018 | `L1-C018` |

## 4. 조립 순서

각 팔은 같은 순서로 조립한다. 먼저 오른팔 하나를 완성하고 같은 방식으로 왼팔을 진행하면 실수가 적다.

1. `J1`: ID 1 모터 삽입, M2x6으로 고정. `J1_holder` 장착. horn 장착 후 M3x6 고정.
2. `J2`: ID 2 모터 삽입, M2x6 고정. horn 장착. `J2`를 `J1` 쪽과 연결.
3. `J3`: ID 3 모터 삽입, M2x6 고정. horn 장착. `J3`를 `J2`와 연결.
4. `J4`: `J4_holder`를 `J3` 위로 넣고 ID 4 모터 삽입. M2x6 고정. horn 장착.
5. `J5`: ID 5 모터 삽입, M2x6 고정. horn 하나 장착. `J5`를 ID 4 모터 쪽에 연결.
6. `J6`: `J6`를 ID 5 horn에 연결. ID 6 모터 삽입, M2x6 고정. horn 장착.
7. `J7`: `J7_holder`로 ID 6 쪽과 연결. ID 7 모터 삽입, M2x6 고정.
8. Gripper: ID 8 모터를 `J8 holder L/R`에 넣고 `J8 L/R` claw와 `J trigger L/R` 장착.
9. Handle/strap: `J Handle`과 `J6 holder with strap` 장착. 벨크로 스트랩을 통과시킨다.
10. Controller: WaveShare 보드를 마운트에 고정하고, 모터를 ID 1 -> 8 순서로 daisy-chain.

조립 중 주의:

- horn 나사를 처음부터 세게 조이지 말고 위치 확인 후 최종 조임.
- 케이블이 관절 회전부에 감기지 않게 여유를 둔다.
- 좌우 팔의 같은 ID는 같은 variant인지 다시 확인.
- `joint_6`과 `joint_7`은 Mini 코드에서 follower 쪽과 매핑이 바뀌므로, 물리 조립은 README의 Mini 순서 그대로 따른다.

## 5. ID 후 버스 확인

오른팔부터 8개를 daisy-chain한 뒤 위치값이 읽히는지 확인한다.

```bash
uv run python - <<'PY'
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

port = "/dev/ttyUSB0"
motors = {f"joint_{i}": Motor(i, "sts3215", MotorNormMode.DEGREES) for i in range(1, 8)}
motors["gripper"] = Motor(8, "sts3215", MotorNormMode.RANGE_0_100)
bus = FeetechMotorsBus(port=port, motors=motors)
bus.connect()
print(bus.sync_read("Present_Position", normalize=False))
bus.disconnect()
PY
```

왼팔도 포트만 바꿔서 반복한다.

확인 기준:

- 1-8 ID가 모두 응답해야 한다.
- 특정 ID가 안 읽히면 케이블 방향, daisy-chain 순서, ID 중복을 먼저 확인.
- 값이 읽히면 아직 torque를 걸지 말고 다음 단계로 간다.

## 6. 캘리브레이션

양팔 보드를 각각 연결한 상태에서 실행:

```bash
uv run lerobot-calibrate \
  --teleop.type=openarm_mini \
  --teleop.port_right=/dev/ttyUSB0 \
  --teleop.port_left=/dev/ttyUSB1 \
  --teleop.id=openarm_mini_pair
```

실제 포트는 환경에 맞게 바꾼다.

캘리브레이션에서 하는 일:

- torque disable.
- 모든 모터 `Phase=12`.
- position mode 설정.
- 팔을 아래로 자연스럽게 늘어뜨린 상태를 zero로 기록.
- gripper closed/open 범위 기록.

캘리브레이션 자세:

- 팔은 아래로 곧게 늘어뜨린다.
- gripper는 먼저 완전히 닫은 상태.
- 프롬프트가 gripper open을 요구하면 완전히 연다.
- 좌/우를 헷갈리지 말고 한 팔씩 진행한다.

## 7. 텔레오퍼레이션 전 최종 점검

- 손으로 움직일 때 케이블이 당기지 않는지 확인.
- 손잡이와 스트랩이 손목에 안정적으로 고정되는지 확인.
- gripper trigger가 걸리지 않고 돌아오는지 확인.
- C018/C001이 들어간 축은 C046보다 덜 부드러울 수 있다. 좌우 같은 축에 같은 variant를 넣었으므로 동작 대칭성만 우선 본다.
- follower와 연결하기 전에는 Mini 단독 위치 읽기부터 확인한다.

## 8. 문제 대응

모터가 하나만 안 잡힘:

- 해당 ID 라벨 확인.
- 케이블 방향 확인.
- 단독 연결해서 다시 `lerobot-setup-motors`로 ID 재설정.

관절이 뻑뻑함:

- torque가 꺼져 있는지 확인.
- horn이 비틀려 조립됐는지 확인.
- printed part와 모터 케이스가 간섭하는지 확인.
- 나사를 조금 풀었을 때 부드러워지는지 확인.

gripper가 안 움직임:

- `J8 holder L/R`, `J8 L/R`, trigger 방향 확인.
- support scar 제거.
- horn 체결 각도 확인.

캘리브레이션을 다시 하고 싶음:

```bash
uv run lerobot-calibrate \
  --teleop.type=openarm_mini \
  --teleop.port_right=/dev/ttyUSB0 \
  --teleop.port_left=/dev/ttyUSB1 \
  --teleop.id=openarm_mini_pair
```

기존 캘리브레이션 사용 여부 프롬프트에서 `c`를 입력하면 새로 캘리브레이션한다.

## 9. 레퍼런스

확인일: 2026-05-14

공식/원본 문서:

- Open Arms Mini GitHub: https://github.com/pkooij/open-arms-mini
  - Mini가 7DOF+gripper 리더 텔레오퍼레이터이고 `openarm_mini`로 LeRobot에 통합된다는 설명.
  - 3D printing 수량표, motor ID 표, 조립 순서, wrist 6/7 swap note 기준.
- Open Arms Mini BOM: https://github.com/pkooij/open-arms-mini/blob/main/BOM.md
  - 팔당 STS3215-C046 8개, Waveshare board, 7.5 V power supply, M2/M3 screw, 3-pin cable, wrist strap 기준.
- LeRobot OpenArm 문서: https://huggingface.co/docs/lerobot/main/openarm
  - OpenArm follower/leader, bimanual teleoperation 쪽 상위 문맥.
- LeRobot `lerobot-setup-motors` 문서: https://huggingface-lerobot.mintlify.app/api/scripts/setup-motors
  - `openarm_mini` 지원, motor ID assignment, one-by-one setup/troubleshooting 기준.
- SO-100 문서: https://huggingface.co/docs/lerobot/so100
  - SO100 leader는 기어 제거 지시가 있는 별도 케이스. Mini에는 이 절차를 적용하지 않는 비교 근거.
- SO-101 문서: https://huggingface.co/docs/lerobot/so101
  - SO101 leader는 기어 제거 대신 서로 다른 기어비 모터를 쓰는 설계라는 비교 근거.

로컬 소스/작업 문서:

- Mini 원본 로컬 클론:
  - `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini/README.md`
  - `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini/BOM.md`
- LeRobot Mini 구현:
  - `/home/syhlabtop/workspace/lerobot/src/lerobot/teleoperators/openarm_mini/openarm_mini.py`
  - `/home/syhlabtop/workspace/lerobot/src/lerobot/teleoperators/openarm_mini/config_openarm_mini.py`
- 출력/모터 작업 기록:
  - `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/mini_next_print_queue_2026-05-13.md`
  - `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/sts3215_parallel_work_2026-05-12.md`
  - `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/sts3215_inventory_assignment_2026-05-12.md`
