## cali
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras={} \
#--control.type=calibrate
#cd scripts

## teleoperation
#cd ..
#python lerobot/scripts/control_robot.py \
#--robot.type=so100 \
#--robot.cameras={} \
#--control.type=teleoperate
#cd scripts

## record
recorder=syhlab
exp_name=test_record
exp_num=1
cd ..
python lerobot/scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras={} \
--control.type=record \
--control.fps=30 \
--control.single_task='test_task' \
--control.repo_id=${recorder}/${exp_name}_${exp_num} \
--control.num_episodes=1 \
--control.push_to_hub=false
--control.warmup_time_s=2 \
--control.episode_time_s=30 \
--control.reset_time_s=5
cd scripts

## replay
cd ..
python lerobot/scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras={} \
--control.type=replay \
--control.fps=30 \
--control.repo_id=${recorder}/${exp_name}_${exp_num}  \
--control.episode=0 \
--control.local_files_only=true
cd scripts
