# Stage 21 Action Contract Diagnosis

Dataset rows: 1505
Feature count: 16

## Decision

The large first-step deltas are not explained by the dataset action contract.
For `lerobot/full_folding` episode 0, arm joint `action - observation.state`
deltas are normally small: representative p99 values are about `2.45 deg` for
`right_joint_7`, `3.39 deg` for `right_joint_4`, `3.21 deg` for `left_joint_4`,
and `4.85 deg` for `left_joint_7`. The syhlabtop snapshots contain 20-70 deg
deltas, all at the 100th percentile of the dataset comparison.

The PI0.5 relative-to-absolute postprocessor is functioning as configured:
`absolute = unnormalized_relative + cached_state` for arm joints, with zero
reconstruction error for both tested snapshots. This rules out the local
postprocessor pairing as the immediate cause.

Motion remains blocked. Do not generate a Stage 19 write packet from either
`snapshot_20260511_154554` or `snapshot_20260511_175613`.

Most likely next causes:

```text
1. current ready/zero pose is outside or near the edge of the training state distribution;
2. wrist/base visual inputs are still off-distribution enough to produce abnormal relative actions;
3. state/action feature order or side semantics may still be wrong before policy input, despite matching names;
4. gripper read reliability remains unresolved for snapshot_20260511_175613.
```

## Snapshot Summary

- `chest_154554`: mean_abs_delta=25.462, max_abs_delta=67.930 at `right_joint_4.pos`
- `high_175613`: mean_abs_delta=26.593, max_abs_delta=72.753 at `right_joint_4.pos`

## Postprocess Check

- `chest_154554`: max reconstruction error 0.000000 deg; full postprocess error 0.000000 deg
- `high_175613`: max reconstruction error 0.000000 deg; full postprocess error 0.000000 deg

## Highest Snapshot Delta Percentiles

- `high_175613` `right_joint_4.pos` delta=-72.753 deg, abs percentile=100.0, state percentile=0.0, state_outside_minmax=True
- `chest_154554` `right_joint_4.pos` delta=-67.930 deg, abs percentile=100.0, state percentile=0.0, state_outside_minmax=True
- `high_175613` `left_joint_4.pos` delta=-59.616 deg, abs percentile=100.0, state percentile=1.0, state_outside_minmax=False
- `chest_154554` `left_joint_4.pos` delta=-58.376 deg, abs percentile=100.0, state percentile=0.0, state_outside_minmax=True
- `high_175613` `right_joint_7.pos` delta=52.937 deg, abs percentile=100.0, state percentile=95.9, state_outside_minmax=False
- `chest_154554` `right_joint_7.pos` delta=47.306 deg, abs percentile=100.0, state percentile=98.7, state_outside_minmax=False
- `high_175613` `left_joint_7.pos` delta=-30.511 deg, abs percentile=100.0, state percentile=9.0, state_outside_minmax=False
- `high_175613` `right_joint_5.pos` delta=-29.323 deg, abs percentile=100.0, state percentile=0.0, state_outside_minmax=True
- `chest_154554` `right_joint_5.pos` delta=-28.884 deg, abs percentile=100.0, state percentile=0.0, state_outside_minmax=True
- `chest_154554` `left_joint_7.pos` delta=-26.089 deg, abs percentile=100.0, state percentile=7.1, state_outside_minmax=False
- `high_175613` `left_joint_5.pos` delta=25.796 deg, abs percentile=100.0, state percentile=93.4, state_outside_minmax=False
- `high_175613` `left_joint_2.pos` delta=24.476 deg, abs percentile=100.0, state percentile=66.5, state_outside_minmax=False
- `chest_154554` `left_joint_2.pos` delta=24.340 deg, abs percentile=100.0, state percentile=76.5, state_outside_minmax=False
- `chest_154554` `left_joint_1.pos` delta=23.998 deg, abs percentile=100.0, state percentile=15.1, state_outside_minmax=False
- `chest_154554` `left_joint_5.pos` delta=23.614 deg, abs percentile=100.0, state percentile=81.8, state_outside_minmax=False
- `high_175613` `right_joint_3.pos` delta=-23.196 deg, abs percentile=100.0, state percentile=17.2, state_outside_minmax=False
- `high_175613` `left_joint_1.pos` delta=22.778 deg, abs percentile=100.0, state percentile=15.5, state_outside_minmax=False
- `chest_154554` `left_gripper.pos` delta=22.311 deg, abs percentile=100.0, state percentile=21.4, state_outside_minmax=False
- `high_175613` `left_gripper.pos` delta=22.018 deg, abs percentile=100.0, state percentile=21.5, state_outside_minmax=False
- `chest_154554` `right_joint_3.pos` delta=-20.782 deg, abs percentile=100.0, state percentile=17.0, state_outside_minmax=False
