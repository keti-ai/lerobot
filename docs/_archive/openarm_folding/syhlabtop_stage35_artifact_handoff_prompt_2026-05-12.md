# syhlabtop Stage 35 Artifact Handoff Prompt

Date: 2026-05-12

Copy this prompt to the syhlabtop agent only if the operator wants to continue
no-motion preparation for Stage 35.

---

You are the syhlabtop agent for Stage 35 artifact handoff.

This is not actuator execution. Do not move the robot.

## Current Status

Stage 34 no-send gates are complete for:

```text
snapshot: snapshot_20260512_171650
stage34_runtime_preflight: PASS
stage34_execution_packet_no_send: CREATED
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

## Goal

Provide the exact Stage 34 no-send packet artifacts to A6000 so that Stage 35
can be reviewed. This step only transfers or prints files and checksums.

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

## Required Files

Use these local syhlabtop files:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.md
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.md
```

## Steps

1. Sync repo:

```bash
cd /home/syhlabtop/workspace/lerobot
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
sed -n '1,220p' audits/openarm_folding/stage35_first_actuator_write_boundary_2026-05-12.md
```

2. Print checksums:

```bash
sha256sum \
  /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.json \
  /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.md \
  /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json \
  /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.md
```

3. Print the execution packet JSON header and rows. Do not execute anything:

```bash
sed -n '1,260p' /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json
```

4. Transfer the four files to A6000, if a transfer path is available:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage34_packets/snapshot_20260512_171650/
```

If direct transfer is not available, report the checksums and paste the packet
JSON rows.

5. Stop and report:

```text
repo_head:
snapshot:
runtime_preflight_json_sha256:
runtime_preflight_md_sha256:
execution_packet_json_sha256:
execution_packet_md_sha256:
execution_packet_path:
transfer_to_a6000: DONE/BLOCKED/NOT_RUN
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
next_blocker:
```

## Interpretation

If transfer succeeds, A6000 must verify the packet and draft the exact Stage 35
operator approval document.

If transfer is blocked, do not proceed. A6000 can only prepare Stage 35 after it
has the exact no-send packet contents and checksums.

Motion remains blocked in all cases.
