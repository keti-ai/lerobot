# OpenArm Limit/Axis Physical Check Plan

Date: 2026-05-14

## Current Evidence

Read-only audit artifact:

- `/home/syhlabtop/openarm_folding_20260512/audits/limit_axis_audit_2026-05-14.md`
- `/home/syhlabtop/openarm_folding_20260512/audits/limit_axis_audit_2026-05-14.json`

Current readback is within the software limits for all 16 features.

Smallest current software-limit margins:

- `right_joint_4.pos`: 4.49 deg above min `0`
- `left_gripper.pos`: 5.45 deg above min `-65`
- `left_joint_4.pos`: 5.61 deg above min `0`
- `right_joint_2.pos`: 8.73 deg above min `-9`
- `right_gripper.pos`: 8.84 deg below max `0`
- `left_joint_2.pos`: 11.28 deg below max `9`

Rollout-log symptoms:

- Repeated saturation/readback warnings concentrate on left wrist/forearm keys:
  `left_joint_5.pos`, `left_joint_4.pos`, `left_joint_7.pos`, `left_joint_1.pos`,
  plus grippers.
- `joint_limit_saturated_features` became high only after all-joint limit saturation
  was allowed. This means the model frequently asks for targets outside current
  review limits, but actual commands are clamped inside the software range.

## What This Does Not Prove

The current audit does not prove the physical hard stops or visual axis semantics.
It only proves:

- current readback is inside software limits,
- software limits match LeRobot `OpenArmFollowerConfigBase` side defaults,
- the live harness is clamping commands into those limits.

The missing piece is whether these software limits and signs match the actual
assembled robot after zeroing, printed parts, gripper jaws, and left/right
mounting.

## Required Physical Checks

### 1. No-Write Manual Pose Check

With torque disabled, manually place the robot in a visually neutral folding-ready
pose and run the read-only audit again.

Record for each suspicious joint:

- visual pose
- readback degrees
- whether readback is near expected neutral
- whether the joint is close to a software limit despite visually having room

Suspicious keys:

- `left_joint_4.pos`
- `left_joint_5.pos`
- `left_joint_6.pos`
- `left_joint_7.pos`
- `right_joint_4.pos`
- `right_gripper.pos`
- `left_gripper.pos`

### 2. Tiny Direction Probe

Only after operator approval, run a tiny single-joint pulse probe:

- one joint at a time
- selected motor torque only
- `+1 deg`, return to start, `-1 deg`, return to start
- operator records visual direction for each pulse
- no policy inference
- no camera dependency
- no `send_action`
- no `OpenArmFollower.connect`

Output table:

| key | +1 deg visual direction | -1 deg visual direction | expected? | notes |
| --- | --- | --- | --- | --- |

### 3. Soft Physical Range Review

Do not drive to hard stops. The useful check is whether the current software
limits are too narrow, too wide, or sign-flipped relative to a comfortable
folding workspace.

For each suspicious joint:

- comfortable min visual pose and readback
- comfortable max visual pose and readback
- whether software min/max should be adjusted for rollout

## Likely Outcomes

If signs and neutral pose are correct:

- Keep current joint order/signs.
- Continue live rollout, but reduce model pressure into limits by narrowing the
  runtime soft workspace or adding per-joint cap differences for left wrist axes.

If any sign is flipped:

- Stop policy rollout.
- Fix action/state sign mapping before more learned-policy motion.

If zero/readback is shifted:

- Do not rewrite calibration immediately.
- First record a corrected runtime limit table in the live harness and compare
  against dataset state distribution.

If gripper semantics are offset:

- Keep gripper saturation but adjust gripper runtime open/close limits to the
  installed jaws, not generic `[-65, 0]`.

## Current Recommendation

Do not run the next long policy rollout until at least the tiny direction probe
has been performed for the suspicious left wrist axes and both grippers.
