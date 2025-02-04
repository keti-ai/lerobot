# cali

# teleoperation

# record
cd ..
python lerobot/scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras={} \
--control.type=record \
--control.fps=30 \
--control.single_task='test_task' \
--control.repo_id=syhlab/my_robot_test_6 \
--control.num_episodes=1 \
--control.push_to_hub=false
cd scripts
# replay

cd ..
python lerobot/scripts/control_robot.py \
--robot.type=so100 \
--robot.cameras={} \
--control.type=replay \
--control.fps=30 \
--control.repo_id=syhlab/my_robot_test_6 \
--control.episode=0 \
--control.local_files_only=true
cd scripts
