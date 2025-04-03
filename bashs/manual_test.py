from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBus
from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig

cfg = FeetechMotorsBusConfig(
    port="/dev/ttyACM1",  # assuming follower arm
    motors={"gripper": (6, "sts3215")},
    mock=False
)

bus = FeetechMotorsBus(cfg)
bus.connect()
print("Initial position:", bus.read("Present_Position"))

# Try to move the gripper a few steps
bus.write("Goal_Position", [2100], motor_names="gripper")
