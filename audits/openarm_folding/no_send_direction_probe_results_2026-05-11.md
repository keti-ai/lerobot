# No-Send Direction Probe Results

Date: 2026-05-11
Work root: `/home/syhlabtop/openarm_folding_20260511`
Scope: manual direction/limit check only.

This probe used direct Damiao state reads only:

```text
DamiaoMotorsBus.connect(handshake=False)
sync_read_all_states()
disconnect(disable_torque=False)
```

No torque enable, torque disable, zero write, goal write, `send_action`, rollout,
record, or replay command was used.

## Operator Axis Definitions

Operator-defined positive directions used during this probe:

```text
joint_2  + shoulder lift / side lateral raise
joint_4  + elbow flex
joint_7  + wrist flap up toward ceiling from zero/parallel pose
gripper  + close
```

Operator hardware notes:

```text
joint_5: forearm axial roll
joint_6: handshake-plane wrist/forearm fan
joint_7: wrist flap pitch, orthogonal to joint_6
```

## Recorded Samples

Official saved samples:

```text
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_144602.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_144751.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_144903.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_145046.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_145223.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_145418.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_145526.csv
/home/syhlabtop/openarm_folding_20260511/calibration/direction_probe_20260511_145625.csv
```

Discarded sample:

```text
right_joint_7 was accidentally advanced before operator movement in an earlier
interactive run. That run was interrupted and did not write a result file.
Use direction_probe_20260511_144602 for right_joint_7.
```

## Direction Table

| Feature | Operator positive direction | Before deg | After deg | Delta deg | Observed sign | Review limit used |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `right_joint_2.pos` | shoulder lift / side lateral raise | -0.295 | 47.419 | 47.714 | positive | [-9, 90] |
| `left_joint_2.pos` | shoulder lift / side lateral raise | -0.273 | -50.457 | -50.184 | negative | [-90, 9] |
| `right_joint_4.pos` | elbow flex | -0.382 | 122.716 | 123.098 | positive | [0, 135] |
| `left_joint_4.pos` | elbow flex | -1.825 | 42.741 | 44.566 | positive | [0, 135] |
| `right_joint_7.pos` | wrist flap up | 7.246 | 39.200 | 31.955 | positive | [-80, 80] |
| `left_joint_7.pos` | wrist flap up | -3.246 | -85.756 | -82.510 | negative | [-80, 80] |
| `right_gripper.pos` | close to max closed | -18.458 | 36.031 | 54.489 | positive | [-65, 0] |
| `left_gripper.pos` | close to max closed | -4.732 | 38.173 | 42.905 | positive | [-65, 0] |

## Findings

`joint_2` appears mirrored between arms:

```text
right_joint_2 + shoulder lift -> positive
left_joint_2  + shoulder lift -> negative
```

This matches the asymmetric review limits:

```text
right_joint_2 [-9, 90]
left_joint_2  [-90, 9]
```

`joint_4` elbow flex is positive on both arms and matches the `[0, 135]`
review limit direction.

`joint_7` wrist flap up appears mirrored between arms:

```text
right_joint_7 + wrist flap up -> positive
left_joint_7  + wrist flap up -> negative
```

The current symmetric `[-80, 80]` review limits do not encode that physical
mirror direction. Also, the manual left wrist-flap sample reached `-85.756 deg`,
slightly outside the review lower bound of `-80 deg`. Before any motion gate,
left/right `joint_7` sign and physical range should be explicitly handled.

Both grippers close in the positive direction:

```text
right_gripper max-closed sample: 36.031 deg
left_gripper  max-closed sample: 38.173 deg
```

This differs from the A6000 review/audit gripper limit of `[-65, 0]`, but it
does not by itself prove a calibration or zero-position error. The LeRobot
OpenArm side-specific baseline uses `[-65, 0]`, while the existing bimanual
record configs in `../openarm_lerobot` use `gripper: [-90, 45]`.

The likely interpretation is:

```text
[-65, 0]   baseline / Quest frozen contract / conservative working range
[-90, 45]  syhlabtop bimanual record preset / wider physical range
```

For initial folding deploy work, following the LeRobot baseline `[-65, 0]`
remains the safer default unless the task explicitly requires more closing
travel. If full close is required later, use an explicit folding-specific
gripper limit decision instead of silently inheriting the wider record preset.

## Gripper-Only Zero Adjustment

After reviewing the OpenArm baseline docs, the operator clarified that the
vendor-provided follower arms were already zeroed and only the gripper motors
had been replaced. OpenArm's baseline defines gripper zero as fully closed.

The grippers were manually set to fully closed and read before zeroing:

```text
left_gripper=38.173144
right_gripper=35.812594
```

Then only motor ID `008` on each follower CAN bus was zeroed:

```bash
/home/syhlabtop/workspace/openarm_can/setup/openarm-can-set-zero can0 008
/home/syhlabtop/workspace/openarm_can/setup/openarm-can-set-zero can1 008
```

No arm joint zero was changed. No full-arm zero-position calibration was run.

Closed-position readback after gripper-only zero:

```text
left_gripper=-0.010928
right_gripper=-0.010928
```

Slightly-open readback after gripper-only zero:

```text
left_gripper=-26.632680
right_gripper=-23.244854
```

This confirms the baseline convention after adjustment:

```text
0 deg ~= fully closed
negative gripper values ~= opening direction
baseline gripper range [-65, 0] is now appropriate for initial deploy review
```

## Impact on A6000 Snapshot Action Review

Arm joint limits used by A6000 were mostly consistent with observed direction:

- `right_joint_2` and `left_joint_2` clamp behavior matches mirrored limits.
- `right_joint_4` and `left_joint_4` clamp behavior matches elbow-flex positive
  direction.

Open issues before command candidacy:

- gripper baseline `[-65, 0]` is appropriate after gripper-only zero, but any
  future wider folding-specific range still requires explicit operator approval;
- `left_joint_7` wrist-flap direction/range must be reviewed before treating a
  policy delta as a physical up/down wrist command;
- any future command path must apply a small per-step delta cap and must print
  both raw and clamped targets before sending.

## Motion Status

Motion remains blocked. These samples are manual, no-send direction checks only.
