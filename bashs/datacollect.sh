## record / for configs, check config list on lerobot.common.robot_devices.control_configs.RecordControlConfig
# it confirmed demo dataset collect 250418 syh bellow
#recorder=syhlab
#exp_name=pusht
#exp_num=$(date +"%Y%m%d_%H%M%S")  # 현재 시간 기반으로 설정됨
#
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras='{
#  "head": {
#    "type": "intelrealsense",
#    "serial_number": 918512073045,
#    "fps": 30,
#    "width": 1280,
#    "height": 720
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
#--control.reset_time_s=5 \
#
#cd bashs
#

# replay demo
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

# 250418 datacollect scripts for push t syh
export recorder=syhlab
export exp_name=pusht
export exp_num=$(date +"%Y%m%d_%H%M%S")

cd lerobot/
python scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras='{
  "head": {
    "type": "intelrealsense",
    "serial_number": 918512073045,
    "fps": 30,
    "width": 1280,
    "height": 720
  }
}' \
--control.type=record \
--control.fps=30 \
--control.single_task='push-T-real' \
--control.repo_id=${recorder}/${exp_name}_${exp_num} \
--control.num_episodes=5 \
--control.push_to_hub=false \
--control.warmup_time_s=2 \
--control.episode_time_s=5 \
--control.reset_time_s=5
