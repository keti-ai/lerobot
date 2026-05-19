# Damiao Setup vs Axis Alignment Review

timestamp: `2026-05-14`
repo_head: `8d6382ce0e04bf244cb3bb18f9cde8a1b40284b6`

## Decision

Persistent Damiao motor setting changes are not a required next step for the current folding rollout setup.

Freeze motor-side settings for now. Treat the remaining issue as an axis, zero, software-limit, and real folding hardware-contract alignment problem unless a read-only CAN/motor-ID test proves otherwise.

## What Is Required From Damiao

- CAN interface configured and stable.
- Correct left/right bus mapping.
- Correct OpenArm default motor IDs and receive IDs.
- Correct motor type mapping: `joint_1..2=dm8009`, `joint_3..4=dm4340`, `joint_5..7/gripper=dm4310`.
- Existing motor zero convention must match the robot assembly/training contract.

These are setup prerequisites, not rollout-time tuning knobs.

## What We Should Not Change Casually

- Do not call `OpenArmFollower.connect()` on the actual rollout path. In this repo it can call `bus.set_zero_position()` and `bus.enable_torque()`.
- Do not call `set_zero_position()` unless a separate physical calibration procedure is deliberately approved.
- Do not treat `write_calibration()` as a Damiao hardware fix. The Damiao bus implementation only caches LeRobot calibration in memory; Damiao motors do not store that calibration internally.
- Do not use Damiao configuration changes to compensate for a suspicious policy axis before verifying side/order/sign/zero.

## Current Evidence

- Current live rollout uses `DamiaoMotorsBus guarded MIT batch`, not `send_action`, `lerobot-rollout`, or `OpenArmFollower.connect`.
- `rollout_trial_20260514_155239` completed full-16 execution:
  - chunks: `24`
  - actions: `468`
  - stop_reason: `max_chunks`
  - selected_scope: `full-16`
- Limit/axis audit readbacks were all within current software limits.
- High saturation/readback symptoms concentrate on `left_joint_5.pos`, `left_joint_4.pos`, `left_joint_7.pos`, grippers, and joint4 limit conventions.

This pattern does not prove broken Damiao settings. It is more consistent with one or more of:

- policy pushing to a real workspace boundary,
- software limits too narrow for the assembled folding setup,
- training robot zero/range differing from this robot,
- sign or side convention mismatch on a subset of axes,
- gripper degree range differing because of larger jaws or assembly.

## Alignment With Real Folding Project

The folding project is not just stock OpenArm plus arbitrary motor tuning. The published setup adds task-specific hardware:

- bimanual OpenArm,
- +5 cm upper-arm/bicep extension,
- larger gripper jaws,
- camera-based observations,
- joint-space policy outputs,
- relative action training with inference postprocessing back to absolute robot targets.

Therefore the relevant alignment checks are:

1. Physical hardware: confirm +5 cm arm extension and larger jaws are installed or record deviation.
2. Sensor layout: confirm base/high view and wrist views match the folding dataset view closely enough.
3. Robot contract: confirm `robot_config_id`, selected feature order, units in degrees, and gripper range.
4. Axis contract: confirm positive direction and comfortable range for suspicious axes.
5. Runtime limits: update only runtime soft limits after physical direction/range confirmation.

## Recommended Next Check

Run a tiny axis contract check before changing any Damiao persistent state:

1. Read-only neutral/range observation for suspicious joints.
2. If motion is approved, one joint at a time:
   - command `+1 deg`,
   - readback and operator visual direction note,
   - return to start,
   - command `-1 deg`,
   - readback and operator visual direction note,
   - return to start.
3. Record physical positive direction, safe observed range, and whether software sign matches the assembled robot.

If signs match, adjust runtime soft limits/workspace envelope and continue live rollout. If signs or side/order mapping do not match, stop policy rollout and fix the software contract, not Damiao motor settings.
