# Stage 16 Runtime Preflight Spec

Date: 2026-05-11
Scope: no-send runtime preflight only. This is not actuator execution.

## Purpose

Stage 15 created a capped dry-run target table from the refreshed
post-gripper-zero A6000 review. Stage 16 cannot use that table blindly because
the robot may have moved after the snapshot.

This preflight reads fresh follower-arm positions from CAN and compares them to
the Stage 15 dry-run reference values. If current drift is too large, the motion
candidate is stale and must be rejected before any command path is considered.

## Tool

```text
audits/openarm_folding/guarded_first_motion_runtime_preflight.py
```

This tool:

- reads the Stage 15 dry-run JSON;
- verifies its sha256;
- verifies `send_allowed=false` and `motion_allowed=false`;
- reads current positions with `DamiaoMotorsBus.connect(handshake=False)`;
- disconnects with `disable_torque=False`;
- compares fresh current readback against Stage 15 review current values;
- writes a no-send JSON report.

It does not enable torque, disable torque, write zero, write goals, call
`send_action`, rollout, record, replay, or run policy inference.

## Accepted Input

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_guarded_first_motion_dry_run.json
sha256: ce6c6efb2d6b2d7532500cb7b4ca61273993358ccd1ef437e4ae25781ee2cef3
```

Default drift limits:

```text
arm joints: <= 1 deg from Stage 15 review current value
grippers:   <= 3 deg from Stage 15 review current value
```

## Command

```bash
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/guarded_first_motion_runtime_preflight.py \
  --dry-run-json /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_guarded_first_motion_dry_run.json \
  --json-out /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_runtime_preflight.json
```

## Interpretation

If `all_within_drift_limit=false`, motion remains blocked and a new snapshot or
new dry-run plan is required.

If `all_within_drift_limit=true`, motion is still blocked. That result only
means the Stage 15 target table is not stale relative to the fresh readback.

## Verification

The runtime preflight was executed on `syhlabtop` with current follower CAN
readback only.

Result:

```text
timestamp: 20260511_161208
mode: runtime_preflight_no_send
send_allowed: false
motion_allowed: false
all_within_drift_limit: true
blocking_keys: []
arm_drift_limit_deg: 1.0
gripper_drift_limit_deg: 3.0
```

Output:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_runtime_preflight.json
sha256: e29ca7aa1ec00a124a0f141842b7efa1a01a8bbb45397ad6ade6f9db3dcc49aa
```

Largest observed arm drift was about `0.022 deg`; gripper drift was effectively
zero. `left_joint_7.pos` remained held in the Stage 15 target table.

A later actuator command stage would still need:

- explicit operator approval of the exact fresh-readback target table;
- a runtime flag absent by default;
- a typed confirmation string;
- a hold/abort procedure;
- logging of every sent target and post-send readback;
- a decision on whether `left_joint_7.pos` remains held.
