# Stage 34 Right Joint 4 Limit Check

Date: 2026-05-12

## Result

syhlabtop completed the Stage 34 read-only `right_joint_4.pos` limit check.

The fresh readback is inside the review/software limit, but it differs from the
accepted Stage 32 snapshot by about 12.5 degrees. Therefore the Stage 32
snapshot and the Stage 34 dry-run target table are stale.

Stage 35 actuator write remains blocked.

## syhlabtop Report

```text
repo_head: 3420dfb3563ce8ae313464cb618107f1588232dc
snapshot_right_joint_4_deg: -4.2293176683380596
fresh_right_joint_4_deg: 8.272851356413208
right_joint_4_review_limit: [0, 135]
fresh_within_limit: true
drift_from_snapshot_deg: 12.502169024751267
read_path: DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states() on can1 right arm; no OpenArmFollower.connect()
torque_enabled: false
actuator_commands_sent: false
send_action_called: false
motion_status: BLOCKED
next_blocker: Stage 32 snapshot and Stage 34 dry-run target table are stale. Capture a new Stage 32 snapshot and rerun A6000 no-send review before first-write planning.
```

syhlabtop artifact:

```text
/home/syhlabtop/openarm_folding_20260512/audits/stage34_right_joint4_limit_check_2026-05-12.md
```

## Interpretation

The earlier Stage 34 dry-run blocker was not caused by a current
`right_joint_4.pos` value that is persistently below the `[0, 135]` review
limit. The fresh readback is `8.272851356413208 deg`, which is inside the
limit.

However, the accepted Stage 32 snapshot used by the A6000 no-send review
recorded `right_joint_4.pos` as `-4.2293176683380596 deg`. The drift from that
snapshot is `12.502169024751267 deg`, so the old snapshot and all derived
artifacts must not be used for a first-write packet.

The stale artifacts are:

```text
snapshot_20260512_155652
snapshot_20260512_155652_action_review.csv
snapshot_20260512_155652_action_review.json
snapshot_20260512_155652_guarded_first_motion_dry_run.json
snapshot_20260512_155652_guarded_first_motion_dry_run.md
```

These artifacts remain useful as audit evidence only. They must not advance to
Stage 35.

## Next Step

Capture a fresh Stage 32 syhlabtop snapshot, transfer it to A6000, rerun the
A6000 no-send snapshot review, and regenerate the Stage 34 dry-run from the new
accepted snapshot.

Motion remains blocked.
