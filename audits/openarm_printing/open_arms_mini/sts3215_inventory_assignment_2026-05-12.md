# STS3215 Inventory Assignment

Date: 2026-05-12
Target: Open Arms Mini leader teleoperator

## Available Motors

| Variant | Qty | Known / observed spec | Suitability for Mini leader |
| --- | ---: | --- | --- |
| STS3215-C046 | 6 | 7.4 V, 1:147, about 14.4 kg.cm stall | Best match. Use first. |
| STS3215-C044 | 4 | 7.4 V, 1:191, about 27.4 kg.cm stall | Usable, slightly heavier feel than C046. |
| STS3215-C001 | 2 | 7.4 V, 1:345, about 19.5 kg.cm stall | Usable only if needed; high reduction feels less backdrivable. |
| STS3215-C018 | 12 | 12 V, 1:345, about 30 kg.cm stall | Avoid for leader feel if possible; voltage/rate mismatch risk on 7.5 V Mini setup. |

Open Arms Mini BOM requests 16x `STS3215-C046` for a pair. Since only 6x C046 are available, choose one of the plans below.

## Recommended Plan A: Build One High-Quality Arm First

Use this if the goal is to validate Mini teleoperation feel before committing the full pair.

| Joint | ID | Motor |
| --- | ---: | --- |
| Shoulder Pan | 1 | C044 |
| Shoulder Lift | 2 | C044 |
| Shoulder Roll | 3 | C046 |
| Elbow Flex | 4 | C046 |
| Forearm Rotation | 5 | C046 |
| Wrist Flex | 6 | C046 |
| Wrist Roll | 7 | C046 |
| Gripper | 8 | C046 |

Rationale:

- Keeps all wrist/forearm/gripper feel-critical axes on C046.
- Uses C044 only on shoulder axes where added reduction is less objectionable.
- Avoids C001/C018 for the first feel test.

Recommended labels:

- If building the right arm first: `R1=C044`, `R2=C044`, `R3-R8=C046`.
- Keep remaining motors unassigned until the first arm feel is checked.

## Plan B: Complete Pair Immediately With Symmetric Mixing

Use this only if having both arms immediately is more important than matching the intended C046 feel.

Per arm:

| Joint | ID | Motor |
| --- | ---: | --- |
| Shoulder Pan | 1 | C018 |
| Shoulder Lift | 2 | C044 |
| Shoulder Roll | 3 | C044 |
| Elbow Flex | 4 | C001 |
| Forearm Rotation | 5 | C046 |
| Wrist Flex | 6 | C046 |
| Wrist Roll | 7 | C046 |
| Gripper | 8 | C018 |

Total usage for pair:

- C046: 6
- C044: 4
- C001: 2
- C018: 4

Rationale:

- Keeps left and right arms symmetric.
- Preserves the 6x C046 for the most feel-sensitive distal axes.
- Puts high-reduction C018 on base pan and gripper, where mismatch is usually less damaging than wrist axes.

Risks:

- C018 is a 12 V-class, 1:345 motor. On the Mini's 7.5 V setup it may be slower or feel different.
- C001/C018 high reduction can make the leader less backdrivable even with torque disabled.
- Dataset actions from mixed motors should still report positions, but human teleop feel will not match a pure C046 pair.

## Plan C: Best Pair Quality

Order 10 additional C046 motors and build both arms as intended:

- Right: C046 IDs 1-8
- Left: C046 IDs 1-8

Use C044/C001/C018 as spares or for follower/non-leader experiments.

## Selected Plan

Proceed with Plan B: complete both arms immediately with symmetric mixing.

Reason: for the current build, encoder availability and immediate bilateral operation are more important than matching pure C046 hand feel. Keep left/right motor variants symmetric so any feel difference is at least mirrored across both arms.

## Labeling If Using Plan A

| Label | ID | Motor |
| --- | ---: | --- |
| R1 | 1 | C044 |
| R2 | 2 | C044 |
| R3 | 3 | C046 |
| R4 | 4 | C046 |
| R5 | 5 | C046 |
| R6 | 6 | C046 |
| R7 | 7 | C046 |
| R8 | 8 | C046 |

## Labeling If Using Plan B

| Label | ID | Motor |
| --- | ---: | --- |
| R1 | 1 | C018 |
| R2 | 2 | C044 |
| R3 | 3 | C044 |
| R4 | 4 | C001 |
| R5 | 5 | C046 |
| R6 | 6 | C046 |
| R7 | 7 | C046 |
| R8 | 8 | C018 |
| L1 | 1 | C018 |
| L2 | 2 | C044 |
| L3 | 3 | C044 |
| L4 | 4 | C001 |
| L5 | 5 | C046 |
| L6 | 6 | C046 |
| L7 | 7 | C046 |
| L8 | 8 | C018 |
