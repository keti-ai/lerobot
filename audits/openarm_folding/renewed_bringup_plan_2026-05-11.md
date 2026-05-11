# OpenArm Folding Renewed Bringup Plan

Date: 2026-05-11
Owner context: `syhlabtop` robot PC plus A6000 inference/review host.
Scope: PI0.5 OpenArm folding baseline bringup for real hardware deployment.

## Current Ground Truth

The repository and audit branch are active on the robot PC:

```text
/home/syhlabtop/workspace/lerobot
branch: audit/openarm-folding-baseline
remote: keti-ai/lerobot
```

The latest real-robot context is still the sibling project:

```text
/home/syhlabtop/workspace/openarm_lerobot
reference commit: 2367514
```

The A6000 side has already validated the `lerobot/folding_latest` PI0.5 policy
offline. The policy produces finite actions with shape `[1, 30, 16]` and uses
the 16-feature bimanual OpenArm state/action order:

```text
right_joint_1.pos
right_joint_2.pos
right_joint_3.pos
right_joint_4.pos
right_joint_5.pos
right_joint_6.pos
right_joint_7.pos
right_gripper.pos
left_joint_1.pos
left_joint_2.pos
left_joint_3.pos
left_joint_4.pos
left_joint_5.pos
left_joint_6.pos
left_joint_7.pos
left_gripper.pos
```

The current camera contract is:

```text
left_wrist   D405 315122270766
right_wrist  D405 230322273311
base         D435 234322070493
D415         211622062255, auxiliary situation recording only
```

The current CAN contract is:

```text
can0  physical left follower arm
can1  physical right follower arm
can2  leader-side in existing configs
can3  leader-side in existing configs
```

The follower arms were vendor-zeroed before this session. Only the gripper motors
had been replaced. After operator confirmation, both follower grippers were
physically closed and only motor ID `008` was zeroed on `can0` and `can1`.
Post-adjustment readback confirmed:

```text
closed:        left=-0.010928, right=-0.010928
slightly open: left=-26.632680, right=-23.244854
```

Therefore the OpenArm/LeRobot baseline gripper convention is now the active
default for this project:

```text
0 deg ~= fully closed
negative gripper values ~= opening direction
initial review limit: [-65, 0]
```

## Current Stage

The original no-send two-machine pipeline reached Stage 11, and the gripper-only
zero correction has now been completed after that pipeline:

```text
Stage 0  Goal/safety framing                         DONE
Stage 1  Repo preflight on A6000                     DONE
Stage 2  Shared audit docs                           DONE
Stage 3  A6000 model/config asset preparation        DONE
Stage 4  A6000 offline policy load                   DONE
Stage 5  syhlabtop repo/handoff readiness            DONE
Stage 6  syhlabtop camera mapping                    DONE
Stage 7  syhlabtop CAN/calibration mapping           DONE
Stage 8  syhlabtop no-send observation snapshot      DONE
Stage 9  A6000 snapshot action review                DONE
Stage 10 syhlabtop human/safety review               DONE FOR NO-SEND
Stage 11 summary and next blocker list               DONE
Stage 12 syhlabtop gripper-only zero adjustment      DONE
Stage 13 refreshed no-send snapshot after gripper    NEXT
Stage 14 refreshed A6000 snapshot action review      BLOCKED BY STAGE 13
Stage 15 guarded first-motion command path spec      NOT STARTED
Stage 16 guarded first-motion execution              BLOCKED
```

The previous A6000 action review remains useful as a pipeline validation, but it
is stale as a motion candidate because it was generated from the pre-gripper-zero
hardware state.

## Required Next Work

1. Capture a refreshed no-send snapshot on `syhlabtop`.

   The snapshot must be captured after gripper zero correction and must include:

   ```text
   left_wrist.png
   right_wrist.png
   base.png
   state_16.csv
   metadata.json
   ```

   The metadata should record that gripper-only zero was completed on
   2026-05-11 and that `[-65, 0]` is the active initial gripper review range.

2. Transfer the refreshed snapshot to A6000 and NAS.

   Use the same manually approved transfer path as before. Do not assume NAS is
   mounted on `syhlabtop`.

3. Run A6000 offline snapshot action review again.

   The review must produce fresh CSV/JSON artifacts and keep `send_allowed=false`.
   The old `snapshot_20260511_135634` review must not be used as a command
   candidate for the current hardware state.

4. Review the refreshed first-step proposal.

   Required checks:

   - action shape remains `[1, 30, 16]`;
   - all values are finite;
   - gripper values now make sense under the corrected `0=closed`,
     negative-open convention;
   - `right_joint_2` and `left_joint_2` mirror behavior is respected;
   - `joint_4` elbow-flex positive direction is respected;
   - `left_joint_7` sign/range is explicitly handled before any wrist command;
   - every clamped row is explained before motion.

5. Design, but do not execute, a guarded first-motion path.

   The design should be separate from rollout/record/replay and should consume
   a reviewed action artifact rather than directly streaming policy output.

## Guarded Motion Path Requirements

Any later first-motion tool must satisfy all of these before it can be used:

- default mode is dry-run;
- `send_allowed` must be false in all offline artifacts and must require a
  separate operator gate to override inside the motion tool;
- stale snapshot IDs are rejected;
- the exact raw, clamped, and final capped targets are printed before sending;
- only one selected action step may be considered for the first test;
- no chunk rollout, no closed-loop replay, no `lerobot-record`, no
  `lerobot-rollout`, no `lerobot-replay`;
- arm joint delta cap is small and explicit;
- gripper delta cap is small and explicit;
- `left_joint_7` must not be commanded until its mirrored sign and safe range are
  agreed;
- all sent targets and readbacks are logged with timestamps;
- operator must approve the exact command after seeing the printed target table.

Recommended initial caps for discussion, not yet approved for execution:

```text
arm joints: <= 2 deg from current readback
grippers:   <= 5 deg from current readback
```

## Explicitly Not Allowed Yet

The following remain out of scope until a separate explicit motion gate:

- policy output to actuators;
- autonomous rollout;
- record/replay path;
- full-arm zero-position calibration;
- direct use of the old pre-gripper-zero action review as a command candidate;
- widening gripper range beyond `[-65, 0]` without an explicit
  folding-specific decision.

## Open Blockers

- A refreshed post-gripper-zero no-send snapshot does not exist yet.
- A refreshed A6000 action review does not exist yet.
- The previous action review had large deltas and four clamped rows; it is not a
  motion candidate.
- `left_joint_7` wrist-flap direction/range needs explicit handling before any
  wrist motion.
- There is no audited live split-host inference bridge from A6000 to syhlabtop.
- There is no guarded first-motion script/spec approved for execution.

## Acceptance Criteria for the Next Milestone

Stage 13 is complete only when a new post-gripper-zero snapshot exists locally
on `syhlabtop`, includes all three policy camera images and `state_16.csv`, and
its metadata records the corrected gripper convention.

Stage 14 is complete only when A6000 produces a fresh offline review from that
new snapshot, stores CSV/JSON artifacts, and the review is copied back or made
available for syhlabtop human inspection.

Motion remains blocked after Stage 14 unless Stage 15 separately defines and
approves a guarded first-motion path.
