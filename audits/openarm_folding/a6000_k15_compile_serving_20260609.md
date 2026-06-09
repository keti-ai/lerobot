# a6000 K15 torch.compile serving

Executed: 2026-06-10 KST

## Context

- Branch baseline before K15 edit: `5f4a8010`
- Server target: `k1_policy_server`, `0.0.0.0:8081`
- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- Checkpoint:
  `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232/checkpoints/030000/pretrained_model`
- RTC remains K11 horizon 10.
- K14 bf16 autocast remains enabled.
- No checkpoint, client, horizon, or RTC logic was changed.

## Checkpoint Compile Config

Checkpoint grep:

```text
train_config.json: "compile_model": false
train_config.json: "compile_mode": "max-autotune"
config.json: "compile_model": false
config.json: "compile_mode": "max-autotune"
```

Conclusion:

- Training did not use compile.
- K15 serving compile is independent from training compile.
- The server overrides compile only at policy load time, in memory.

## Native Compile Path

PI0.5 already has a native compile path in `src/lerobot/policies/pi05/modeling_pi05.py`:

```text
if config.compile_model:
    torch.set_float32_matmul_precision("high")
    self.sample_actions = torch.compile(self.sample_actions, mode=config.compile_mode)
    self.forward = torch.compile(self.forward, mode=config.compile_mode)
```

`RTCInferenceEngine` in `src/lerobot/rollout/inference/rtc.py` does not apply compile directly. It tracks `use_torch_compile` and waits for warmup inferences. The rollout context sets `policy_config.compile_model = cfg.use_torch_compile` before policy construction, which lets PI0.5 use its native compile hook.

K15 follows that pattern in `policy_server.py`:

- load policy config before construction
- set `compile_model=True`
- set `compile_mode="default"`
- call `policy_class.from_pretrained(..., config=policy_config)`

## Mode Selection

Standalone compile tests on GPU1:

| mode | warmup behavior | steady guided RTC |
|---|---|---:|
| `default` | large first compile, then stable | `160.64 ms` mean |
| `reduce-overhead` | graph breaks + very slow CUDA graph path | `12020.59 ms` mean |

`reduce-overhead` was rejected. K15 uses `default`.

Observed `default` standalone warmup:

```text
warmup0 no kwargs: 130011.78ms
warmup1 len10/delay0: 85107.02ms
warmup2 len18/delay12: 6139.09ms
warmup3 len16/delay14: 160.79ms
warmup4 len17/delay13: 161.65ms
steady mean: 160.64ms, median 161.03ms, max 161.74ms
```

Observed `reduce-overhead` standalone:

```text
warmup0 no kwargs: 110994.20ms
warmup1 len10/delay0: 59437.13ms
warmup2 len18/delay12: 22272.56ms
warmup3 len16/delay14: 12906.85ms
warmup4 len17/delay13: 12870.43ms
steady mean: 12020.59ms, median 12006.54ms, max 13977.43ms
```

## Code Change

Changed only `src/lerobot/async_inference/policy_server.py`.

Added K15 compile support:

- `_should_use_torch_compile()`
  - compile only for `pi05`
  - compile only on CUDA
  - require `torch.compile`
- `_load_policy(...)`
  - loads `PreTrainedConfig`
  - injects `compile_model=True`, `compile_mode="default"`, `device=<client device>`
  - uses PI0.5 native compile path through `from_pretrained(..., config=policy_config)`
  - falls back to normal `from_pretrained(...)` if config load/compile setup fails
- `_reload_policy_without_compile(...)`
  - fallback reload path if compile warmup raises
- `_warmup_policy_autograd() -> bool`
  - keeps K8a no-prefix warmup
  - adds RTC no-leftover warmup for the first real RTC call shape
  - keeps guided RTC warmup
  - adds compile-only live-like RTC warmups:
    - leftover len 18, delay 12
    - leftover len 16, delay 14
    - leftover len 17, delay 13
  - returns success/failure so `SendPolicyInstructions` can fall back to non-compile

Non-PI0.5 and non-CUDA policies keep the existing non-compile load path.

## Graph Breaks And Recompile

Server was started with:

```text
TORCH_LOGS=recompiles,graph_breaks
PYTORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor-k15-server
```

Expected graph breaks/recompiles during compile warmup:

- `modeling_pi05.py:883`: `copy.deepcopy(past_key_values)`
- `rtc/modeling_rtc.py:214`: `Tensor.requires_grad_()`
- `rtc/modeling_rtc.py:219`: `torch.autograd.grad`
- scalar guards on RTC `time`/`tau`
- kwargs/shape guards for `prev_chunk_left_over` None vs len 10 vs len 18

First cold server compile warmup:

```text
Policy warmup: preprocess 625.97ms, no-prefix 33166.34ms,
RTC no-leftover 9681.97ms, guided RTC 54932.42ms,
compile extras len18/delay12 9656.29ms, len16/delay14 221.03ms, len17/delay13 227.04ms
Time taken to put policy on cuda: 224.1316 seconds
```

Final hot-cache reload/warmup with correct synthetic feature schema:

```text
Policy warmup: preprocess 511.32ms, no-prefix 4263.65ms,
RTC no-leftover 310.91ms, guided RTC 388.84ms,
compile extras len18/delay12 373.07ms, len16/delay14 380.52ms, len17/delay13 382.01ms
```

Recompile/graph-break count:

```text
full log: 21 recompile events, 21 graph-break events
after final warmup: 0 recompile events, 0 graph-break events
```

Interpretation:

- K15 compile is noisy during warmup.
- The final steady synthetic run did not trigger additional recompile/graph-break logs.
- Warmup covers the first no-kwargs path, first RTC no-leftover path, and live-like guided leftover lengths.

## Action Sanity

Standalone compare on GPU1:

- eager output: same synthetic observation, same seed, guided RTC len18/delay12
- compiled output: native compile default, warmup complete, same seed and kwargs

```text
compiled_ms=202.28
max_abs_diff=0.00664060
mean_abs_diff=0.00078190
eager_abs_mean=0.11660732
compiled_abs_mean=0.11655828
```

This is within the K14 bf16 sanity scale (`max_abs_diff=0.0120`, `mean_abs_diff=0.000926`).

## Server Synthetic gRPC Measurement

Successful run:

- local gRPC client on `127.0.0.1:8081`
- correct plain dict `lerobot_features`, matching robot-client feature format
- zero 16D state
- three zero camera frames:
  - left wrist `(720, 1280, 3)`
  - right wrist `(720, 1280, 3)`
  - base `(480, 640, 3)`
- `must_go=True`
- 12 observations/action chunks
- steady stats skip first two chunks (`obs >= 16`)

Client loop:

```text
policy warmup complete load_warmup_s=119.82
iter=0 send_ms=37.31 getactions_ms=296.77 actions_bytes=67292
iter=1 send_ms=22.38 getactions_ms=309.40 actions_bytes=67292
iter=2 send_ms=18.33 getactions_ms=304.71 actions_bytes=67292
iter=3 send_ms=17.57 getactions_ms=307.81 actions_bytes=67292
iter=4 send_ms=17.01 getactions_ms=304.77 actions_bytes=67292
iter=5 send_ms=15.75 getactions_ms=293.18 actions_bytes=67292
iter=6 send_ms=15.68 getactions_ms=313.54 actions_bytes=67292
iter=7 send_ms=13.95 getactions_ms=311.61 actions_bytes=67292
iter=8 send_ms=14.19 getactions_ms=306.67 actions_bytes=67292
iter=9 send_ms=15.54 getactions_ms=303.00 actions_bytes=67292
iter=10 send_ms=15.19 getactions_ms=424.22 actions_bytes=67292
iter=11 send_ms=19.28 getactions_ms=294.51 actions_bytes=67292
```

The `iter=10` spike was server-side `prepare_ms=125.96`, not compile recompile.

## K13/K14/K15 Comparison

Steady predict path:

| component | K13 mean ms | K14 mean ms | K15 mean ms |
|---|---:|---:|---:|
| prepare | `5.19` | `3.64` | `15.87` |
| preprocess | `5.01` | `5.61` | `4.16` |
| inference | `413.32` | `395.94` | `287.86` |
| postprocess loop | `6.49` | `6.18` | `4.78` |
| RTC merge | `0.30` | `0.28` | `0.23` |
| pipeline core | `430.18` | `411.55` | `312.80` |
| predict total | `430.60` | `411.95` | `313.12` |

Steady GetActions:

| component | K13 mean ms | K14 mean ms | K15 mean ms |
|---|---:|---:|---:|
| queue age | `1.73` | `1.80` | `1.34` |
| predict | `430.78` | `412.12` | `313.25` |
| serialize | `1.90` | `1.85` | `1.35` |
| handler ready | `432.79` | `414.08` | `314.69` |

K15 steady distribution:

| metric | mean ms | median ms | p95 ms | max ms |
|---|---:|---:|---:|---:|
| inference | `287.86` | `288.03` | `295.79` | `296.86` |
| handler ready | `314.69` | `304.25` | `311.67` | `422.60` |

Delta:

- K13 inference `413.32 -> 287.86 ms`: `-105.46 ms`, `1.44x`
- K14 inference `395.94 -> 287.86 ms`: `-108.08 ms`, `1.38x`
- K14 handler `414.08 -> 314.69 ms`: `-99.39 ms`, `1.32x`

The K15 steady forward target entered the RTC horizon-10 window (`333 ms`) in synthetic server measurements.

## Server Status

Server log:

```text
/tmp/k1_server_logs/policy_server_k15_compile_20260610_000857.log
```

Bind:

```text
LISTEN *:8081 users:(("python3",pid=4123765,fd=7))
```

tmux:

```text
k1_policy_server: 1 windows (created Wed Jun 10 00:08:57 2026)
```

GPU:

```text
0, 22541 MiB used, 26011 MiB free, 0% util
1, 289 MiB used, 48262 MiB free, 0% util
2, 289 MiB used, 48262 MiB free, 0% util
3, 289 MiB used, 48262 MiB free, 0% util
```

GPU0 was selected because it hosted the previous K14 server and had no coworker training conflict. GPUs 1-3 remained free.

## Verification

```text
py_compile: pass
synthetic gRPC no-robot: pass
action sanity: pass
post-warmup recompile/graph-break count: 0
server bind 8081: pass
tmux alive: pass
```

The K15 server is ready for D07f operator live. The expected live improvement is lower forward latency and better alignment with the RTC horizon-10 window. If D07f still shows chunk boundary choppiness, the remaining target is likely RTC dynamics/control behavior rather than server-side model forward alone.
