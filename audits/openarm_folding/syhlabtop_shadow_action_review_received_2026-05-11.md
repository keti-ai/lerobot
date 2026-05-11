# Syhlabtop Shadow Action Review Received

Date: 2026-05-11
Snapshot: `snapshot_20260511_135634`
Scope: no-motion/shadow review only.

## Source Artifacts

A6000/NAS source:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/snapshot_20260511_135634_action_review.csv
/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/snapshot_20260511_135634_action_review.json
```

Syhlabtop local received copy:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_135634_action_review.csv
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_135634_action_review.json
```

Checksums:

```text
7542511654c2124bade6047a3f7b91ae96b169d23fe21d41c20037db3605de9e  snapshot_20260511_135634_action_review.csv
c2c53b2545ab3122d82602b4c1adc8c775db46eebc5ddeaf431f607da8e1b06f  snapshot_20260511_135634_action_review.json
```

## A6000 Review Summary

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
review csv rows: 16
clamped rows: 4
max_abs_delta: 62.198 deg at action_id=0, right_joint_4.pos
```

All rows in the received CSV have `send_allowed=false`.

## First Action Review

The first action proposal is an offline policy output only. It has not been
sent to the robot.

```text
right_joint_1.pos  current=-1.759  proposed=-8.950   clamped=-8.950   delta=-7.190
right_joint_2.pos  current=-0.295  proposed=-9.005   clamped=-9.000   delta=-8.710   clamp
right_joint_3.pos  current=-0.973  proposed=-26.455  clamped=-26.455  delta=-25.483
right_joint_4.pos  current=-0.382  proposed=-62.581  clamped=0.000    delta=-62.198  clamp
right_joint_5.pos  current=2.481   proposed=-27.595  clamped=-27.595  delta=-30.076
right_joint_6.pos  current=-2.590  proposed=-15.201  clamped=-15.201  delta=-12.611
right_joint_7.pos  current=1.519   proposed=53.276   clamped=53.276   delta=51.756
right_gripper.pos  current=-18.458 proposed=-10.278  clamped=-10.278  delta=8.180
left_joint_1.pos   current=1.891   proposed=25.929   clamped=25.929   delta=24.039
left_joint_2.pos   current=-0.929  proposed=24.740   clamped=9.000    delta=25.669   clamp
left_joint_3.pos   current=-1.257  proposed=17.411   clamped=17.411   delta=18.668
left_joint_4.pos   current=0.142   proposed=-61.100  clamped=0.000    delta=-61.242  clamp
left_joint_5.pos   current=-0.645  proposed=21.777   clamped=21.777   delta=22.422
left_joint_6.pos   current=-6.940  proposed=-6.081   clamped=-6.081   delta=0.858
left_joint_7.pos   current=-5.082  proposed=-30.916  clamped=-30.916  delta=-25.834
left_gripper.pos   current=-4.098  proposed=-3.521   clamped=-3.521   delta=0.577
```

## Human Review Gate

Before any later motion gate, a human must review:

- camera orientation for `left_wrist`, `right_wrist`, and `base`;
- whether the first action proposal direction is plausible for the observed
  folding scene;
- clamp rows at `right_joint_2.pos`, `right_joint_4.pos`, `left_joint_2.pos`,
  and `left_joint_4.pos`;
- large deltas at `right_joint_4.pos`, `left_joint_4.pos`, and
  `right_joint_7.pos`;
- gripper proposed values as absolute degree targets.

Motion remains blocked. Do not run rollout, record, replay, or any path that
can call `send_action()` from this artifact.
