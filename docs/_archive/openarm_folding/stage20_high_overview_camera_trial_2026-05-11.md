# Stage 20 High-Overview Camera Trial

Date: 2026-05-11
Scope: no-send diagnosis after raising the base camera on a temporary jig.

## Hardware Modification Track

The Hugging Face hardware modification files for the folding project were
downloaded to:

```text
/home/syhlabtop/openarm_folding_20260511/hardware_modifications/
```

Files:

```text
J3-J4_Cover_back_extended.stl   sha256 a3b8fd1dcb0e72abdc4d7b6a3667162a798fbd7c4f954eaab63d9c99a44efb23
J3-J4_Cover_front_extended.stl  sha256 b2bb0cf3c0d5fa95bcf1fb684e6e810fe4cb8c25310434fa8c41e122d43884c1
J4_5cm_extended.step            sha256 a533f60a3b8228267f417df58e81e1a4c6e1c4274a50ddfa2151c71f92a82beb
README.md                       sha256 85e0caa47ccd8399196008a32778faefd494912c02a9bce4490fcfab1cc6f861
arducam_holder.step             sha256 b51c4d565afe4a632c61af15b42a9319c9361271c98840ccd9c670a893b7291d
arducam_holder.stl              sha256 1d31e0ac9ac2b118fb0925dc45bb3736dff087a9e6c2f9c27e64b24ee488074c
head_camera_holder_v4.stl       sha256 959ae5e0ad6e0870465e361df30db3d1bbdeebb9ba8001274c3ce9e1712f03d3
jaw_normal.stl                  sha256 6ae41c9fbba411333954b8f4d1c6867b61fad1be7d7b936899c27d43410a2137
```

These parts were not installed for the snapshot below. The current robot remains
the standard OpenArm physical embodiment with a temporary high base camera jig.

## Camera Trial Snapshot

The base camera was changed from the previous D435 chest camera to a raised
D435I:

```text
base serial: 213622075840
device: Intel RealSense D435I
source_alias: high_overview_d435i
base_extrinsic_trial: high_overview_like_full_folding_25cm_jig
```

Snapshot:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_175613/
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_175613.tar.gz
sha256 eb509a1734b27fa84cbf968f6a11bdc119fc95708cc74d5de0712ac72c140204
```

Transferred to A6000 and NAS:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260511_175613.tar.gz
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/snapshot_20260511_175613.tar.gz
sha256 eb509a1734b27fa84cbf968f6a11bdc119fc95708cc74d5de0712ac72c140204
```

No policy output was computed on syhlabtop. No torque enable, zero write, goal
write, `send_action`, rollout, record, or replay was used.

Note: the right gripper CAN read reported a packet drop and used last-known
state `0.0 deg`. This makes the gripper row less diagnostic, but the arm rows
remain usable for camera/embodiment comparison.

## A6000 Offline Review

Artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_175613_action_review.csv
sha256 7b38469fe55d01b422780ea4214503cb53d5e77d5cb91674b4b4941744c5ff14

/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_175613_action_review.json
sha256 af334266f1af27d9e5fd8f7c51582a21e121cefebc03ad9037b7d43ec4958efe

/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_175613_action_review.csv
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_175613_action_review.json
```

Review result:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
rows: 16
clamped_rows: 4
mean_abs_delta: 26.593 deg
max_abs_delta: 72.753 deg at right_joint_4.pos
```

Clamped rows:

```text
right_joint_2.pos  proposed -11.299 -> clamped -9.000
right_joint_4.pos  proposed -76.982 -> clamped 0.000
left_joint_2.pos   proposed 20.859 -> clamped 9.000
left_joint_4.pos   proposed -54.381 -> clamped 0.000
```

## Comparison with Previous Post-Gripper-Zero Review

Previous chest/base review:

```text
snapshot_20260511_154554
mean_abs_delta: 25.462 deg
max_abs_delta: 67.930 deg at right_joint_4.pos
clamped_rows: 4
```

High-overview D435I review:

```text
snapshot_20260511_175613
mean_abs_delta: 26.593 deg
max_abs_delta: 72.753 deg at right_joint_4.pos
clamped_rows: 4
```

Per-row comparison:

```text
right_joint_1.pos  old_delta= -7.280 new_delta= -8.317
right_joint_2.pos  old_delta= -9.255 new_delta=-10.086
right_joint_3.pos  old_delta=-20.782 new_delta=-23.196
right_joint_4.pos  old_delta=-67.930 new_delta=-72.753
right_joint_5.pos  old_delta=-28.884 new_delta=-29.323
right_joint_6.pos  old_delta=-12.784 new_delta=-13.772
right_joint_7.pos  old_delta= 47.306 new_delta= 52.937
left_joint_1.pos   old_delta= 23.998 new_delta= 22.778
left_joint_2.pos   old_delta= 24.340 new_delta= 24.476
left_joint_3.pos   old_delta= 20.601 new_delta= 20.712
left_joint_4.pos   old_delta=-58.376 new_delta=-59.616
left_joint_5.pos   old_delta= 23.614 new_delta= 25.796
left_joint_6.pos   old_delta= -0.891 new_delta=  0.131
left_joint_7.pos   old_delta=-26.089 new_delta=-30.511
left_gripper.pos   old_delta= 22.311 new_delta= 22.018
```

## Decision

Raising the base camera alone did not reduce the large raw action deltas. The
new base image is closer to the `full_folding` overview framing, but the policy
still proposes large bimanual arm moves and the same four clamp rows.

This makes "base camera too low" insufficient as the sole cause. Remaining
high-priority causes:

1. embodiment mismatch from the folding hardware modifications, especially the
   +5 cm J4 extension and custom gripper jaw;
2. wrist camera/task-signal mismatch, since wrist views still mostly show
   gripper/frame/cables rather than cloth;
3. action/state contract details, including right gripper read reliability and
   any dataset-specific preprocessing assumptions.

Do not build a Stage 19 write packet from `snapshot_20260511_175613`. Motion
remains blocked.
