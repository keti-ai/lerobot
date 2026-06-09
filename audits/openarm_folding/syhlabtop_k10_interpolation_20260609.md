# K10 Action Interpolation Multiplier

Date: 2026-06-09
Machine: syhlabtop
Scope: client-side async inference control smoothing

## Background

D07c confirmed that the grippers receive strong close commands and the motors reach them. The remaining live issue is the choppy/jerky behavior associated with action starvation and timing gaps. D07c summary showed:

```text
last_avg_fps: 22.54
max_net_latency_ms: 908.09
queue_empty_cnt: 19
clamp_events: 12
gripper_trace_rows: 661
```

The locked robot-folding recipe uses both:

- RTC on the server: chunk boundary blending / reanchoring
- action interpolation on the client: higher-rate interpolation between actions in the same chunk

K10 implements the second part as an opt-in client flag.

## Integration

`RobotClientConfig` now has:

```python
action_interpolation_multiplier: int = 1
```

Default `1` preserves the existing behavior. Values greater than 1 enable `ActionInterpolator` from `src/lerobot/utils/action_interpolator.py`.

`RobotClient` now:

- initializes `ActionInterpolator(config.action_interpolation_multiplier)`
- resets interpolation state on `start()` and `stop()`
- treats buffered interpolated actions as available actions
- pops a new queued policy action only when the interpolator buffer is empty
- sends interpolated actions at `1 / (fps * multiplier)`
- keeps observation `must_go` from firing while interpolated actions are still buffered

`audits/openarm_folding/k4_eval_runner.py` now sets:

```text
diag_arm_cap.action_interpolation_multiplier = 3
```

The K4 runner also uses `client.get_control_interval()` and records `queue_empty_cnt` only when no queued or buffered action is available.

## RTC Relationship

RTC and interpolation are orthogonal:

| mechanism | location | purpose |
|---|---|---|
| RTC | server | blend/reanchor chunk boundaries |
| interpolation | client | run higher-rate control between consecutive actions in a chunk |

D07d should run both together: RTC warm server plus `diag_arm_cap` (`arm15/grip65`, multiplier 3).

## Verification

Compile:

```text
uv run python -m py_compile src/lerobot/async_inference/robot_client.py src/lerobot/async_inference/configs.py audits/openarm_folding/k4_eval_runner.py
PASS
```

Config-only:

```text
uv run python audits/openarm_folding/k4_eval_runner.py --config-only --trial D07d --obj banana --profile diag_arm_cap --duration-s 30 --task ...
action_interpolation_multiplier: 3
PASS
```

Focused pytest:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 UV_CACHE_DIR=/tmp/uv-cache uv run --extra test python -m pytest tests/async_inference/test_robot_client.py -q
27 passed in 0.33s
```

Notes:

- Initial `uv run python -m pytest ...` failed because `pytest` was not installed in the narrow venv.
- `uv run --extra test ...` installed test dependencies, then failed due to an unrelated ROS pytest plugin autoloading `/opt/ros/humble` and missing `lark`.
- Disabling external plugin autoload made the repo-focused test pass.

## Multiplier 3 Unit Check

The added unit test verifies that multiplier 3 expands the second queued policy action into three control sends:

```text
sent motor_1.pos: [0.0, 1.0, 2.0, 3.0]
control interval: 1 / (fps * 3)
```

This confirms the queue pop rate is slower than the send-action rate when interpolation is enabled.

## Next

D07d should be the live validation:

- operator present
- RTC warm server
- `diag_arm_cap`: arm15, grip65, interpolation multiplier 3
- compare against D07b/D07c:
  - `queue_empty_cnt`
  - smoothness/choppy motion
  - grasp contact and handover quality

