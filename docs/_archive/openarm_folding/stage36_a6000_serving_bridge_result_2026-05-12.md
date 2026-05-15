# Stage 36 A6000 Serving Bridge Result

Date: 2026-05-12

## Status

The corrected folding PI0.5 checkpoint is now served on A6000 through the
no-send snapshot policy server. syhlabtop captured a fresh post-Stage35
snapshot, transferred it to A6000, and requested one action proposal through
the HTTP bridge.

```text
a6000_model_server: RUNNING
server_url: http://10.252.205.103:8765/predict_snapshot
server_pid: 2702819
snapshot: snapshot_20260512_194042
proposal: PASS
all_finite: true
action_shape: [1, 30, 16]
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

The operator stated that robot movement is approved, but no robot command was
sent in Stage 36. The proposal was generated after that approval, so the exact
target table still needs a separate final confirmation before any actuator
write.

## A6000 Server

```text
model_dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
device: cuda:0
allowed_snapshot_root: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots
health: ok
```

Server log:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage36_a6000_snapshot_policy_server_20260512.log
```

## Snapshot

syhlabtop snapshot:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260512_194042/
```

A6000 snapshot:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260512_194042/
```

Snapshot checksums:

```text
state_16.csv: 23927871e7dcbcc8fb51f27d3a2e384c9f53fc899d924b472d88e7526ae00ba5
left_wrist.png: ba6e0d5155ffb71ba7682717539723ca2b72017519830a7e8ad0724bae09cdaf
right_wrist.png: 05b878211958f4e6b25840f521c022162122a12d973ef4f5da8561c1fa04acd6
base.png: 996f26e376acf0ce116d8f20d345776c876affbffc4516da3c7a57d5cec850e4
metadata.json: a322161b34ff7614f568ad0fc9ea18132cb8daecdfc578aca29ae062c6e9eb18
```

## Proposal Artifacts

syhlabtop:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_a6000_served_action_proposal.json
sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_a6000_served_action_proposal.md
sha256: 3159601cf434dd6e0299ca24ae66180ff64d637d8adb59c8cb8db11085afe04e
```

A6000:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage36_served_proposals/snapshot_20260512_194042/
```

The A6000 copies matched the syhlabtop checksums.

## Proposal Summary

```text
max_abs_arm_delta_deg: 2.1111412048339844
right_joint_4_delta_deg: 1.211517333984375
left_joint_4_delta_deg: -1.4297370910644531
right_joint_7_delta_deg: 2.1111412048339844
server_latency_ms: 1992.767095565796
```

Largest deltas:

| Key | Current deg | Proposed deg | Delta deg |
| --- | ---: | ---: | ---: |
| `right_gripper.pos` | 0.000000 | -21.427551 | -21.427551 |
| `left_gripper.pos` | -26.588966 | -22.597725 | 3.991241 |
| `right_joint_7.pos` | -4.032605 | -1.921464 | 2.111141 |
| `left_joint_7.pos` | 0.229498 | -1.549128 | -1.778625 |
| `left_joint_4.pos` | 5.234737 | 3.805000 | -1.429737 |
| `right_joint_4.pos` | 8.294708 | 9.506226 | 1.211517 |

## Boundary

Stage 36 proves the A6000 service path can return a no-send action proposal to
syhlabtop. It does not authorize direct policy rollout or robot write.

```text
stage36_a6000_serving_bridge: PASS
next_motion_target_table: DRAFTED_SEPARATELY
send_action: false
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```
