# Handoff Prompt - syhlabtop Banana Handover Session 2026-05-21

Use the prompt below for the next main management agent.

```text
You are the main management agent for the syhlabtop OpenArm LeRobot fork.
Continue from the 2026-05-21 banana handover data collection session.

Repository:
- Path: /home/syhlabtop/workspace/lerobot
- Branch: audit/openarm-folding-baseline
- Current SSOT: docs/PLAN.md
- Current status file: docs/STATUS.md
- Session runbook: docs/_archive/openarm_folding/banana_handover_recording_session_2026-05-21.md

Primary result:
- Dataset collection is complete and pushed.
- Dataset repo_id: KETI-IRRC/openarm_handover_v0_20260521_202117
- Local root: /home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117
- meta/info.json: total_episodes=20, total_frames=17944, fps=30, robot_type=bi_openarm_follower
- Task: Pick the banana, hand it over to the other arm, and place it at the target.
- Cameras: left_wrist D405 315122270766, right_wrist D405 230322273311, base D435I 213622075840
- Teleop: openarm_mini, id=mini_set1
- Robot: bi_openarm_follower, id=openarm_bimanual_follower, can0=left, can1=right

Important hardware/session mapping:
- OPENARM_MINI_LEFT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA096282-if00
- OPENARM_MINI_RIGHT=/dev/serial/by-id/usb-1a86_USB_Single_Serial_58FA095468-if00
- Mini calibration: /home/syhlabtop/.cache/huggingface/lerobot/calibration/teleoperators/openarm_mini/mini_set1.json
- Camera config type in this repo is intelrealsense, not realsense.
- Default uv sees the RSUSB pyrealsense2 build through an ignored local .pth file:
  /home/syhlabtop/workspace/lerobot/.venv/lib/python3.12/site-packages/00_rsusb_realsense.pth
  pointing to /home/syhlabtop/src/librealsense/build-py312-rsusb/Release.
  Recreate this if the venv is rebuilt.

What happened:
- Mini stable serial paths were identified and exported.
- openarm_mini calibration mini_set1 was completed.
- Direct teleop control with follower and cameras worked.
- Initial record command failed when camera type was written as realsense; fixed to intelrealsense.
- First collection produced 7 good episodes, then right_wrist RealSense 230322273311 timed out with latest-frame staleness.
- Data from those 7 episodes survived and was uploaded.
- Remaining 13 episodes were appended with --resume=true, the exact stamped repo_id, and explicit --dataset.root.
- Final upload completed: Processing Files (11 / 11) 446MB, New Data Upload 283MB, Exiting.

Critical resume rule:
- New datasets: use base repo_id KETI-IRRC/openarm_handover_v0 and let lerobot-record stamp it.
- Resume/replay existing data: use exact stamped repo_id KETI-IRRC/openarm_handover_v0_20260521_202117.
- Resume requires explicit --dataset.root=/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117.
- --resume=true with only KETI-IRRC/openarm_handover_v0 does not auto-find the latest stamped repo.

Code changes from the session:
- src/lerobot/scripts/lerobot_record.py
  - Added OpenArm-only gripper close helper.
  - It closes follower grippers at record start and after each recorded episode without adding dataset frames.
  - It uses CAN motor state/action only, not camera observation, to avoid coupling to RealSense timeouts.
- src/lerobot/motors/damiao/damiao.py
  - Connect failure now shuts down the CAN socket and clears it.
  - Disconnect now sends repeated torque-disable pulses and extra gripper torque-off pulses.
- src/lerobot/robots/openarm_follower/openarm_follower.py
  - Disconnect handles partial connection state: bus and cameras are disconnected only if connected.
- src/lerobot/robots/bi_openarm_follower/bi_openarm_follower.py
  - If right arm connect fails after left arm connected, bimanual connect now disconnects the partial setup and re-raises.
These patches are intentionally scoped to OpenArm/Damiao/record paths to stay close to upstream.

Safety context:
- User once hit Ctrl-C repeatedly during a mini-side problem and follower torque, especially gripper torque, did not fully drop.
- A later partial connect failed on right-arm gripper handshake while left arm/cameras were already connected.
- The code patch addresses that failure shape, but operator should still keep physical power abort/E-stop ready.
- If torque remains on, use the raw CAN disable command from banana_handover_recording_session_2026-05-21.md.

Next recommended checks:
1. Confirm git is clean except any user-owned unrelated files:
   git status --short --branch
2. Replay the dataset visually:
   cd /home/syhlabtop/workspace/lerobot
   uv run python -m lerobot.scripts.lerobot_dataset_viz \
     --repo-id KETI-IRRC/openarm_handover_v0_20260521_202117 \
     --episode-index 19 \
     --num-workers 0
3. Inspect local metadata:
   sed -n '1,220p' /home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117/meta/info.json
4. Decide whether this dataset is for immediate replay review only, a small handover fine-tune, or additional data collection with more episodes/varied objects.

Do not:
- Do not delete or overwrite the local dataset root.
- Do not resume into the unstamped base repo id.
- Do not commit the ignored .venv .pth file unless the user explicitly asks for environment materialization.
- Do not assume camera type "realsense" works in this checkout; use "intelrealsense".
```
