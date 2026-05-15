# Stage 40 No-Send Readiness

Date: 2026-05-13

## Status

```text
stage40_fresh_snapshot: DONE
stage40_a6000_no_send_proposal: PASS
stage40_no_execute_validation: PASS
stage40_actual_write: DONE
stage40_result: audits/openarm_folding/stage40_actual_write_result_2026-05-13.md
motion_status: BLOCKED_FOR_REVIEW
next_motion_approval: NOT_GIVEN
```

No rollout, recording, replay-to-robot, `send_action`, local PI0.5 inference,
zeroing, calibration write, left-arm command, gripper command, torque enable,
or actuator write was run.

## Snapshot

```text
snapshot: snapshot_20260513_152125
local_path: /home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260513_152125/
a6000_path: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260513_152125/
scene_note: stage40_fresh_post_stage39
```

The snapshot capture reported one right gripper packet drop and used the last
known gripper state. Arm joint state and all three images were recorded.

Snapshot checksums:

```text
state_16.csv: 44abbf40bdcf0aabefdc9371bb88c6387817bca7a18a42de7888659bf7b7411f
left_wrist.png: a56f9beb200ae7d01700b3d9919537a166a3b85e0bbb93e324cda4b7b6e35397
right_wrist.png: 0011e19b9b1e3752046e7b8bbc354ca9dc2194ef8a3fd5133e024198006942e4
base.png: b43b5fcf1ec92aec7c264512c5629b096599cf978d45cb6521e34495913cc9f9
metadata.json: 3aeb8ac8eac543c1568dd20c241b454da02f2ba994ce08cdbe50fd4c373da527
```

## A6000 Proposal

```text
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_a6000_served_action_proposal.json
proposal_sha256: b600f8380260c21f101453a499325409a460ad9129c5ca38d986df92af86efab
proposal_md_sha256: 8ddbf8151d6975f38e3f04afe939ebd075db6deb0d5d507e5abaca36f194a813
```

```text
all_finite: true
action_shape: [1, 30, 16]
max_abs_arm_delta_deg: 1.4891548156738281
right_joint_4_delta_deg: 1.4891548156738281
right_joint_7_delta_deg: -0.11715316772460938
left_joint_4_delta_deg: 1.0674400329589844
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
```

All selected right-arm proposal deltas were within the 2 degree cap, so the
Stage 40 target table uses the A6000 right-arm proposal directly.

## No-Execute Validation

```text
proposal_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_target_delta_from_fresh_deg: 1.4891547267763565
max_abs_drift_from_proposal_current_deg: 0.00000019852152810528878
```

Readiness artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_ready_no_send.json
sha256: faabc718827bb6f27fb4ca961f4077c4de6fd3e59368f11f20f19ca813de95d4

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_152125_stage40_ready_no_send.md
sha256: 9d10294e84f0344811c03e570d860805073fba0a13f514dd9903b7ebe82d6f18
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage40_served_proposal_write/snapshot_20260513_152125/
```

The A6000 copies matched the syhlabtop checksums.

## Final Target Table

| Key | Fresh current deg | A6000 proposed deg | Proposal delta deg | Draft target deg | Draft delta from fresh deg |
| --- | ---: | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -3.835893 | -4.051618 | -0.215725 | -4.051618 | -0.215725 |
| `right_joint_2.pos` | 0.666637 | 1.116878 | 0.450241 | 1.116878 | 0.450241 |
| `right_joint_3.pos` | 14.676934 | 15.215549 | 0.538614 | 15.215549 | 0.538614 |
| `right_joint_4.pos` | 6.677295 | 8.166450 | 1.489155 | 8.166450 | 1.489155 |
| `right_joint_5.pos` | -3.529896 | -3.685856 | -0.155960 | -3.685856 | -0.155960 |
| `right_joint_6.pos` | 4.863169 | 4.412115 | -0.451054 | 4.412115 | -0.451054 |
| `right_joint_7.pos` | -1.256774 | -1.373927 | -0.117153 | -1.373927 | -0.117153 |

## Boundary

```text
stage40_no_execute_validation: PASS
stage40_actual_write: DONE
stage40_result: audits/openarm_folding/stage40_actual_write_result_2026-05-13.md
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
