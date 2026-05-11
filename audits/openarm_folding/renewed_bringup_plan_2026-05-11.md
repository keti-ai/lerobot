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

The original no-send two-machine pipeline reached Stage 11, the gripper-only
zero correction completed after that pipeline, and the refreshed
post-gripper-zero no-send/A6000 review has now completed:

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
Stage 13 refreshed no-send snapshot after gripper    DONE
Stage 14 refreshed A6000 snapshot action review      DONE
Stage 15 guarded first-motion command path spec      DONE FOR DRY-RUN
Stage 16 guarded first-motion execution              BLOCKED
```

The previous A6000 action review for `snapshot_20260511_135634` remains useful
as an initial pipeline validation, but it is stale as a motion candidate because
it was generated from the pre-gripper-zero hardware state.

The refreshed post-gripper-zero review is:

```text
audits/openarm_folding/post_gripper_zero_snapshot_review_2026-05-11.md
```

It produced finite `[1, 30, 16]` actions with `send_allowed=false`, but the
first-step proposal still has large arm deltas and four clamped rows. It is not
approved as an actuator command.

## Required Next Work

1. Add a runtime command path, but do not execute it without a separate gate.

   Stage 15 only created the dry-run target table. Stage 16 requires a separate
   command implementation with fresh readback verification, explicit operator
   approval, and an abort procedure before any actuator command is considered.

2. Keep the runtime path bound to the refreshed post-gripper-zero review
   artifact.

   The default candidate artifact for review is:

   ```text
   /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_action_review.csv
   ```

   The tool must reject old `snapshot_20260511_135634` artifacts and any review
   whose metadata or checksum does not match the selected snapshot.

3. Decide whether `left_joint_7` is allowed in any first guarded command.

   Until the mirrored wrist-flap direction/range is explicitly accepted,
   `left_joint_7` should be held at current readback or excluded from the first
   motion candidate.

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

- A guarded dry-run target table exists, but a runtime command path does not.
- The refreshed A6000 action review has large deltas and four clamped rows; it
  is not a motion candidate without a guarded cap/selection path.
- `left_joint_7` wrist-flap direction/range needs explicit handling before any
  wrist motion.
- There is no audited live split-host inference bridge from A6000 to syhlabtop.

## Acceptance Criteria for the Next Milestone

Stage 15 is complete for dry-run only. Stage 16 requires a separate runtime
command path with fresh current readback, exact target-table approval, and
operator abort procedure.

Motion remains blocked unless Stage 15 separately defines and approves a guarded
first-motion path and the operator approves the exact target table.
