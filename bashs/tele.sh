## cali
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras={} \
#--control.type=calibrate
#cd scripts

## teleoperation

#!/bin/bash

ROBOT_TYPE=so100
HEAD_CAMERA_SERIAL=918512073045
HAND_CAMERA_SERIAL=218622278274

echo "🕹️ Starting teleoperation..."
cd ..
cd ..

python lerobot/scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras={} \
--control.type=teleoperate
cd scripts
  --robot.type=${ROBOT_TYPE} \
  --robot.cameras="{
    \"head\": {\"type\": \"intelrealsense\", \"serial_number\": ${HEAD_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720},
    \"wrist\": {\"type\": \"intelrealsense\", \"serial_number\": ${HAND_CAMERA_SERIAL}, \"fps\": 30, \"width\": 1280, \"height\": 720}
  }" \
  --control.type=teleoperate \
  --control.display_data=true
echo "✅ Teleoperation ended."

## record / for configs, check config list on lerobot.common.robot_devices.control_configs.RecordControlConfig
#recorder=syhlab
#exp_name=test_record
#exp_num=2
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras={} \
#--control.type=record \
#--control.fps=30 \
#--control.single_task='test_task' \
#--control.repo_id=${recorder}/${exp_name}_${exp_num} \
#--control.num_episodes=3 \
#--control.push_to_hub=false \
#--control.warmup_time_s=2 \
#--control.episode_time_s=5 \
#--control.reset_time_s=5
#cd bashs

## replay
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras={} \
#--control.type=replay \
#--control.fps=30 \
#--control.repo_id=${recorder}/${exp_name}_${exp_num}  \
#--control.episode=2 \
#--control.local_files_only=true
#cd bashs
