## record / for configs, check config list on lerobot.common.robot_devices.control_configs.RecordControlConfig
#recorder=syhlab
#exp_name=test_record
#exp_num=$(date +"%Y%m%d_%H%M%S")  # 현재 시간 기반으로 설정됨
#
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras='{
#  "top": {
#    "type": "intelrealsense",
#    "serial_number": 918512073045,
#    "fps": 30,
#    "width": 640,
#    "height": 480
#  }
#}' \
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

recorder=syhlab
exp_name=test_record
exp_num=20250411_185907

# replay
cd ..
python lerobot/scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras='{
  "top": {
    "type": "intelrealsense",
    "serial_number": 918512073045,
    "fps": 30,
    "width": 640,
    "height": 480
  }
}' \
--control.type=replay \
--control.fps=30 \
--control.repo_id=${recorder}/${exp_name}_${exp_num}  \
--control.episode=2 \


