# Stage 35 No-Execute Writer Validation

Date: 2026-05-12

## Purpose

Prepare the Stage 35 validation path without creating any actuator-write path.
This is still no-motion preparation.

The actual actuator writer remains not ready. This stage only validates the
approved Stage 34 no-send execution packet and, on syhlabtop, can perform a
fresh read-only right-arm drift check.

## Tool

```text
audits/openarm_folding/stage35_no_execute_writer_validation.py
```

The tool has no `--execute` argument. It never enables torque, writes goals,
sends MIT commands, calls `send_action`, rollout, record, replay-to-robot, or
`OpenArmFollower.connect()`.

## Accepted Packet

```text
snapshot: snapshot_20260512_171650
packet: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage34_packets/snapshot_20260512_171650/snapshot_20260512_171650_execution_packet_no_send.json
packet_sha256: c5411331665ea5b31a9d85de4adf27ce74f0c9596630c4cc8481e6afd58ec259
dry_run_sha256: ef1501cad3dd3890955701d74c330e3393a1181fcbfbcba47a2a9d6100263fdc
runtime_preflight_sha256: 8b3d8df7db88eb8bdfaa9975e08cef3d91e9c0769312312cd2d969666b36d920
```

Packet flags must remain:

```text
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

## A6000 Packet-Only Validation

This validates the transferred packet and checksum without robot access:

```bash
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/probevenv/bin/python \
  audits/openarm_folding/stage35_no_execute_writer_validation.py \
  --packet-json /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage34_packets/snapshot_20260512_171650/snapshot_20260512_171650_execution_packet_no_send.json \
  --json-out /tmp/snapshot_20260512_171650_stage35_no_execute_packet_only.json \
  --md-out /tmp/snapshot_20260512_171650_stage35_no_execute_packet_only.md
```

This command does not read CAN.

Verification on A6000:

```text
packet_validation_passed: true
fresh_readback_validation_passed: null
execute_path_available: false
actual_writer_status: NOT_READY
```

Outputs:

```text
/tmp/snapshot_20260512_171650_stage35_no_execute_packet_only.json
/tmp/snapshot_20260512_171650_stage35_no_execute_packet_only.md
```

Negative checksum check:

```text
wrong expected packet checksum: rejected with non-zero exit status
```

## syhlabtop Fresh Read Validation

Only after operator approval for read-only CAN access, syhlabtop may run:

```bash
cd /home/syhlabtop/workspace/lerobot
PYTHONPATH=/home/syhlabtop/workspace/lerobot/src \
  /home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python \
  audits/openarm_folding/stage35_no_execute_writer_validation.py \
  --packet-json /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json \
  --read-fresh-current \
  --json-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json \
  --md-out /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.md
```

Allowed read path:

```text
DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states()
disconnect(disable_torque=False)
```

## Fixed Target Table

Selected joints:

```text
right_joint_1.pos
right_joint_2.pos
right_joint_3.pos
right_joint_4.pos
right_joint_5.pos
right_joint_6.pos
right_joint_7.pos
```

| Key | Packet current deg | Target deg | Delta deg |
| --- | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.469744 | -5.057898 | -0.588154 |
| `right_joint_2.pos` | -1.868768 | -1.801383 | 0.067385 |
| `right_joint_3.pos` | 14.611363 | 15.022029 | 0.410666 |
| `right_joint_4.pos` | 8.272851 | 8.502065 | 0.229214 |
| `right_joint_5.pos` | -3.092757 | -2.528544 | 0.564213 |
| `right_joint_6.pos` | -0.469924 | -0.612096 | -0.142172 |
| `right_joint_7.pos` | -4.229318 | -3.921798 | 0.307520 |

Expected max delta:

```text
0.5881538391113281 deg
```

## Current Boundary

```text
stage35_no_execute_validator: READY
stage35_a6000_packet_only_validation: PASS
stage35_actual_writer: NOT_READY
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

Actual Stage 35 actuator write still requires a separate explicit human
approval after the no-execute validation result is reviewed.
