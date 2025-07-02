#echo "🕹️ Starting follower calibration..."
#
#sudo chmod 777 /dev/ttyACM1
#
#python -m lerobot.calibrate \
#    --robot.type=so100_follower \
#    --robot.port=/dev/ttyACM1 \
#    --robot.id=black
#
#echo "✅ follower calibration ended."
#
#!/bin/bash
#
#echo "🕹️ Starting leader calibration..."
#
#sudo chmod 777 /dev/ttyACM0
#
#python -m lerobot.calibrate \
#    --teleop.type=so100_leader \
#    --teleop.port=/dev/ttyACM0 \
#    --teleop.id=blue
#
#echo "✅ leader calibration ended."
