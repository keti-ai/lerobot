# a6000 K13 server-side latency breakdown

Executed: 2026-06-09 KST

## Context

- Branch baseline before edit: `ac15d03c`
- Server target: `k1_policy_server`, `0.0.0.0:8081`
- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- RTC remains K11 horizon 10.
- K8a warmup remains enabled.
- K12 client-side result:
  - `server_rtt_ms` mean `633.3`, median `608.7`, p95 `698.1`, max `933.5`
  - client observation send mean `34.1 ms`
  - client deserialize + queue update mean `5.4 ms`
  - K12 residual versus K6 warm forward estimate `398 ms`: about `235 ms` mean, `535 ms` max.

## Code Change

Changed only timing/logging in `src/lerobot/async_inference/policy_server.py`.

Added `INFO` logs:

- `K13 SendObservations timing`
  - receive stream + pickle deserialize
  - enqueue time
  - queue size
  - observation one-way timestamp age
- `K13 GetActions timing`
  - GetActions wait for an observation
  - queue age from enqueue to dequeue
  - predict time
  - action pickle serialize
  - protobuf response object construction
  - server sleep for configured inference latency
  - handler-ready time before returning to gRPC
- `K13 Predict timing`
  - raw observation prepare
  - preprocessor
  - policy inference
  - original action clone
  - chunk-30 postprocess loop
  - RTC merge
  - detach/cpu
  - TimedAction wrapping
  - pipeline core and full predict totals

No inference, RTC, horizon, warmup, client, or checkpoint logic changed.

Note: true gRPC response send time happens after the unary handler returns, so the server can log only up to handler return readiness. The response-send/cadence gap is inferred by comparing client `server_rtt_ms` with server handler timing.

## Existing K11/K12 Server Log

Source log:

```text
/tmp/k1_server_logs/policy_server_k11_horizon10_20260609_213227.log
```

The old log emitted action totals and RTC merge latency at `INFO`, but detailed prepare/preprocess/postprocess split was `DEBUG` and absent from tmux.

Parsed action-path totals:

| metric | n | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| `Observation ... Total time` | 76 | 549.4 | 530.1 | 685.9 | 858.9 |
| `Action chunk ... Total time` | 76 | 552.3 | 532.5 | 689.5 | 861.3 |
| `RTC action queue merged latency` | 76 | 549.4 | 530.1 | 685.9 | 858.9 |
| `real_delay_steps` | 76 | 16.9 | 16.0 | 21.0 | 26.0 |

Last 30 action chunks:

| metric | n | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| action total | 30 | 554.7 | 533.2 | 730.1 | 861.3 |
| RTC latency | 30 | 551.9 | 530.8 | 727.6 | 858.9 |
| real delay steps | 30 | 16.9 | 16.0 | 22.0 | 26.0 |

Interpretation:

- K12 `server_rtt_ms` mean `633.3 ms` minus old server action total mean `552.3 ms` leaves about `81 ms` outside the logged server handler.
- K12 max `933.5 ms` minus old server action max `861.3 ms` leaves about `72 ms` outside the logged server handler.
- The K12 `235 ms` mean residual versus K6's `398 ms` forward estimate was not all queue/serialize/cadence. The live server handler itself was often about `550 ms`, not `398 ms`.

## K13 Instrumented No-Robot Run

Server log:

```text
/tmp/k1_server_logs/policy_server_k13_breakdown_20260609_224112.log
```

Restart:

```text
K13 policy_server start base_commit=ac15d03c gpu=0 port=8081 rtc_execution_horizon=10 timing_instrumentation=1
PolicyServer started on 0.0.0.0:8081
```

Live policy load/warmup:

```text
Injected robot-folding RTCConfig: enabled=True | execution_horizon=10 | max_guidance_weight=10.0 | prefix_attention_schedule=RTCAttentionSchedule.EXP
Policy warmup: preprocess 366.34ms, no-prefix 853.48ms, guided RTC 404.30ms
```

No-robot synthetic gRPC run:

- local client on `127.0.0.1:8081`
- zero 16D state
- three zero camera frames matching alpha-prime-prime schema:
  - left wrist `(720, 1280, 3)`
  - right wrist `(720, 1280, 3)`
  - base `(480, 640, 3)`
- `must_go=True`
- 12 observations/action chunks
- steady stats below skip the first two chunks (`obs >= 16`).

Client-side synthetic loop:

```text
iter=0 send_ms=49.01 getactions_ms=380.02 actions_bytes=67292
iter=1 send_ms=16.15 getactions_ms=426.64 actions_bytes=67292
...
iter=11 send_ms=20.27 getactions_ms=464.58 actions_bytes=67292
```

### SendObservations

| component | n | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| receive + deserialize | 10 | 16.03 | 16.14 | 22.60 | 22.60 |
| enqueue | 10 | 0.04 | 0.04 | 0.04 | 0.04 |
| timestamp one-way age | 10 | 14.31 | 13.27 | 25.66 | 25.66 |

### Predict Path

| component | n | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| prepare raw obs to policy obs | 10 | 5.19 | 4.32 | 9.64 | 9.64 |
| preprocess | 10 | 5.01 | 4.74 | 6.69 | 6.69 |
| inference | 10 | 413.32 | 409.02 | 441.28 | 441.28 |
| original action clone | 10 | 0.06 | 0.06 | 0.07 | 0.07 |
| postprocess loop, 30 calls | 10 | 6.49 | 6.50 | 6.95 | 6.95 |
| RTC merge | 10 | 0.30 | 0.30 | 0.33 | 0.33 |
| detach/cpu | 10 | 0.04 | 0.04 | 0.05 | 0.05 |
| TimedAction wrapping | 10 | 0.08 | 0.08 | 0.10 | 0.10 |
| pipeline core | 10 | 430.18 | 424.31 | 462.46 | 462.46 |
| predict total | 10 | 430.60 | 424.71 | 462.88 | 462.88 |

### GetActions

| component | n | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|---:|
| wait for observation | 10 | 0.01 | 0.01 | 0.02 | 0.02 |
| queue age, enqueue to dequeue | 10 | 1.73 | 1.80 | 2.18 | 2.18 |
| predict | 10 | 430.78 | 424.88 | 463.06 | 463.06 |
| action pickle serialize | 10 | 1.90 | 1.86 | 2.17 | 2.17 |
| response message build | 10 | 0.03 | 0.03 | 0.05 | 0.05 |
| configured sleep | 10 | 0.00 | 0.00 | 0.00 | 0.00 |
| handler ready before gRPC return | 10 | 432.79 | 426.86 | 465.10 | 465.10 |

## Postprocess Loop Standalone Check

Standalone processor-only benchmark on GPU1:

- loaded config/processors only, not policy weights
- cached relative state via dummy preprocessor call
- compared current 30-call loop against a one-shot batched postprocessor
- action dim `16`, chunk `30`

Results:

```text
max_abs_diff: 0.0
loop_mean_ms: 5.812, median: 5.746, max: 8.899
vectorized_mean_ms: 0.243, median: 0.237, max: 0.317
speedup_mean_ms: 5.57
```

Interpretation:

- The current loop is vectorizable, but the maximum expected gain is only about `5-7 ms`.
- This is not the source of the `235 ms` mean residual or the `535 ms` max residual.

## Residual Attribution

Using K12's mean `server_rtt_ms = 633.3 ms`:

| subtraction | remaining mean residual |
|---|---:|
| `633.3 - K6 forward 398` | `235.3 ms` |
| `633.3 - K13 synthetic handler 432.8` | `200.5 ms` |
| `633.3 - K12 obs send 34.1 - K13 synthetic handler 432.8` | `166.4 ms` |
| `633.3 - old K11/K12 server action total 552.3` | `81.0 ms` |

The largest measured K13 server component is inference:

```text
inference mean 413.3 ms
non-forward server work inside GetActions mean about 19-20 ms
serialize/response-message mean about 2 ms
queue wait/age mean about 2 ms in the synthetic no-backlog run
```

Therefore:

- The residual is not the 30-action postprocess loop.
- It is not action serialization.
- It is not server observation queue wait under no-backlog conditions.
- The old live server log indicates most of K12 `server_rtt_ms` was already inside server action generation.
- The remaining outside-handler gap is likely gRPC response return/network/cadence plus timestamp alignment, but only about `80 ms` when compared with old live server action totals.

## Spike Attribution

K12 max residual versus K6 forward:

```text
933.5 - 398 = 535.5 ms
```

But old live server max action total:

```text
861.3 ms
```

So the spike is primarily server handler/action generation, not client-side receive or serialization. K13 synthetic did not reproduce that spike:

```text
handler_ready max 465.1 ms
inference max 441.3 ms
```

Likely spike sources:

- live server forward variance/GPU scheduling, not Python postprocess;
- early-trial RTC guided chunks with high real delay (`real_delay` max `26`);
- possible GPU clock/thermal/load variability;
- possible concurrent gRPC handler cadence during real client operation.

Current evidence does not support postprocess loop, pickle, or queue wait as the spike cause.

## Targets

Priority 1: policy forward / GPU path.

- Mean K13 inference is about `413 ms`; old live handler mean is about `552 ms`.
- If forward/GPU path is reduced to `250-300 ms`, expected server handler drops by roughly `100-160 ms`.
- Candidate next work: fp16/bf16 or torch.compile, with explicit K8a-style warmup because compile cold can be large.

Priority 2: live handler variance.

- Need capture K13 logs during the next operator trial to split the actual `552-861 ms` live handler into inference vs non-forward.
- If live K13 still shows inference spikes, optimize model/GPU.
- If live K13 shows queue/cadence spikes, then address server scheduling/concurrency.

Priority 3: postprocess vectorization.

- Safe and exact in standalone benchmark (`max_abs_diff=0.0`).
- Expected gain only `5-7 ms`, so it is useful cleanup but not the main latency target.

Priority 4: gRPC response/cadence.

- Server-side unary handler cannot directly measure network send after return.
- Approximate outside-handler gap from old live log is about `80 ms` mean.
- If needed, add client/server paired monotonic timestamp protocol or gRPC interceptor in a separate diagnostic.

## Goal Estimate

Current K12:

```text
server_rtt mean 633 ms, max 933 ms
```

Near-term expected gains:

- postprocess vectorization: `~5-7 ms`
- response/cadence optimization if confirmed: up to `~80 ms`
- forward optimization: likely `100-200 ms`, largest target

Practical target:

```text
server_rtt mean 633 ms -> 450-520 ms
max 933 ms -> below 700 ms if forward spikes are removed
```

This remains inside the 1 s chunk window, but reducing spikes should improve visible chunk-boundary smoothness.

## Restart Status

After adding K13 timing instrumentation, the server was restarted:

- tmux session: `k1_policy_server`
- bind: `0.0.0.0:8081`
- pid: `3849091`
- GPU: physical GPU 0
- log: `/tmp/k1_server_logs/policy_server_k13_breakdown_20260609_224112.log`

Bind check:

```text
k1_policy_server: 1 windows (created Tue Jun  9 22:41:12 2026)
LISTEN 0      4096                    *:8081             *:*    users:(("python3",pid=3849091,fd=7))
```

GPU state after synthetic warm run:

```text
0, 34995, 0
1, 48262, 0
2, 48262, 0
3, 48262, 0
```

## Next

- Use K13 server logs during the next operator trial to see whether live spikes are in `inference_ms` or queue/cadence.
- Prioritize forward optimization if live K13 confirms `inference_ms` dominates.
