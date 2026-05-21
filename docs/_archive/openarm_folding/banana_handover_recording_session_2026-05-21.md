# Banana Handover Recording Session - 2026-05-21

## Summary

2026-05-21 syhlabtop 에서 `openarm_mini` 양팔 teleop 과 `bi_openarm_follower`
양팔 follower 로 banana handover dataset 을 수집했다. 최종 dataset 은 private HF repo
`KETI-IRRC/openarm_handover_v0_20260521_202117` 이며, local root 는 다음이다.

```text
/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117
```

최종 `meta/info.json` 기준:

```text
codebase_version: v3.0
robot_type: bi_openarm_follower
fps: 30
total_episodes: 20
total_frames: 17,944
splits.train: 0:20
action/state: 16D, degrees
video: left_wrist, right_wrist, base, 640x480 RGB AV1, pyav
```

Task string:

```text
Pick the banana, hand it over to the other arm, and place it at the target.
```

## Hardware Mapping

OpenArm mini stable serial paths:

```bash
export OPENARM_MINI_LEFT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA096282-if00
export OPENARM_MINI_RIGHT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA095468-if00
readlink -f "$OPENARM_MINI_LEFT"   # /dev/ttyACM0 at session time
readlink -f "$OPENARM_MINI_RIGHT"  # /dev/ttyACM1 at session time
```

Follower CAN mapping:

```text
openarm_left: can0
openarm_right: can1
```

RealSense cameras used in this dataset:

```text
left_wrist:  D405 315122270766
right_wrist: D405 230322273311
base:        D435I 213622075840
```

An extra D415 `211622062255` was visible in the environment but was not used by this
dataset command.

Mini calibration was saved before recording:

```text
/home/syhlabtop/.cache/huggingface/lerobot/calibration/teleoperators/openarm_mini/mini_set1.json
```

## Environment Fixes

The shell assignment form below is documentation only and is not valid bash:

```text
openarm_mini_left = /dev/serial/by-id/...
```

Use `export NAME=value` without spaces. The working session used `.bashrc` variables
`OPENARM_MINI_LEFT` and `OPENARM_MINI_RIGHT`.

The first serial permission failure was resolved by the user already being in
`dialout` and by opening a new shell. At the working point:

```text
/dev/ttyACM0 root:dialout crw-rw----
/dev/ttyACM1 root:dialout crw-rw-rw-
```

Default `uv run` was also made able to import the RSUSB pyrealsense2 build by adding
an ignored venv `.pth` file:

```text
/home/syhlabtop/workspace/lerobot/.venv/lib/python3.12/site-packages/00_rsusb_realsense.pth
```

Its content points at:

```text
/home/syhlabtop/src/librealsense/build-py312-rsusb/Release
```

This file is local environment state, not git-tracked. Recreate it if `.venv` is
rebuilt and `uv run lerobot-find-cameras intelrealsense` stops seeing the cameras.

## First Creation Command

For a new handover dataset, use the base repo id. `lerobot-record` stamps a timestamp
onto the repo id when `--resume=false`:

```bash
cd /home/syhlabtop/workspace/lerobot

uv run lerobot-record \
  --teleop.type=openarm_mini \
  --teleop.port_right="$OPENARM_MINI_RIGHT" \
  --teleop.port_left="$OPENARM_MINI_LEFT" \
  --teleop.id=mini_set1 \
  --robot.type=bi_openarm_follower \
  --robot.id=openarm_bimanual_follower \
  --robot.left_arm_config.port=can0 \
  --robot.left_arm_config.side=left \
  --robot.left_arm_config.max_relative_target=5 \
  --robot.right_arm_config.port=can1 \
  --robot.right_arm_config.side=right \
  --robot.right_arm_config.max_relative_target=5 \
  --robot.cameras='{ left_wrist: {type: intelrealsense, serial_number_or_name: "315122270766", width: 640, height: 480, fps: 30}, right_wrist: {type: intelrealsense, serial_number_or_name: "230322273311", width: 640, height: 480, fps: 30}, base: {type: intelrealsense, serial_number_or_name: "213622075840", width: 640, height: 480, fps: 30} }' \
  --display_data=false \
  --dataset.repo_id=KETI-IRRC/openarm_handover_v0 \
  --dataset.private=true \
  --dataset.single_task="Pick the banana, hand it over to the other arm, and place it at the target." \
  --dataset.num_episodes=20 \
  --dataset.episode_time_s=30 \
  --dataset.fps=30 \
  --dataset.reset_time_s=15
```

Important camera type detail: this codebase's camera config choice is
`intelrealsense`, not `realsense`.

## Resume Command Used For Remaining Episodes

After the first 7 episodes, the right wrist camera timed out:

```text
RealSenseCamera(230322273311) latest frame is too old: 521.3 ms (max allowed: 500 ms)
```

The saved data survived. Resume requires the stamped repo id and an explicit local
root. Do not resume with only `KETI-IRRC/openarm_handover_v0`; it will not infer the
latest timestamped repo. Do not omit `--dataset.root`; `LeRobotDataset.resume()` rejects
writing into the revision-safe Hub snapshot cache.

Command used to append the remaining 13 episodes:

```bash
cd /home/syhlabtop/workspace/lerobot

uv run lerobot-record \
  --teleop.type=openarm_mini \
  --teleop.port_right="$OPENARM_MINI_RIGHT" \
  --teleop.port_left="$OPENARM_MINI_LEFT" \
  --teleop.id=mini_set1 \
  --robot.type=bi_openarm_follower \
  --robot.id=openarm_bimanual_follower \
  --robot.left_arm_config.port=can0 \
  --robot.left_arm_config.side=left \
  --robot.left_arm_config.max_relative_target=5 \
  --robot.right_arm_config.port=can1 \
  --robot.right_arm_config.side=right \
  --robot.right_arm_config.max_relative_target=5 \
  --robot.cameras='{ left_wrist: {type: intelrealsense, serial_number_or_name: "315122270766", width: 640, height: 480, fps: 30}, right_wrist: {type: intelrealsense, serial_number_or_name: "230322273311", width: 640, height: 480, fps: 30}, base: {type: intelrealsense, serial_number_or_name: "213622075840", width: 640, height: 480, fps: 30} }' \
  --display_data=false \
  --resume=true \
  --dataset.repo_id=KETI-IRRC/openarm_handover_v0_20260521_202117 \
  --dataset.root=/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117 \
  --dataset.private=true \
  --dataset.single_task="Pick the banana, hand it over to the other arm, and place it at the target." \
  --dataset.num_episodes=13 \
  --dataset.episode_time_s=30 \
  --dataset.fps=30 \
  --dataset.reset_time_s=15
```

Final push log showed:

```text
Processing Files (11 / 11): 446MB
New Data Upload: 283MB
Exiting
```

## Replay

Use the module entrypoint in this checkout:

```bash
cd /home/syhlabtop/workspace/lerobot

uv run python -m lerobot.scripts.lerobot_dataset_viz \
  --repo-id KETI-IRRC/openarm_handover_v0_20260521_202117 \
  --episode-index 19 \
  --num-workers 0
```

If rerun is missing:

```bash
uv pip install 'lerobot[viz]'
# or
uv pip install rerun-sdk
```

## Verification

Local metadata check:

```bash
sed -n '1,220p' \
  /home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117/meta/info.json
```

Expected key values:

```text
total_episodes: 20
total_frames: 17944
robot_type: bi_openarm_follower
fps: 30
features.action.shape: [16]
features.observation.state.shape: [16]
observation.images.{left_wrist,right_wrist,base}: 480x640x3 video
```

## Safety Code Changes From This Session

This session also patched the local fork to avoid leaving OpenArm torque on during
partial failures and Ctrl-C exits:

- `lerobot_record.py`: closes OpenArm follower grippers at record start and after each
  recorded episode without adding dataset frames.
- `damiao.py`: cleans up CAN bus on connect/handshake failure; sends repeated
  torque-disable pulses, including extra gripper pulses, during disconnect.
- `openarm_follower.py`: disconnect now handles partially connected arms and cameras.
- `bi_openarm_follower.py`: bimanual connect now disconnects any already-connected arm
  when the second arm fails.

These changes are intentionally scoped to OpenArm follower / Damiao / record paths so
the fork stays close to upstream behavior elsewhere.

## Emergency Torque-Off

If a process is interrupted repeatedly and any OpenArm motor still feels torqued,
use the raw CAN disable pulse below after making sure the robot is physically safe:

```bash
cd /home/syhlabtop/workspace/lerobot

uv run python -c "import time, can; ids=list(range(1,9)); data=bytes([0xFF]*7+[0xFD]);
for port in ['can0','can1']:
    print('disable', port)
    bus=can.interface.Bus(channel=port, interface='socketcan', fd=True, bitrate=1000000, data_bitrate=5000000)
    try:
        for _ in range(10):
            for mid in ids:
                bus.send(can.Message(arbitration_id=mid, data=data, is_extended_id=False, is_fd=True))
                time.sleep(0.002)
            bus.send(can.Message(arbitration_id=8, data=data, is_extended_id=False, is_fd=True))
            time.sleep(0.03)
    finally:
        bus.shutdown()
print('done')"
```

Expected output:

```text
disable can0
disable can1
done
```

## Known Risks

- RealSense `230322273311` timed out once at 30 fps. If this recurs, consider lowering
  camera fps/resolution or enabling streaming encoding/encoder threading before long
  recording sessions.
- The local RSUSB pyrealsense2 `.pth` file is not tracked. Recreate it after venv
  rebuilds.
- The record helper closes follower grippers, but the operator should also start the
  mini grippers in a compatible closed pose to avoid a first-frame reopen jump.
- Dataset visual replay should still be reviewed in rerun before using this dataset for
  training decisions.
