# Syhlabtop Stage Guides

Date: 2026-05-11
Machine: `syhlabtop`
Repo path: `/home/syhlabtop/workspace/lerobot`
Goal: prepare no-motion/shadow-readiness artifacts.

## Stage S0: Safety and Scope

Prompt to use:

```text
Confirm the session scope before touching hardware.

Goal: no-motion/shadow readiness only.
Forbidden: training, full dataset download, model.safetensors download, lerobot-rollout, lerobot-record, lerobot-replay, robot.send_action(), policy output to motors, any robot motion.

Report:
- operator present: yes/no
- E-stop location known: yes/no
- robot workspace clear: yes/no
- no-motion objective acknowledged: yes/no
```

Exit condition:

- No hardware command has run.
- Safety state is written to the preflight note.

## Stage S1: Repo and Storage Preflight

Prompt to use:

```text
Run repo and storage preflight from /home/syhlabtop/workspace/lerobot.

Allowed commands are read-only or mkdir for the selected work root.
Do not run robot commands.

Collect:
- pwd
- git status --short --branch
- git log -1 --oneline --decorate
- df -h for /, /data if present, /mnt/nas/lerobot_shared if present
- mount status for /mnt/nas/lerobot_shared

Choose syhlabtop work root:
- /data/keti/syh/openarm_folding_20260511 if /data is local and writable
- otherwise /home/syhlabtop/openarm_folding_20260511

Create:
<syhlabtop-work-root>/audits
<syhlabtop-work-root>/camera_maps
<syhlabtop-work-root>/hardware/openarm
<syhlabtop-work-root>/calibration
<syhlabtop-work-root>/shadow_snapshots
<syhlabtop-work-root>/shadow_reviews
<syhlabtop-work-root>/safety_configs

Write:
<syhlabtop-work-root>/audits/2026-05-11_preflight_syhlabtop.md
```

Exit condition:

- Work root is known.
- NAS availability is known.
- Preflight note exists.

## Stage S2: Camera Mapping, No Motion

Prompt to use:

```text
Map cameras without moving the robot and without running policy inference.

Target camera keys:
- left_wrist
- right_wrist
- base

Use only non-actuating camera discovery/capture commands. If a command can move motors or start robot control, stop and ask.

Save outputs under:
<syhlabtop-work-root>/camera_maps/

Required record:
- physical camera label
- device path or serial
- assigned policy key
- sample image filename if captured
- resolution
- timestamp
```

Exit condition:

- Each of `left_wrist`, `right_wrist`, `base` is mapped or explicitly blocked.

## Stage S3: CAN and Calibration Mapping, No Motion

Prompt to use:

```text
Inspect OpenArm CAN and calibration mapping without commanding motion.

Do not enable torque.
Do not send motor commands.
Do not call robot.send_action().

Collect:
- CAN interface names
- robot config path if used
- calibration files present
- right arm motor bus and IDs
- left arm motor bus and IDs
- gripper mapping
- any mismatch between config and physical labels

Save notes under:
<syhlabtop-work-root>/hardware/openarm/
<syhlabtop-work-root>/calibration/
```

Exit condition:

- It is clear whether the 16 state names can be read in the required order.

## Stage S4: No-Send Snapshot, Operator-Gated

Prompt to use:

```text
Only proceed if the operator explicitly approves non-actuating robot IO.

Create one no-send observation snapshot.
Do not compute policy action on syhlabtop.
Do not send any action.

Required snapshot layout:
snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json

state_16.csv columns must be exactly:
right_joint_1.pos,right_joint_2.pos,right_joint_3.pos,right_joint_4.pos,right_joint_5.pos,right_joint_6.pos,right_joint_7.pos,right_gripper.pos,left_joint_1.pos,left_joint_2.pos,left_joint_3.pos,left_joint_4.pos,left_joint_5.pos,left_joint_6.pos,left_joint_7.pos,left_gripper.pos

Units: degrees.
metadata.json must include:
- timestamp
- hostname
- repo path
- branch
- commit
- work root
- camera mapping
- CAN/calibration mapping note paths
- send_allowed=false
- motion_allowed=false
```

Exit condition:

- Snapshot bundle exists, or blocker is documented.
- `send_allowed=false` is present.

## Stage S5: Handoff to A6000

Prompt to use:

```text
If /mnt/nas/lerobot_shared is mounted, copy the snapshot bundle to:
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/

If NAS is not mounted, report the local snapshot path and do not improvise a transfer method without operator approval.

Do not run A6000 inference from syhlabtop.
Do not send actions.
```

Exit condition:

- A6000 can find the snapshot on NAS, or manual transfer is the next blocker.

## Stage S6: Final Syhlabtop Report

Prompt to use:

```text
Prepare a concise final report.

Include:
- repo path, branch, commit, worktree status
- selected work root
- NAS mount status
- camera mapping result
- CAN/calibration mapping result
- snapshot path if created
- NAS handoff path if copied
- blockers before A6000 shadow action review
- explicit safety line: no robot motion, no send_action, no rollout/record/replay
```

Exit condition:

- A human can decide whether to run A6000 snapshot action review next.

## Stop Conditions

Stop and ask before continuing if:

- a command may enable torque
- a command may actuate motors
- a command starts rollout, record, replay, or teleop
- camera mapping is ambiguous
- state order cannot be proven
- units are not degrees
- gripper semantics are unclear
- NAS path is unavailable and transfer is needed
