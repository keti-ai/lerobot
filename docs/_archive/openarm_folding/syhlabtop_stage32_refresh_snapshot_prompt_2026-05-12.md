# syhlabtop Stage 32 Refresh Snapshot Prompt

Date: 2026-05-12

Copy this prompt to the syhlabtop agent only after the operator confirms that
continuing no-motion diagnostics is acceptable.

---

You are the syhlabtop agent for the OpenArm folding Stage 32 refresh snapshot.

Do not move the robot. Do not run actuator write. Do not enable torque. Do not
zero. Do not run rollout, record, replay-to-robot, or `robot.send_action()`.

## Current Status

The previous Stage 32 snapshot was:

```text
snapshot_20260512_155652
```

It passed A6000 no-send review, but Stage 34 later found the snapshot is stale:

```text
snapshot_right_joint_4_deg: -4.2293176683380596
fresh_right_joint_4_deg: 8.272851356413208
drift_from_snapshot_deg: 12.502169024751267
fresh_within_limit: true
```

Therefore do not use the old `snapshot_20260512_155652` dry-run table for any
first-write planning.

Motion remains blocked.

## Goal

Create a fresh read-only Stage 32 snapshot bundle and transfer it to A6000 for
offline no-send review.

syhlabtop does not load the PI0.5 model. A6000 owns model inference.

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
- local PI0.5 model inference on syhlabtop
- copying `model.safetensors` to syhlabtop

## Steps

1. Sync repo:

```bash
cd /home/syhlabtop/workspace/lerobot
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
sed -n '1,220p' audits/openarm_folding/stage34_right_joint4_limit_check_2026-05-12.md
```

2. Use the same A6000-served snapshot architecture from:

```bash
sed -n '1,340p' audits/openarm_folding/syhlabtop_a6000_served_snapshot_handoff_prompt_2026-05-12.md
```

3. Create a new snapshot directory. Do not reuse `snapshot_20260512_155652`.

Expected layout:

```text
$SNAP/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

`state_16.csv` must use this exact order:

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

4. Transfer the fresh snapshot to A6000:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/<fresh-snapshot-id>/
```

5. Stop after transfer and report:

```text
repo_head:
architecture: syhlabtop_snapshot__a6000_inference
previous_snapshot: snapshot_20260512_155652
fresh_snapshot:
fresh_snapshot_path:
fresh_right_joint_4_deg:
right_joint_4_review_limit: [0, 135]
camera_mapping: PASS/FAIL
state_order_check: PASS/FAIL
snapshot_bundle: CREATED/NOT_CREATED
snapshot_transfer_to_a6000: DONE/BLOCKED/NOT_RUN
local_model_on_syhlabtop: NO
torque_enabled: false
actuator_commands_sent: false
send_action_called: false
motion_status: BLOCKED
next_blocker: A6000 no-send review required for fresh snapshot
artifact_paths:
```

The only acceptable `motion_status` is `BLOCKED`.

## A6000 Follow-Up

After the fresh snapshot transfer is complete, A6000 must rerun the no-send
snapshot review on the fresh snapshot and regenerate Stage 34 dry-run artifacts
from the fresh review outputs.

Do not proceed to Stage 35 from the old snapshot or from an unreviewed fresh
snapshot.
