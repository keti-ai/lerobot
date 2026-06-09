# K12 Client-Side Latency Breakdown

Date: 2026-06-09
Machine: syhlabtop
Trial: K12
Profile: `diag_arm_cap` (`arm15/grip65`, interpolation multiplier 3)
Server: `10.252.205.103:8081` K11 horizon 10 server

## Purpose

D07e still showed visible motion discontinuity. Gripper close, queue starvation,
and major cap mismatch were already ruled out or mitigated:

- D07c: gripper command/readback reached strong close.
- D07d: interpolation removed queue starvation.
- D07e: horizon 10 partially reduced choppiness but latency remained near 900 ms.

K12 adds client-side timing to split the residual latency into camera capture,
observation serialization/gRPC send, action chunk receive/deserialize, queue
update, and action application timing.

## Code Change

`RobotClientConfig` now has an optional default-off field:

```python
latency_breakdown_csv: str | None = None
```

When unset, no timing CSV is created and normal control behavior is unchanged.

When set, `RobotClient` records:

- `obs_capture_ms`: `robot.get_observation()` including 3 RealSense frames
- `send_ms`: observation pickle plus gRPC send
- `obs_serialize_ms`: pickle only
- `obs_grpc_ms`: gRPC observation send only
- `server_rtt_ms`: first action timestamp to client chunk receipt
- `deserialize_ms`: action chunk `pickle.loads`
- `queue_update_ms`: action queue aggregation/update
- `total_ms`: action timestamp to action application

`k4_eval_runner.py` enables this only for trial `K12`:

```text
/home/syhlabtop/k4_logs/latency_breakdown_K12.csv
```

## Trial Summary

Summary file: `/home/syhlabtop/k4_logs/summary_trial_K12.json`

```json
{
  "trial": "K12",
  "obj": "banana",
  "profile": "diag_arm_cap",
  "status": "completed_control_window",
  "duration_s": 15.0,
  "last_avg_fps": 17.0,
  "max_net_latency_ms": 933.46,
  "queue_empty_cnt": 0,
  "clamp_events": 27,
  "clamp_joint_counts": {
    "joint_1": 5,
    "joint_4": 26
  },
  "action_queue_samples": 629,
  "latency_breakdown_csv": "/home/syhlabtop/k4_logs/latency_breakdown_K12.csv"
}
```

The 15 s control window completed without receiver/control thread errors.

## Breakdown

CSV rows: 210

Rows with observation + first action chunk + action apply fields: 25

| component | n | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| obs_capture_ms | 89 | 2.1 | 2.0 | 2.5 | 4.3 |
| send_ms | 89 | 34.1 | 33.7 | 38.5 | 45.0 |
| obs_serialize_ms | 89 | 1.4 | 1.1 | 2.4 | 3.1 |
| obs_grpc_ms | 89 | 32.7 | 32.2 | 37.3 | 43.0 |
| server_rtt_ms | 25 | 633.3 | 608.7 | 698.1 | 933.5 |
| deserialize_ms | 25 | 4.7 | 3.8 | 8.0 | 14.1 |
| queue_update_ms | 25 | 0.7 | 0.4 | 0.7 | 6.8 |
| total_ms | 210 | 449.1 | 388.3 | 708.5 | 1067.6 |

Complete-row view:

| component | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|
| obs_capture_ms | 2.2 | 2.0 | 2.7 | 4.0 |
| send_ms | 35.1 | 35.1 | 37.9 | 45.0 |
| obs_serialize_ms | 1.5 | 1.3 | 2.5 | 3.1 |
| obs_grpc_ms | 33.6 | 33.4 | 36.4 | 43.0 |
| server_rtt_ms | 633.3 | 608.7 | 698.1 | 933.5 |
| deserialize_ms | 4.7 | 3.8 | 8.0 | 14.1 |
| queue_update_ms | 0.7 | 0.4 | 0.7 | 6.8 |
| total_ms | 605.1 | 546.4 | 824.4 | 1067.6 |

## Interpretation

Camera capture is not the bottleneck:

- 3-camera `robot.get_observation()` averaged about `2 ms`.

Client-side observation transfer is not the main bottleneck:

- observation pickle averaged `1.4 ms`
- gRPC send averaged `32.7 ms`
- total send averaged `34.1 ms`

Client action receive overhead is small:

- chunk deserialize averaged `4.7 ms`
- queue update averaged `0.7 ms`

The dominant measured component is `server_rtt_ms`:

- mean `633.3 ms`
- p95 `698.1 ms`
- max `933.5 ms`

Using K6's warm server forward estimate of about `398 ms`:

```text
server_rtt - 398 ms:
  mean residual: 235.3 ms
  median residual: 210.7 ms
  max residual: 535.5 ms

server_rtt - send_ms - 398 ms:
  mean residual after client send and forward: 200.2 ms
```

This means the residual is not explained by syhlabtop camera capture, pickle,
gRPC observation upload, client deserialize, or client queue update. It is
mostly server-side and transport/cadence time outside the measured forward pass:
server scheduling, observation queue timing, action chunk timing, RTC/processing
around the forward pass, or network round-trip jitter.

## Target Recommendation

Priority targets:

1. Server forward path remains large at about `398 ms`.
   - Compile/fp16/model-server optimization is still a major target.
   - If this drops to `200 ms`, end-to-end latency could plausibly drop by
     about `200 ms`.

2. Server-side residual/cadence is the next target, about `200-235 ms` mean and
   up to `535 ms` in spikes.
   - Add server-side timestamps for observation receive, queue admission,
     inference start/end, postprocess/RTC start/end, and chunk send.
   - Confirm whether the residual is server queue wait, RTC merge/postprocess,
     gRPC response scheduling, or network jitter.

3. Image compression or lower resolution is not the first target based on K12.
   - Client gRPC observation send is only about `33 ms`.
   - JPEG/compression may save some bandwidth, but it cannot explain the
     `600-900 ms` action chunk latency.

4. Camera capture parallelization is not a priority.
   - Capture is about `2 ms`, too small to matter for the current bottleneck.

## Decision

The residual latency is not on syhlabtop camera capture or client serialization.
K12 identifies the large target as server-side forward plus server/transport
cadence around the forward pass.

Next branch should be a server-side K13 breakdown/optimization:

- timestamp server observation receive to action send,
- separate queue wait, preprocess, forward, postprocess, RTC, serialization,
  and gRPC send,
- then optimize the largest server-side component before another official K4
  attempt.

