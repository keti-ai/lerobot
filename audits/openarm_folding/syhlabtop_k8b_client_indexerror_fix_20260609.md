# K8b Client Receiver IndexError Fix

Date: 2026-06-09
Machine: `syhlabtop`
Branch: `audit/openarm-folding-baseline`

## Background

D07 RTC live trial failed after one action chunk. The client receiver thread
crashed in `RobotClient.receive_actions()` while logging the verbose queue
state:

```text
Received action chunk for step #0 | Latest action: #29 | Incoming actions: 0:29
IndexError: list index out of range
```

The delayed chunk was fully stale: all incoming timesteps had already been
consumed. `_aggregate_action_queues()` correctly skipped those actions, leaving
the queue empty, but the verbose logging path still indexed
`new_timesteps[0]`.

## Change

File: `src/lerobot/async_inference/robot_client.py`

- Added `_format_timestep_range()` so empty timestep lists render as `empty`.
- Added `_log_action_queue_update()` to centralize verbose queue logging and
  protect logging from killing the receiver thread.
- Kept `_aggregate_action_queues()` behavior unchanged: stale actions are still
  discarded.
- Added an explicit empty deserialized chunk guard.
- Added a debug log for fully stale chunks where all incoming timesteps are
  already consumed.

This is a defensive client-side fix only. No server behavior was changed.

## Tests

Commands run:

```bash
uv run python -m py_compile src/lerobot/async_inference/robot_client.py
uv run python -m py_compile tests/async_inference/test_robot_client.py
```

Both passed.

`pytest` was not available in the current uv environment:

```text
error: Failed to spawn: `pytest`
Caused by: No such file or directory
```

Direct stale-chunk mock was run instead:

```bash
uv run python -c "... stale TimedAction chunk 0:3 with latest_action=29 ..."
```

Result:

```text
Latest action: 29 | Old action steps: empty | Incoming action steps: 0:3 | Updated action steps: empty
empty queue stale chunk mock ok
```

## Result

The D07 crash condition is now guarded on the client side. A fully stale chunk
can leave the queue empty without raising `IndexError` from verbose logging.

K8a server warmup / stale-chunk behavior should still be validated separately
before repeating D07.
