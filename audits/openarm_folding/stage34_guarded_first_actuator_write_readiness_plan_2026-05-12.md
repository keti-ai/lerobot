# Stage 34 Guarded First Actuator Write Readiness Plan

Date: 2026-05-12

## Purpose

Stage 32 passed no-send A6000 snapshot review for
`snapshot_20260512_155652`. This does not authorize motion.

Stage 34 is the next no-motion gate before any guarded first actuator write.
It must convert the Stage 32 no-send action review into a fresh, capped,
operator-auditable dry-run packet.

## Inputs

Accepted Stage 32 snapshot:

```text
snapshot_20260512_155652
```

A6000 review artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.csv
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.json
```

Stage 32 review summary:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
max_first_action_arm_delta_deg: 1.3073272705078125 at right_joint_1.pos
right_joint_4_delta_deg: 0.7648124694824219
left_joint_4_delta_deg: -0.0755462646484375
right_joint_7_delta_deg: 0.4439506530761719
```

## Important Tooling Warning

The existing guarded first-motion scripts currently contain hardcoded approval
constants for the older `snapshot_20260511_154554` artifacts:

```text
audits/openarm_folding/guarded_first_motion_dry_run.py
audits/openarm_folding/guarded_first_motion_runtime_preflight.py
audits/openarm_folding/guarded_first_motion_execution_packet.py
audits/openarm_folding/guarded_first_motion_actuator_write.py
```

Do not run those scripts directly against `snapshot_20260512_155652` until the
approved snapshot id and artifact checksums are regenerated or the tools are
parameterized.

Using stale 2026-05-11 constants for a 2026-05-12 snapshot must remain blocked.

## Stage 34 Required Work

### 1. Regenerate or Parameterize Dry-Run Gate

Create a new no-send dry-run gate for:

```text
approved_snapshot_id: snapshot_20260512_155652
review_csv: snapshot_20260512_155652_action_review.csv
review_json: snapshot_20260512_155652_action_review.json
```

The gate must validate:

- CSV SHA256
- JSON SHA256
- `send_allowed=false`
- `all_finite=true`
- `action_shape=[1,30,16]`
- `obs_id=snapshot_20260512_155652`
- 16D action order

Default cap proposal:

```text
arm joints: <= 2 deg target delta from reviewed current value
grippers:   <= 5 deg target delta from reviewed current value
```

This cap is a dry-run cap only. It does not authorize motion.

### 2. Build Stage 34 Dry-Run JSON

Output target:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_155652_guarded_first_motion_dry_run.json
```

Required fields:

```text
mode: dry_run_only
send_allowed: false
motion_allowed: false
approved_snapshot_id: snapshot_20260512_155652
requires_separate_operator_motion_gate: true
```

### 3. Fresh Runtime Preflight

Before any actuator writer is considered, syhlabtop must read fresh current
state and compare it with the Stage 34 dry-run reference values.

Read path must remain:

```text
DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states()
```

Forbidden:

- torque enable
- zeroing
- calibration write
- goal write
- `send_action`
- rollout
- record
- replay

Default drift limits:

```text
arm joints: <= 1 deg from Stage 34 dry-run current value
grippers:   <= 3 deg from Stage 34 dry-run current value
```

Output target:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_155652_runtime_preflight.json
```

### 4. Execution Packet, Still No-Send

Only if fresh runtime preflight passes, build an execution packet with:

```text
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
requires_final_operator_motion_gate: true
```

Output target:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_155652_execution_packet_no_send.json
```

## Stage 35 Boundary

Actual actuator write is Stage 35, not Stage 34.

Stage 35 requires a separate explicit human approval with:

- exact command
- exact selected joints
- exact target table
- expected maximum delta
- operator at robot
- power/abort procedure
- e-stop readiness

The first actuator write must not be a full folding rollout. It must remain a
single guarded actuator-write test.

## Current Status

```text
stage32_snapshot_review: STALE_RECAPTURE_REQUIRED
stage34_right_joint4_limit_check: FRESH_READ_WITHIN_LIMIT
stage34_dry_run: STALE_BLOCKED
stage34_runtime_preflight: NOT_RUN
stage34_execution_packet: NOT_RUN
stage35_actuator_write: BLOCKED
motion_status: BLOCKED
```

## 2026-05-12 Dry-Run Update

Stage 34 dry-run was generated with:

```text
audits/openarm_folding/guarded_first_motion_dry_run_v2.py
```

Output:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.json
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.md
```

Result:

```text
send_allowed: false
motion_allowed: false
stage35_candidate_ready: false
blocking_first_write_keys: ["right_joint_4.pos"]
```

The blocker is that `right_joint_4.pos` current value was below the review
limit min. Applying the 2 degree cap did not bring the proposed target into the
review limit range.

Do not run Stage 35 from this dry-run table.

## 2026-05-12 Right Joint 4 Fresh Read Update

syhlabtop ran the no-motion Stage 34 right-joint-4 read-only check:

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
```

This means `right_joint_4.pos` is currently within the review limit, but the
accepted Stage 32 snapshot and the Stage 34 dry-run table are stale. The next
step is to capture a fresh Stage 32 snapshot and rerun the A6000 no-send review
before regenerating Stage 34 artifacts.

Use:

```text
audits/openarm_folding/stage34_right_joint4_limit_check_2026-05-12.md
audits/openarm_folding/syhlabtop_stage32_refresh_snapshot_prompt_2026-05-12.md
```

## 2026-05-12 Fresh Snapshot 171650 Update

The stale `snapshot_20260512_155652` path was restarted with:

```text
snapshot_20260512_171650
```

A6000 review passed:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
```

Stage 34 dry-run for `snapshot_20260512_171650` also passed for no-send
planning:

```text
max_abs_right_arm_candidate_delta_deg: 0.588154
right_arm_candidate_targets_within_review_limits: true
send_allowed: false
motion_allowed: false
```

syhlabtop then completed the Stage 34 runtime preflight and no-send execution
packet:

```text
stage34_runtime_preflight: PASS
stage34_execution_packet_no_send: CREATED
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

The reported syhlabtop packet artifacts are:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.md
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.md
```

These packet files are not yet present under the A6000 work root. The next
no-motion step is to transfer or print the packet files and checksums for A6000
review.

Use:

```text
audits/openarm_folding/stage35_first_actuator_write_boundary_2026-05-12.md
audits/openarm_folding/syhlabtop_stage35_artifact_handoff_prompt_2026-05-12.md
```
