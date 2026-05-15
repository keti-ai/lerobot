# syhlabtop Stage 34 Right Joint 4 Limit Check Prompt

Date: 2026-05-12

Copy this prompt to the syhlabtop agent only if the operator wants to continue
with no-motion Stage 34 diagnostics.

---

You are the syhlabtop agent for Stage 34 no-motion diagnostics.

Do not move the robot. Do not run actuator write. Do not enable torque. Do not
zero. Do not run rollout, record, replay-to-robot, or `robot.send_action()`.

## Current Status

Stage 32 passed:

```text
snapshot: snapshot_20260512_155652
A6000 review: PASS
send_allowed: false
motion_status: BLOCKED
```

Stage 34 dry-run was generated on A6000:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.json
```

But Stage 35 is blocked:

```text
blocking_first_write_keys: ["right_joint_4.pos"]
```

Reason:

```text
right_joint_4.pos current: -4.229 deg
review/software limit: [0, 135] deg
2 deg capped target: -2.229 deg
target in limits: false
```

## Goal

Confirm the `right_joint_4.pos` readback/limit situation without moving the
robot.

This is a diagnostic step only.

## Allowed

- Pull latest repo docs.
- Read existing snapshot and audit files.
- Read current motor state if the read path remains:
  `DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states()`.
- Compare fresh `right_joint_4.pos` to:
  - Stage 32 snapshot value `-4.229 deg`
  - right joint 4 default review limit `[0, 135]`

## Forbidden

- `OpenArmFollower.connect()`
- torque enable
- zeroing
- calibration write
- goal write
- MIT command
- actuator write
- `send_action`
- rollout
- record
- replay-to-robot

## Steps

1. Sync repo:

```bash
cd /home/syhlabtop/workspace/lerobot
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
```

2. Read:

```bash
sed -n '1,240p' audits/openarm_folding/stage34_guarded_first_motion_dry_run_2026-05-12.md
```

3. Inspect local Stage 32 snapshot metadata and state:

```bash
SNAP=/home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260512_155652
cat "$SNAP/metadata.json"
cat "$SNAP/state_16.csv"
```

4. If and only if the operator confirms read-only CAN access is safe, read
fresh current state with the same no-send read path used in Stage 32. Do not
enable torque or send goals.

5. Write:

```text
/home/syhlabtop/openarm_folding_20260512/audits/stage34_right_joint4_limit_check_2026-05-12.md
```

Include:

```text
repo_head:
snapshot_right_joint_4_deg:
fresh_right_joint_4_deg:
right_joint_4_review_limit: [0, 135]
fresh_within_limit: true/false
drift_from_snapshot_deg:
read_path:
torque_enabled: false
actuator_commands_sent: false
send_action_called: false
motion_status: BLOCKED
next_blocker:
```

## Interpretation

If fresh `right_joint_4.pos` is still below `0 deg`, do not proceed. Report
that the first-write plan is blocked by the joint 4 limit/readback convention.

If fresh `right_joint_4.pos` is within `[0, 135]`, do not proceed to motion.
Capture a new Stage 32 snapshot and rerun A6000 review, because the previous
snapshot target table is stale.

In all cases, motion remains blocked.
