# Stage 18 Guarded Actuator Write Spec

Date: 2026-05-11
Scope: one guarded right-arm actuator write path.

## Purpose

Stage 18 adds the first actuator writer, but keeps it constrained to one capped
right-arm step from the Stage 17 packet. It does not run policy inference,
rollout, replay, record, camera capture, or live A6000 streaming.

## Tool

```text
audits/openarm_folding/guarded_first_motion_actuator_write.py
```

Default mode is dry-run readback validation only.

The writer does not call `OpenArmFollower.connect()`. It uses direct
`DamiaoMotorsBus.connect(handshake=False)` on `can1` so it does not run
calibration, set zero, configure motors, or connect cameras.

## Fixed First-Write Scope

Selected motors:

```text
can1 right arm only
joint_1
joint_2
joint_3
joint_4
joint_5
joint_6
joint_7
```

Excluded:

```text
left arm
right_gripper
left_gripper
left_joint_7 special handling remains held/excluded
```

Targets are loaded from the accepted Stage 17 packet:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_execution_packet_no_send.json
sha256: e2627900430cda3aac90739babb35cc0ba7df8b19a89d3704ea8545505187d2f
```

## Gates

Dry-run command:

```bash
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src:audits/openarm_folding \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/guarded_first_motion_actuator_write.py \
  --packet-json /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_execution_packet_no_send.json \
  --json-out /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_stage18_dry_run.json
```

Execute command, only when the operator is physically holding power/abort:

```bash
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src:audits/openarm_folding \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/guarded_first_motion_actuator_write.py \
  --packet-json /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_execution_packet_no_send.json \
  --execute \
  --power-held \
  --confirm SEND_RIGHT_ARM_JOINTS_ONCE_20260511 \
  --json-out /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_stage18_execute.json
```

The execute path refuses to run unless all of these are true:

- packet sha256 matches the accepted Stage 17 packet;
- selected rows are exactly right arm `joint_1` to `joint_7`;
- every packet row still has `would_send=false`;
- fresh readback drift from packet fresh value is `<=1 deg`;
- target delta from fresh readback is `<=2 deg`;
- targets are within right-arm default limits;
- `--execute`, `--power-held`, and exact confirmation phrase are provided.

## Write Sequence

If all gates pass:

1. Connect `can1` with `handshake=False`.
2. Read selected joint positions.
3. Enable torque for selected right-arm joints only.
4. Send one MIT control batch using OpenArm default position gains.
5. Read back immediately.
6. Hold for `1.0s`.
7. Read back again.
8. Disable selected right-arm joints.
9. Final readback and JSON log.

On exception or interrupt after execute starts, the script best-effort disables
the selected right-arm joints and logs the failure.

## Dry-Run Verification

The Stage 18 writer dry-run was executed with no actuator write:

```text
timestamp: 20260511_163228
mode: stage18_guarded_right_arm_write
execute_requested: false
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
port: can1
selected_motors: joint_1..joint_7
excluded: left_arm, right_gripper, left_gripper
```

Output:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_stage18_dry_run.json
sha256: c300381df2ac5d7fc93123a9bb2168bed28f7e475bb7b7dfed9dcc3e9fdbb8ad
```

Validated targets:

| Motor | Fresh deg | Target deg | Delta deg | Drift deg |
| --- | ---: | ---: | ---: | ---: |
| `joint_1` | -1.126 | -3.126 | -2.000 | 0.000 |
| `joint_2` | -0.295 | -2.295 | -2.000 | 0.000 |
| `joint_3` | 13.540 | 11.540 | -2.000 | 0.000 |
| `joint_4` | 0.361 | 0.000 | -0.361 | 0.000 |
| `joint_5` | -3.093 | -5.071 | -1.978 | -0.022 |
| `joint_6` | -0.426 | -2.426 | -2.000 | 0.000 |
| `joint_7` | 5.978 | 7.978 | 2.000 | 0.000 |

All dry-run rows validated within `1 deg` drift and `2 deg` target delta.

## After First Write

After any successful execute, do not run another write from the same packet.
Capture a new no-send snapshot, send it to A6000, run offline review, and rebuild
Stage 15/16/17 artifacts before considering a second motion.
