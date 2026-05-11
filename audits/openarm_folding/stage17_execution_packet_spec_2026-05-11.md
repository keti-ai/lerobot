# Stage 17 Execution Packet Spec

Date: 2026-05-11
Scope: no-send execution packet only. This is not actuator execution.

## Purpose

Stage 17 starts the guarded execution path by building the exact target packet
that a later actuator writer would consume. This stage still sends nothing.

The packet builder validates:

- the accepted Stage 15 dry-run JSON checksum;
- the accepted Stage 16 runtime preflight JSON checksum;
- `send_allowed=false`;
- `motion_allowed=false`;
- `all_within_drift_limit=true` in the Stage 16 preflight;
- a fresh CAN readback at packet-build time;
- the same 1 deg arm / 3 deg gripper drift limits.

Every output row keeps:

```text
would_send: false
send_block_reason: stage17_execution_not_enabled
```

## Tool

```text
audits/openarm_folding/guarded_first_motion_execution_packet.py
```

This tool reads current CAN state with `handshake=False`, but does not enable
torque, disable torque, write zero, write goals, call `send_action`, rollout,
record, replay, or run policy inference.

The confirmation phrase for this no-send packet is:

```text
I_UNDERSTAND_THIS_IS_STILL_NO_SEND
```

This phrase is intentionally not a motion approval. It only permits packet
generation.

## Command

```bash
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/guarded_first_motion_execution_packet.py \
  --dry-run-json /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_guarded_first_motion_dry_run.json \
  --preflight-json /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_runtime_preflight.json \
  --confirm I_UNDERSTAND_THIS_IS_STILL_NO_SEND \
  --json-out /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_execution_packet_no_send.json
```

## Remaining Blockers Before Any Actuator Write

## Verification

The no-send execution packet was generated on `syhlabtop`:

```text
timestamp: 20260511_161738
mode: stage17_execution_packet_no_send
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
requires_final_operator_motion_gate: true
requires_hold_abort_procedure: true
requires_new_code_for_actuator_write: true
```

Output:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_execution_packet_no_send.json
sha256: e2627900430cda3aac90739babb35cc0ba7df8b19a89d3704ea8545505187d2f
```

All rows have:

```text
would_send: false
send_block_reason: stage17_execution_not_enabled
```

The generated packet target deltas remain bounded by the Stage 15 caps:

```text
arm joints: <= 2 deg from fresh readback
grippers:   <= 5 deg from fresh readback
left_joint_7.pos: held
```

## Remaining Blockers Before Any Actuator Write

- There is no actuator writer in this stage.
- There is no final operator motion gate.
- There is no hold-to-run or abort procedure.
- There is no post-send readback logger.
- `left_joint_7.pos` remains held from Stage 15.
- The command path still needs a deliberate decision about whether to command
  both arms together or start with a smaller subset.

Motion remains blocked after this stage.
