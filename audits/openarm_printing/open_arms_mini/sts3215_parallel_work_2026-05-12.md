# STS3215 Parallel Work While Printing

Date: 2026-05-12
Scope: Open Arms Mini / `openarm_mini` teleoperator

## Goal

Use the printing window to prepare the 16 Feetech STS3215 motors for the Mini pair.

`openarm_mini` expects two independent buses:

- right arm: IDs 1-8
- left arm: IDs 1-8

Each arm uses the same ID map:

| ID | LeRobot name | Physical joint |
| ---: | --- | --- |
| 1 | `joint_1` | Shoulder Pan |
| 2 | `joint_2` | Shoulder Lift |
| 3 | `joint_3` | Shoulder Roll |
| 4 | `joint_4` | Elbow Flex |
| 5 | `joint_5` | Forearm Rotation |
| 6 | `joint_6` | Wrist Flex |
| 7 | `joint_7` | Wrist Roll |
| 8 | `gripper` | Gripper |

## Important Setup Behavior

`lerobot-setup-motors --teleop.type=openarm_mini` prompts in reverse order:

1. Right `gripper` -> ID 8
2. Right `joint_7` -> ID 7
3. Right `joint_6` -> ID 6
4. Right `joint_5` -> ID 5
5. Right `joint_4` -> ID 4
6. Right `joint_3` -> ID 3
7. Right `joint_2` -> ID 2
8. Right `joint_1` -> ID 1
9. Left `gripper` -> ID 8
10. Left `joint_7` -> ID 7
11. Left `joint_6` -> ID 6
12. Left `joint_5` -> ID 5
13. Left `joint_4` -> ID 4
14. Left `joint_3` -> ID 3
15. Left `joint_2` -> ID 2
16. Left `joint_1` -> ID 1

Only connect one motor at a time when prompted.

## Physical Prep

Before running software:

- Put 16 motors in a tray.
- Do not open the gearboxes or remove gears. Open Arms Mini does not follow the SO-ARM100 leader gear-removal step.
- Make labels with variant included:
  - `R1-C018`, `R2-C044`, `R3-C044`, `R4-C001`, `R5-C046`, `R6-C046`, `R7-C046`, `R8-C018`
  - `L1-C018`, `L2-C044`, `L3-C044`, `L4-C001`, `L5-C046`, `L6-C046`, `L7-C046`, `L8-C018`
- Make a temporary "DONE" area.
- Keep only one motor connected to the Waveshare board during ID assignment.
- Do not daisy-chain motors until all IDs are assigned.

Selected motor variant assignment:

| Side | ID 1 | ID 2 | ID 3 | ID 4 | ID 5 | ID 6 | ID 7 | ID 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Right | C018 | C044 | C044 | C001 | C046 | C046 | C046 | C018 |
| Left | C018 | C044 | C044 | C001 | C046 | C046 | C046 | C018 |

## Hardware Modification Check

No motor-internal hardware modification is planned for Mini.

SO-ARM100 explicitly removes gears from leader motors to reduce friction and use only position encoding. Open Arms Mini is different: its BOM and assembly path use normal STS3215-C046 servos, installed with horns and screws, and the LeRobot `openarm_mini` driver reads motor positions with torque disabled during calibration. Therefore:

- Do not remove gears from C018/C044/C001/C046 motors.
- Do not split the servo case unless a motor is already defective and being inspected separately.
- Keep grease, gear mesh, encoder alignment, and output shaft stack untouched.
- If a joint feels too stiff later, first check torque-disabled state, cable drag, printed part rubbing, horn alignment, screw overtightening, and motor variant placement before considering any irreversible motor changes.

Bench checks before ID assignment:

- Confirm the case, output spline, horn, and connector are not cracked or loose.
- Rotate each output gently by hand only enough to feel binding; do not force high-reduction C001/C018 motors.
- Verify left/right pairs use the same variant for the same ID.
- Label every motor before connecting it to the setup board.
- Power and configure one motor at a time.

## Port Discovery

Run:

```bash
uv run lerobot-find-port
```

If the script asks to unplug/replug the controller, follow the prompt and record the result here:

| Board | Port |
| --- | --- |
| right/setup board | TBD |
| left board, if separate | TBD |

Alternative quick check:

```bash
ls -l /dev/serial/by-id/
```

## Motor ID Setup Command

Use the detected port for both `port_right` and `port_left` if setting IDs through one controller board sequentially:

```bash
uv run lerobot-setup-motors \
  --teleop.type=openarm_mini \
  --teleop.port_right=/dev/ttyUSB0 \
  --teleop.port_left=/dev/ttyUSB0
```

Replace `/dev/ttyUSB0` with the actual port.

Reason: setup is done one motor at a time. The script will still walk through right then left motor definitions, but the same physical setup board can be used for both label sets.

## Execution Checklist

| Step | Prompt target | Connect this variant | Label after success | Status |
| ---: | --- | --- | --- | --- |
| 1 | RIGHT `gripper` | C018 | `R8-C018` | pending |
| 2 | RIGHT `joint_7` | C046 | `R7-C046` | pending |
| 3 | RIGHT `joint_6` | C046 | `R6-C046` | pending |
| 4 | RIGHT `joint_5` | C046 | `R5-C046` | pending |
| 5 | RIGHT `joint_4` | C001 | `R4-C001` | pending |
| 6 | RIGHT `joint_3` | C044 | `R3-C044` | pending |
| 7 | RIGHT `joint_2` | C044 | `R2-C044` | pending |
| 8 | RIGHT `joint_1` | C018 | `R1-C018` | pending |
| 9 | LEFT `gripper` | C018 | `L8-C018` | pending |
| 10 | LEFT `joint_7` | C046 | `L7-C046` | pending |
| 11 | LEFT `joint_6` | C046 | `L6-C046` | pending |
| 12 | LEFT `joint_5` | C046 | `L5-C046` | pending |
| 13 | LEFT `joint_4` | C001 | `L4-C001` | pending |
| 14 | LEFT `joint_3` | C044 | `L3-C044` | pending |
| 15 | LEFT `joint_2` | C044 | `L2-C044` | pending |
| 16 | LEFT `joint_1` | C018 | `L1-C018` | pending |

## Post-ID Bus Check

After ID setup, test each arm as a daisy chain of 8 motors.

Right arm:

```bash
uv run python - <<'PY'
from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus

port = "/dev/ttyUSB0"
motors = {f"joint_{i}": Motor(i, "sts3215", MotorNormMode.DEGREES) for i in range(1, 8)}
motors["gripper"] = Motor(8, "sts3215", MotorNormMode.RANGE_0_100)
bus = FeetechMotorsBus(port=port, motors=motors)
bus.connect()
print(bus.sync_read("Present_Position", normalize=False))
bus.disconnect()
PY
```

Left arm: repeat with the left board/port.

## Do Not Do Yet

- Do not run full calibration until printed parts are installed enough to place the arm in the required hanging zero pose.
- Do not torque-test motors loose on the bench.
- Do not daisy-chain motors during ID assignment.

## Mixed Variant Note

This build intentionally mixes C018/C044/C001/C046. LeRobot reads encoder position through the same `sts3215` model path, so ID assignment and position readout should work. Expect different mechanical feel across joints because gear ratios differ.

## Full Calibration Later

After assembly:

```bash
uv run lerobot-calibrate \
  --teleop.type=openarm_mini \
  --teleop.port_right=/dev/ttyUSB0 \
  --teleop.port_left=/dev/ttyUSB1 \
  --teleop.id=openarm_mini_pair
```

During calibration the code asks each arm to:

- disable torque
- set Phase to 12
- set position mode
- place arm hanging straight down
- close gripper for zero
- record gripper closed/open range
