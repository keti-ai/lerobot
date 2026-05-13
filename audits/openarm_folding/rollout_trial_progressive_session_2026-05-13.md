# Rollout Trial Progressive Session

Date: 2026-05-13

## Status

```text
previous_position: Stage40 actual write DONE
next_axis: rollout_trial_<YYYYMMDD_HHMMSS>
new_stage_numbers: forbidden
motion_status: BLOCKED_FOR_REVIEW
session_envelope_approval: NOT_GIVEN
```

This document replaces numbered Stage expansion for rollout entry. All new
rollout artifacts must live under a `rollout_trial_<timestamp>/` root.

## Boundary

Hard boundaries for this phase:

```text
right_arm_7_joints_only: true
left_arm_commands: forbidden
gripper_commands: forbidden
send_action_path: forbidden
lerobot_rollout_actual_path: forbidden
openarm_follower_connect_actual_path: forbidden
actuator_path: DamiaoMotorsBus.connect(handshake=False) + guarded MIT batch
torque_enable_scope: selected right-arm joints only
```

Hard gates:

```text
finite_action: required
schema_check: required
proposal_checksum_and_obs_id_check: required
snapshot_checksum_check: required
joint_limit_check: required
metadata_sanity_check: robot_config_id, joint_order, action_units, checkpoint_id, action_normalization_id
excluded_joint_command_attempt: hard block
```

The old 20 degree mismatch diagnosis is not a rollout hard gate. It has been
replaced by the lightweight metadata sanity checks above plus normal action
finite/limit/cap checks.

## A6000 Proposal Schema

The no-send A6000 server keeps backward compatibility and adds full chunk
fields:

```text
predicted_abs_action: first absolute 16D action
predicted_abs_action_chunk: full [1, 30, 16] absolute action chunk
model_id
checkpoint_id
robot_config_id
action_normalization_id
action_space_version
joint_order
action_units
is_absolute_action: true
inference_timestamp
obs_id
snapshot_checksum
```

The server remains no-send:

```text
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
```

## Session Envelope

Manual approval is session-envelope based, not exact-table based. The envelope
covers:

```text
rollout_trial_id
model_id/checkpoint_id/robot_config_id/action_normalization_id
selected_features: right_joint_1.pos through right_joint_7.pos
max_risk_level
max_session_duration_s
max_chunks
max_actions_per_chunk
max_per_step_delta_cap_deg
max_total_joint_delta_per_session_deg
readback_soft_error_deg
readback_hard_error_deg
forbidden command paths and excluded joints
```

Exact target tables are still written before each chunk executes. They do not
require new manual approval while they remain inside the approved envelope.

## Risk Levels

```text
Level 0: no-execute only
Level 1: 3 actions or 2 sec, cap 2.0 deg
Level 2: 10 actions or 5 sec, cap 4.0 deg
Level 3: 30 actions or 10 sec, cap 6.0 deg
Level 4: up to 3 chunks initially, cap 8.0 deg, optional ceiling 10.0 deg after stable readback
```

Promotion requires stable readback, valid right-arm-only targets, no camera or
state failures, no A6000 health failure, no operator stop, no excluded joint
command, and no command path violation.

Readback thresholds:

```text
soft: 1.0 deg
hard: 2.0 deg
```

State machine:

```text
BLOCKED_FOR_REVIEW
ARMED_FOR_ROLLOUT_SESSION
ROLLOUT_SESSION_ACTIVE
PAUSED_SOFT_REVIEW
BLOCKED_FOR_REVIEW
```

Use `PAUSED_SOFT_REVIEW` for recoverable issues. Use `BLOCKED_FOR_REVIEW` for
hard safety or integrity violations.

## Artifact Layout

```text
rollout_trial_<timestamp>/
  metadata.json
  session/
    session_envelope_approval_draft.md
    session_envelope_approval.json
    session_summary.json
    session_summary.md
    chunk_000/
      snapshot/
      proposal.json
      proposal.md
      no_execute_validation.json
      no_execute_validation.md
      exact_target_table.json
      exact_target_table.md
      actual_execution.json
      actual_execution.md
      readback.json
      readback.md
```

## Implemented Tools

```text
audits/openarm_folding/a6000_snapshot_policy_server.py
  Adds full chunk and metadata fields to no-send proposals.

audits/openarm_folding/syhlabtop_snapshot_policy_client.py
  Adds local snapshot checksum to the request and proposal artifact.

audits/openarm_folding/rollout_trial_guarded_session.py
  Validates proposal chunks, writes envelope drafts, plans right-arm-only
  guarded command steps, supports Level 2+ interpolation, and can execute only
  with session-envelope approval flags.
```

## Next Operator-Gated Work

1. Restart or refresh the A6000 server so it serves the new full-chunk schema.
2. Capture a fresh rollout trial snapshot.
3. Request a fresh A6000 proposal.
4. Run no-execute validation and write the session envelope draft.
5. Obtain operator approval for the envelope.
6. Execute the guarded progressive session only inside that envelope.

No actual rollout is authorized by this document.
