# a6000 K6 inference latency breakdown

Executed: 2026-06-09 KST

## Context

- Branch updated to: `23e5aaa2`
- Running server: `k1_policy_server` on `0.0.0.0:8081`
- Server log: `/tmp/k1_server_logs/policy_server_k7_rtc_20260609_183357.log`
- Server process was not stopped or restarted.
- Standalone benchmark used physical GPU 1 through `CUDA_VISIBLE_DEVICES=1` to avoid the live server on GPU 0.

## D07 server log timing

Relevant server log lines:

```text
19:06:49 Receiving policy instructions ... Policy type: pi05 ... Actions per chunk: 30 | Device: cuda
19:08:39 Injected robot-folding RTCConfig: enabled=True | execution_horizon=20 | max_guidance_weight=10.0 | prefix_attention_schedule=RTCAttentionSchedule.EXP
19:08:39 RTC processor initialized on policy and model
19:08:42 RTC relative-action prefix re-anchoring enabled
19:08:42 Time taken to put policy on cuda: 112.7322 seconds
19:08:43 Preprocessing and inference took 0.8767s, action shape: torch.Size([1, 30, 16])
19:08:43 RTC action queue merged | latency=0.9608s | real_delay=29 | remaining_actions=1
19:08:43 Action chunk #0 generated | Total time: 964.69ms
19:08:45 Preprocessing and inference took 1.6502s, action shape: torch.Size([1, 30, 16])
19:08:45 RTC action queue merged | latency=1.6859s | real_delay=51 | remaining_actions=0
19:08:45 Action chunk #0 generated | Total time: 1688.35ms
```

Notes:

- The policy load cold phase was `112.7s`.
- The first generated chunk was a cold/no-prefix RTC path at `964.69ms` server-side.
- The second generated chunk was the first guided RTC path at `1688.35ms` server-side.
- The client-reported D07 `max_net_latency_ms=2679` is not pure network. In `robot_client.py`, it is computed from client receive time minus the first action timestamp, and that timestamp is the original observation timestamp.

## Standalone forward benchmark

Command environment:

```bash
CUDA_VISIBLE_DEVICES=1 \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python ...
```

Benchmark input:

- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- State: synthetic zero 16D state
- Images: synthetic zero tensors matching policy config:
  - `left_wrist`: `[3, 720, 1280]`
  - `right_wrist`: `[3, 720, 1280]`
  - `base`: `[3, 480, 640]`
- Action dim: `16`
- Chunk: `30`
- RTC guided case includes relative leftover re-anchor and `predict_action_chunk(..., prev_chunk_left_over=..., inference_delay=20, execution_horizon=20)`.

Results:

| path | cold/path-first | warm mean | warm median | warm max |
|---|---:|---:|---:|---:|
| preprocess only | 464.6 ms | 4.2 ms | 4.1 ms | 4.6 ms |
| RTC off predict | 1059.7 ms | 276.4 ms | 260.3 ms | 324.4 ms |
| RTC off predict + postprocess + pickle | 303.1 ms | 265.7 ms | 265.2 ms | 268.8 ms |
| RTC on, no prefix predict | 257.7 ms | 259.5 ms | 260.5 ms | 262.3 ms |
| RTC on, guided + reanchor predict | 1544.7 ms | 365.7 ms | 385.9 ms | 389.5 ms |
| RTC on, guided + reanchor + postprocess + pickle | 383.5 ms | 391.3 ms | 396.2 ms | 398.8 ms |
| pickle only, 30 TimedAction tensors | 1.6 ms | 1.4 ms | 1.3 ms | 1.8 ms |

Other benchmark facts:

- HF/cache policy load: `118.335s`
- Peak GPU allocated: `9105.5 MB`
- Benchmark JSON: `/tmp/k6_latency_benchmark_20260609.json`

## Breakdown

| source | D07 / measured value | interpretation |
|---|---:|---|
| Policy load cold start | 112.732 s server, 118.335 s standalone | Must be excluded from live trial timing by preloading before motion. |
| First no-prefix server chunk | 964.69 ms | Matches standalone RTC-off/no-prefix cold scale. Barely under 30-step chunk time at 30 fps. |
| First guided RTC server chunk | 1688.35 ms | Matches standalone first guided RTC cold path (`1544.7 ms`) plus server overhead. Exceeds 1.0 s chunk time. |
| Warm RTC-off forward | 276.4 ms | Baseline model forward is not the persistent bottleneck. |
| Warm RTC-guided forward | 365.7 ms | RTC guidance/re-anchor adds about `89 ms` vs RTC-off forward. |
| Warm guided full server-like path | 391.3 ms | Warm RTC should be comfortably under the 1.0 s chunk window. |
| Serialization | 1-4 ms | Not material. |
| Client D07 max minus server second chunk | about 990.7 ms | Residual includes observation age, client/server scheduling, gRPC transfer, client deserialize, and queue timing; it is not isolated network. |

## Attribution

The D07 `2679ms` spike is not explained by steady-state RTC compute.

Most likely sources:

1. Cold policy load and first-call warmup were not isolated before live action flow.
2. The first guided RTC chunk paid an autograd/guidance cold-path cost, producing a `1.65-1.69s` server chunk.
3. The remaining roughly `1.0s` in the client metric is outside server forward/serialization and is partly a measurement artifact because the client latency clock starts at the observation timestamp.

Not supported by the measurements:

- Persistent RTC overhead as the main cause: warm guided RTC is about `391ms` full path.
- Pickle/serialization as the main cause: isolated pickle is about `1.4ms`.
- Pure gRPC transfer as proven cause: the available a6000-side data cannot split observation age from transport without syhlabtop client logs.

## Conclusion

The 2.7s D07 value should be treated as a cold/warmup plus client-path residual spike, not as steady RTC infeasibility.

RTC remains real-time plausible after warmup:

- 30 actions at 30 fps gives a 1.0 s chunk window.
- Warm guided RTC full path measured about `0.39s`.
- The cold guided path measured about `1.5-1.7s`, which breaks the RTC assumption unless warmed before live motion.

## Optimization options

- Add or run a pre-live warmup sequence after `SendPolicyInstructions` and before motion:
  - one no-prefix chunk to warm model kernels,
  - one guided RTC chunk with dummy/held state to warm the autograd guidance path,
  - discard warmup actions.
  - Expected effect: reduce server chunk time from about `1.7s` cold guided to about `0.4s` warm guided.
- Keep the server process and loaded policy alive between D07 retries. Avoid re-sending policy instructions unless the checkpoint/device changes.
- Add client-side guard for empty/short action queues and IndexError before next live retry.
- If warm latency still exceeds 1.0 s in real client logs, then tune RTC:
  - lower `execution_horizon`,
  - lower `max_guidance_weight`,
  - compare `EXP` vs `LINEAR`,
  - consider disabling RTC only as a fallback.
- FP16/BF16 and torch compile may help warm throughput, but both need separate validation. Compile can make cold startup worse unless warmup is explicit.

## Next

- Implement or manually execute warmup/discard before D07 motion.
- Add client IndexError/empty-queue defense.
- Re-run D07 only after confirming the first live chunk is warm and client `max_net_latency_ms` is below the 1.0 s chunk window.
