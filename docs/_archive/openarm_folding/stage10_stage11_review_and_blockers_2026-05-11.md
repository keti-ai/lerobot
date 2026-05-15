# Stage 10/11 Review and Blockers

Date: 2026-05-11
Snapshot: `snapshot_20260511_135634`
Scope: no-motion review only.

## Stage 10 Result

Stage 10 reviewed the returned A6000 action proposal on syhlabtop.

Accepted:

- The robot posture is the intended zero posture, per operator confirmation.
- Camera mounts are correct at the hardware level, per operator confirmation.
- Camera stream identities follow the existing LeRobot dataset convention:
  `left_wrist`, `right_wrist`, `base`.
- A6000 output shape is `[1, 30, 16]`.
- All first-step review rows are finite.
- All first-step review rows keep `send_allowed=false`.
- The action review files were copied back to syhlabtop and checksum verified.

Not approved:

- The A6000 action proposal is not approved as an actuator command.
- No autonomous or policy-driven motion gate is open.

## Action Delta Review

The first action proposal has 16 rows. Four rows are clamped by configured
joint limits:

```text
right_joint_2.pos current=-0.295 proposed=-9.005  clamped=-9.000 delta=-8.710   limits=[-9, 90]
right_joint_4.pos current=-0.382 proposed=-62.581 clamped=0.000  delta=-62.198  limits=[0, 135]
left_joint_2.pos  current=-0.929 proposed=24.740  clamped=9.000  delta=25.669   limits=[-90, 9]
left_joint_4.pos  current=0.142  proposed=-61.100 clamped=0.000  delta=-61.242  limits=[0, 135]
```

Largest absolute deltas:

```text
62.198 deg  right_joint_4.pos  clamp
61.242 deg  left_joint_4.pos   clamp
51.756 deg  right_joint_7.pos
30.076 deg  right_joint_5.pos
25.834 deg  left_joint_7.pos
25.669 deg  left_joint_2.pos   clamp
25.483 deg  right_joint_3.pos
24.039 deg  left_joint_1.pos
22.422 deg  left_joint_5.pos
```

The clamp behavior itself is useful: the postprocess/review path is enforcing
limits before any command can be considered. However, the first proposal is too
large to treat as a first real-motion command without an additional guarded
motion design.

## Stage 11 Blocker List

Before any motion test, implement and review a guarded real-robot test path that
is separate from the current offline snapshot review. Required blockers:

1. A motion-specific operator signoff that names the exact test scope.
2. A script or procedure that can execute at most one explicitly selected action
   step, not an autonomous chunk rollout.
3. A hard velocity/delta cap much smaller than the observed offline proposal
   deltas.
4. A dry-run printout of the exact 16 target values before any send.
5. An explicit `send_allowed=true` gate controlled by the operator at runtime.
6. A way to reject stale A6000 action files by snapshot id and timestamp.
7. A hold-to-run or immediate abort procedure at the robot PC.
8. Confirmation that gripper commands are absolute degree targets.
9. Confirmation that right-first then left action order is preserved:
   right joints 1-7, right gripper, left joints 1-7, left gripper.
10. A local log that records every value sent, if any future send is approved.

Until those blockers are resolved, only no-send work is allowed:

- capture additional observation snapshots;
- run A6000 offline action review;
- compare outputs against limits and expected directions;
- update audit docs.

## Current Motion Status

Motion remains blocked. The work has validated the no-send two-machine pipeline:

```text
syhlabtop cameras/state snapshot
-> manual transfer to A6000/NAS
-> A6000 offline PI05 action proposal
-> syhlabtop received review files
-> no actuator command sent
```

Do not run rollout, record, replay, or any path that can call `send_action()`
from this artifact.
