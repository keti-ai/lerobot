# Stage 39 No-Send Readiness

Date: 2026-05-13

## Status

```text
stage39_fresh_snapshot: DONE
stage39_a6000_no_send_proposal: PASS
stage39_no_execute_validation: PASS
stage39_actual_write: DONE
stage39_result: audits/openarm_folding/stage39_actual_write_result_2026-05-13.md
motion_status: BLOCKED_FOR_REVIEW
```

No rollout, recording, replay-to-robot, `send_action`, local PI0.5 inference,
zeroing, calibration write, left-arm command, gripper command, torque enable,
or actuator write was run.

## Snapshot

```text
snapshot: snapshot_20260513_150206
local_path: /home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260513_150206/
a6000_path: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260513_150206/
```

The snapshot capture reported one right gripper packet drop and used the last
known gripper state. Arm joint state and all three images were recorded.

Snapshot checksums:

```text
state_16.csv: 1d154d689b3674e16e0b405f6ea46064da42766cbfd24dae69af2ff4635c142f
left_wrist.png: e1102c883e772b6af50ea31f50d21b1ad41cc5233c237f9208abff25790ae81b
right_wrist.png: 5ea0d05ccdac536614af228727587b66209368ebb7955105bcadde3b3be5aec9
base.png: 328decf84c38914b6811563cd19c4473b5e212b0ab07b7f314b646e5df91910e
metadata.json: f1264b904244d82646434b2570216379a9db1d19e1ee3ea41342f8be2ae2f153
```

## A6000 Proposal

```text
proposal_json: /home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_a6000_served_action_proposal.json
proposal_sha256: e4ef68ec4acb02d05679988ce7c026531e6a697b34ae0724be2bd3b734b06854
proposal_md_sha256: e136d9e65950e281dac4af18c3a7200e8c72a64456c792bd5b756a1fc5db83f3
```

```text
all_finite: true
action_shape: [1, 30, 16]
max_abs_arm_delta_deg: 1.4376983642578125
right_joint_4_delta_deg: -1.0605735778808594
right_joint_7_delta_deg: 0.22760581970214844
left_joint_4_delta_deg: -1.4376983642578125
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
```

All selected right-arm proposal deltas were within the 2 degree cap, so the
Stage 39 target table uses the A6000 right-arm proposal directly.

## No-Execute Validation

```text
proposal_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_target_delta_from_fresh_deg: 1.0824308091758805
max_abs_drift_from_proposal_current_deg: 0.02185723129502115
```

Readiness artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_ready_no_send.json
sha256: 664488cd2405eb779bea7990d40edd05082b696a1ba7525b47a4418922c46ebe

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260513_150206_stage39_ready_no_send.md
sha256: d41a2406e91a91749c42a900266d6bfea8d5ebf0e99e9baa3ad4a7d63759d2cf
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage39_served_proposal_write/snapshot_20260513_150206/
```

The A6000 copies matched the syhlabtop checksums.

## Final Target Table

| Key | Fresh current deg | A6000 proposed deg | Proposal delta deg | Draft target deg | Draft delta from fresh deg |
| --- | ---: | ---: | ---: | ---: | ---: |
| `right_joint_1.pos` | -4.491601 | -4.036126 | 0.455475 | -4.036126 | 0.455475 |
| `right_joint_2.pos` | -1.344202 | -0.759507 | 0.584695 | -0.759507 | 0.584695 |
| `right_joint_3.pos` | 15.048502 | 14.538319 | -0.510183 | 14.538319 | -0.510184 |
| `right_joint_4.pos` | 8.622562 | 7.540132 | -1.060574 | 7.540132 | -1.082431 |
| `right_joint_5.pos` | -3.529896 | -3.479749 | 0.050146 | -3.479749 | 0.050146 |
| `right_joint_6.pos` | -0.251355 | 0.348044 | 0.599399 | 0.348044 | 0.599399 |
| `right_joint_7.pos` | -1.060062 | -0.832456 | 0.227606 | -0.832456 | 0.227606 |

## Boundary

```text
stage39_no_execute_validation: PASS
stage39_actual_write: DONE
stage39_result: audits/openarm_folding/stage39_actual_write_result_2026-05-13.md
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
