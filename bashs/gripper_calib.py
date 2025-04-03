import numpy as np
from types import SimpleNamespace
from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBus, CalibrationMode

# Dummy config structure matching FeetechMotorsBusConfig
dummy_config = SimpleNamespace(
    port="/dev/null",  # unused for test
    motors={"gripper": (6, "sts3215")},
    mock=True
)

# Create FeetechMotorsBus instance
bus = FeetechMotorsBus(config=dummy_config)

# Manually inject faulty calibration
bus.set_calibration({
    "motor_names": ["gripper"],
    "calib_mode": ["LINEAR"],
    "start_pos": [2048],
    "end_pos": [2048],  # This causes divide-by-zero
    "drive_mode": [0],
    "homing_offset": [0],
})

# Simulate raw motor position reading
raw_values = np.array([2048], dtype=np.float32)

# Debug output
try:
    calibrated = bus.apply_calibration(raw_values.copy(), ["gripper"])
    print("[RESULT]", calibrated)
except Exception as e:
    print("[ERROR]", e)
