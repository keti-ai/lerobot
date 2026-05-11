# Stage 24 Normalized Target Probe

## Decision

The loaded model's raw normalized output does not match the normalized target computed from
`recorded_action - observation.state` using the checkpoint action quantiles. This confirms
that the current A6000 `folding_latest` runtime path is not reproducing dataset behavior before
any robot-specific input is involved.

Motion remains blocked.

## Frame Summary

- frame `0`: mean_abs_raw_error=0.680, max_abs_raw_error=1.518 at `right_joint_4.pos`
- frame `1`: mean_abs_raw_error=0.673, max_abs_raw_error=1.483 at `right_joint_4.pos`

## Worst Rows

### Frame 0
- `right_joint_4.pos` raw=-3.056, target=-1.538, error=-1.518, recorded_delta=0.109 deg
- `right_joint_7.pos` raw=2.053, target=0.802, error=1.251, recorded_delta=0.011 deg
- `left_joint_4.pos` raw=-2.545, target=-1.366, error=-1.179, recorded_delta=0.051 deg
- `left_joint_2.pos` raw=1.893, target=0.723, error=1.170, recorded_delta=-0.123 deg
- `right_joint_5.pos` raw=-1.636, target=-0.735, error=-0.901, recorded_delta=-0.035 deg
- `left_joint_5.pos` raw=1.489, target=0.691, error=0.798, recorded_delta=0.142 deg
- `right_joint_3.pos` raw=-1.001, target=-0.313, error=-0.688, recorded_delta=-0.055 deg
- `left_joint_7.pos` raw=-1.402, target=-0.727, error=-0.675, recorded_delta=0.186 deg
### Frame 1
- `right_joint_4.pos` raw=-3.021, target=-1.538, error=-1.483, recorded_delta=0.109 deg
- `right_joint_7.pos` raw=2.010, target=0.801, error=1.209, recorded_delta=-0.011 deg
- `left_joint_2.pos` raw=1.906, target=0.722, error=1.184, recorded_delta=-0.145 deg
- `left_joint_4.pos` raw=-2.535, target=-1.366, error=-1.170, recorded_delta=0.051 deg
- `right_joint_5.pos` raw=-1.648, target=-0.735, error=-0.913, recorded_delta=-0.035 deg
- `left_joint_5.pos` raw=1.516, target=0.685, error=0.831, recorded_delta=-0.033 deg
- `right_joint_3.pos` raw=-1.029, target=-0.313, error=-0.716, recorded_delta=-0.055 deg
- `left_joint_7.pos` raw=-1.427, target=-0.727, error=-0.700, recorded_delta=0.186 deg
