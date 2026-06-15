 패턴별 복구표입니다.

  공통 Preflight

  cd /home/syhlabtop/workspace/lerobot

  export STAMPED=KETI-IRRC/openarm_handover_v0_20260521_202117
  export STAMPED_LOCAL=/home/syhlabtop/.cache/huggingface/lerobot/${STAMPED}
  export OPENARM_MINI_RIGHT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA095468-if00
  export OPENARM_MINI_LEFT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA096282-if00
  export HF_HUB_OFFLINE=0
  export TRANSFORMERS_OFFLINE=0

  ip -br link show can0 can1
  readlink -f "$OPENARM_MINI_RIGHT"
  readlink -f "$OPENARM_MINI_LEFT"
  uv run python -c "import can, serial, scservo_sdk, pyrealsense2; print('imports ok')"

  저장 상태 확인

  uv run python -c "import json, pandas as pd; root='${STAMPED_LOCAL}'; d=json.load(open(root+'/meta/info.json')); print(d['total_episodes'], d['total_frames'],
  d.get('total_tasks')); print(pd.read_parquet(root+'/meta/tasks.parquet'))"

  1. CAN DOWN
  증상:

  can0 DOWN
  can1 DOWN

  복구:

  uv run lerobot-setup-can --mode=setup --interfaces=can0,can1
  ip -br link show can0 can1

  2. Mini leader 권한 없음
  증상:

  Permission denied: /dev/serial/by-id/...

  복구:

  sudo chmod a+rw "$(readlink -f "$OPENARM_MINI_RIGHT")" "$(readlink -f "$OPENARM_MINI_LEFT")"
  ls -l "$(readlink -f "$OPENARM_MINI_RIGHT")" "$(readlink -f "$OPENARM_MINI_LEFT")"

  영구 조치:

  sudo usermod -aG dialout syhlabtop
  # 로그아웃/로그인 또는 재부팅 후 적용
  id

  3. Mini leader가 녹화 중 사라짐
  증상:

  SerialException: write failed: [Errno 19] No such device

  복구:

  pkill -f lerobot-record

  # mini leader USB 전원/케이블 재연결 후
  readlink -f "$OPENARM_MINI_RIGHT"
  readlink -f "$OPENARM_MINI_LEFT"

  sudo chmod a+rw "$(readlink -f "$OPENARM_MINI_RIGHT")" "$(readlink -f "$OPENARM_MINI_LEFT")"

  그 뒤 저장된 개수 확인하고 부족분만 resume.

  4. Feetech Input Voltage Error
  증상:

  [RxPacketError] Input voltage error
  Failed to write 'Homing_Offset' on id_=7

  복구:

  pkill -f lerobot-record

  # mini leader 전원/USB 완전 분리, 10초 대기, 재연결
  sudo chmod a+rw "$(readlink -f "$OPENARM_MINI_RIGHT")" "$(readlink -f "$OPENARM_MINI_LEFT")"

  이건 카메라 문제가 아니라 mini leader servo/전원/USB 쪽 문제입니다.

  5. robot.id 누락으로 재 calibration prompt
  증상:

  Running calibration for bi_openarm_follower_left

  복구: record 명령에 반드시 추가:

  --robot.id=openarm_bimanual_follower

  6. RealSense latest frame too old
  증상:

  RealSenseCamera(230322273311) latest frame is too old: 502.5 ms

  복구:

  pkill -f lerobot-record
  # right_wrist D405 USB 재연결
  /home/syhlabtop/src/librealsense/build/Release/rs-enumerate-devices 2>&1 | egrep 'Serial Number|Failed'

  명령에는 카메라별 warmup_s: 3 유지. 반복되면 해당 세션은 부족분만 resume.

  7. RealSense No device connected / Viewer에도 안 보임
  증상:

  RuntimeError: No device connected
  Failed to open RealSenseCamera(230322273311)

  복구:

  pkill -f realsense-viewer
  pkill -f lerobot-record

  # right_wrist D405 물리 재연결
  lsusb | grep -i RealSense

  /home/syhlabtop/src/librealsense/build/Release/rs-enumerate-devices 2>&1 | egrep 'Failed|Name|Serial Number|Physical Port|Usb Type'

  Viewer는 이 경로로 실행:

  /home/syhlabtop/src/librealsense/build/Release/realsense-viewer

  8. RealSense set_xu / Resource temporarily unavailable
  증상:

  set_xu(ctrl=1) failed! Resource temporarily unavailable

  복구:

  pkill -f realsense-viewer
  pkill -f lerobot-record

  # 해당 D405 USB 재연결, 가능하면 다른 USB3 포트/전원 허브 사용
  /home/syhlabtop/src/librealsense/build/Release/rs-enumerate-devices

  정상 조건:

  315122270766
  230322273311
  213622075840

  세 serial이 모두 보여야 record 재개.

  9. Missing dependency
  증상:

  python-can not installed
  feetech-servo-sdk is required

  복구:

  uv sync --locked --extra core-scripts --extra openarms --extra feetech

  10. 경고지만 원인 아님
  아래는 단독으로는 실패 원인이 아닙니다.

  Relative goal position magnitude had to be clamped
  Packet drop: gripper ... Using last known state
  No files have been modified since last commit
  Waiting for image writer to terminate

11. 업로드/정리 후 다음 resume에서 mini leader 권한이 다시 660으로 돌아감

  증상:

  PermissionError: [Errno 13] Permission denied:
  '/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA095468-if00'
  ...
  teleop.connect()
  self.bus_right.connect()

  이전 No such device와 다릅니다.

  - No such device: 녹화 중 USB 장치가 사라짐
  - Permission denied: 장치는 존재하지만 현재 사용자가 열 권한 없음

  주로 mini leader가 재연결되면서 /dev/ttyACM*가 새로 만들어지고 권한이 다시 이렇게 바뀔 때 생깁니다:

  crw-rw---- root dialout /dev/ttyACM*

  복구 명령:

  export OPENARM_MINI_RIGHT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA095468-if00
  export OPENARM_MINI_LEFT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA096282-if00

  readlink -f "$OPENARM_MINI_RIGHT"
  readlink -f "$OPENARM_MINI_LEFT"

  sudo chmod a+rw "$(readlink -f "$OPENARM_MINI_RIGHT")" "$(readlink -f "$OPENARM_MINI_LEFT")"

  ls -l "$(readlink -f "$OPENARM_MINI_RIGHT")" "$(readlink -f "$OPENARM_MINI_LEFT")"

  정상 기대:

  crw-rw-rw- ... /dev/ttyACM*

  영구 조치가 반영됐는지 확인:

  id | grep dialout

  dialout이 안 나오면 아직 로그아웃/로그인 또는 재부팅 전이라 임시 chmod가 계속 필요합니다.

  그리고 이 로그 앞에 나온:

  No files have been modified since last commit

  은 원인 아닙니다. HF upload 단계에서 새 변경이 없어서 skip했다는 메시지이고, 실패 원인은 그 이후 teleop.connect()의 serial permission입니다.



  중단 키
  Ctrl-C보다 이걸 우선 사용:

  Left Arrow = 현재 episode 버리고 재녹화
  Esc        = 전체 clean stop


12. right_wrist RealSense stream freeze during recording

  증상:

  Recording episode N
  RealSenseCamera(230322273311) latest frame is too old: XXXX ms (max allowed: 500 ms)
  ...
  stop() cannot be called before start()
  terminate called without an active exception

  의미:

  right_wrist D405는 USB에 남아 있을 수 있지만, stream thread가 새 frame을 못 받음.
  현재 recording episode는 저장되지 않았을 가능성이 높음.

  복구:

  pkill -f lerobot-record
  pkill -f realsense-viewer

  # right_wrist D405 물리 재연결 권장
  # 10초 대기

  /home/syhlabtop/src/librealsense/build/Release/rs-enumerate-devices 2>&1 | egrep 'Failed|Name|Serial Number|Physical Port|Usb Type'

  uv run python -c "import pyrealsense2 as rs; ctx=rs.context(); print([(d.get_info(rs.camera_info.serial_number), d.get_info(rs.camera_info.name)) for d in
  ctx.query_devices()])"

  저장 개수 확인:

  uv run python -c "import json; root='/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117'; d=json.load(open(root+'/meta/info.json'));
  print(d['total_episodes'], d['total_frames'])"

  부족분만 resume:

  --dataset.num_episodes=<남은개수>




지금 해야 할 최소 복구:

pkill -f lerobot-record

  # OpenArm mini leader 전원/USB를 한번 완전히 뺐다 꽂기
  # 특히 left mini leader 쪽. 10초 정도 기다렸다가 다시 연결.

sudo chmod a+rw /dev/ttyACM0 /dev/ttyACM1
ls -l /dev/ttyACM0 /dev/ttyACM1







cd /home/syhlabtop/workspace/lerobot

  export HF_HUB_OFFLINE=0
  export TRANSFORMERS_OFFLINE=0
  export STAMPED=KETI-IRRC/openarm_handover_v0_20260521_202117
  export STAMPED_LOCAL=/home/syhlabtop/.cache/huggingface/lerobot/${STAMPED}
  export OPENARM_MINI_RIGHT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA095468-if00
  export OPENARM_MINI_LEFT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA096282-if00

  uv run lerobot-record \
    --resume=true \
    --display_data=false \
    --dataset.private=true \
    --dataset.repo_id="${STAMPED}" \
    --dataset.root="${STAMPED_LOCAL}" \
    --dataset.single_task="Pick the blue toothpaste, hand it over to the other arm, and place it at the target." \
    --dataset.num_episodes=14 \
    --dataset.episode_time_s=30 \
    --dataset.fps=30 \
    --dataset.reset_time_s=15 \
    --teleop.type=openarm_mini \
    --teleop.port_right="${OPENARM_MINI_RIGHT}" \
    --teleop.port_left="${OPENARM_MINI_LEFT}" \
    --teleop.id=mini_set1 \
    --robot.type=bi_openarm_follower \
    --robot.id=openarm_bimanual_follower \
    --robot.left_arm_config.port=can0 \
    --robot.left_arm_config.side=left \
    --robot.left_arm_config.max_relative_target=5 \
    --robot.right_arm_config.port=can1 \
    --robot.right_arm_config.side=right \
    --robot.right_arm_config.max_relative_target=5 \
    --robot.cameras='{ left_wrist: {type: intelrealsense, serial_number_or_name: "315122270766", width: 640, height: 480, fps: 30, warmup_s: 3}, right_wrist: {type:
  intelrealsense, serial_number_or_name: "230322273311", width: 640, height: 480, fps: 30, warmup_s: 3}, base: {type: intelrealsense, serial_number_or_name: "213622075840",
  width: 640, height: 480, fps: 30, warmup_s: 3} }'



