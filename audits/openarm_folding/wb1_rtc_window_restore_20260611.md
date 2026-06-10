# WB1 RTC Window Restore

Executed: 2026-06-11 KST

## Scope

- Target server code: `src/lerobot/async_inference/policy_server.py`
- Branch: `audit/openarm-folding-baseline`
- Base before edit: `73acce74`
- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- Server endpoint: `10.252.205.103:8081`

Local `git pull` result:

```text
Fast-forwarded local a6000 checkout to 04a5d8f4.
```

The active patched server is reachable on 8081:

```text
LISTEN *:8081 users:(("python3",pid=604002,fd=7))
```

## H: Chunk Length

HF config read after registering the `pi05` policy class:

```text
type pi05
chunk_size 30
n_action_steps 30
dtype bfloat16
rtc_config None
```

Client config in `audits/openarm_folding/k4_eval_runner.py`:

```text
actions_per_chunk=30
fps=30
```

Code path:

- `PolicyServer._get_action_chunk()` runs policy RTC over the policy action chunk.
- The server then returns `chunk[:, : self.actions_per_chunk, :]`.
- `_pad_rtc_prefix_for_compile()` uses `policy.config.chunk_size` when compile is enabled.

Decision: actual RTC chunk length `H=30`. The client also requests 30 actions, so there is no hidden `H=50` margin in the current alpha-double-prime deployment.

## d: Delay Evidence

Patched bf16/no-compile server-side WB1 logging after process-only tmux respawn:

```text
log: /tmp/k1_server_logs/policy_server_wb1_horizon15_bf16_20260611_014404.log
pid: 604002
gpu: CUDA_VISIBLE_DEVICES=1
bind: 0.0.0.0:8081
torch_compile: False
```

WB1 analyzer summary across 12 synthetic no-robot chunks:

| metric | mean | p95 | max |
|---|---:|---:|---:|
| delay_steps_current | 13.25 | 14 | 14 |
| delay_steps_qmax | 13.67 | 14 | 14 |
| window_upper_H_minus_d | 16.33 | 17 | 17 |

Server log decision fields:

```text
WB1 RTC window config | policy_chunk_size_H=30 | actions_per_chunk=30 | execution_horizon_s=15 | environment_dt=0.033333s | torch_compile=False
WB1 RTC window delay | ... delay_steps_qmax=14 | history_mean=13.25 | history_p95=14 | history_max=14 | window_upper_H_minus_d=16 | window_ok=True
```

Action timing from the same run:

| source | steady range |
|---|---:|
| K13 inference_ms | 381.5-438.2 ms |
| K13 pipeline_core_ms | 405.9-466.3 ms |
| synthetic GetActions RTT | 411.7-473.1 ms |

Interpretation:

- RTC currently uses server-side pipeline latency (`_merge_rtc_action_chunk(..., total_latency)`), not client network latency.
- The patched bf16/no-compile server measured `d` p95/max `14` controller steps in the no-robot synthetic run.
- With `H=30` and `s=15`, the measured conservative window is `14 <= 15 <= 16`, so `window_ok=True`.
- Compile is not required for the current server-side measurement. If live operator logs later push qmax above 15, no static `s` can satisfy the window with `H=30`; latency reduction would be required.

## Selected Horizon

Changed:

```text
_ROBOT_FOLDING_RTC_EXECUTION_HORIZON = 10 -> 15
```

Rationale:

- `s=15` is the largest balanced value possible for `H=30`.
- If live server delay is `d=15`, then `d <= s <= H-d` becomes `15 <= 15 <= 15`.
- If `d<15`, `s=15` remains inside the feasible window until `H-d` drops below 15.
- If `d>15`, no static horizon can satisfy the RTC window with `H=30`; the next step must reduce `d`, usually compile-on or equivalent latency reduction.

Compile decision for this commit:

- Compile remains opt-in through `LEROBOT_ASYNC_SERVER_TORCH_COMPILE`.
- The restarted WB1 server uses bf16/no-compile: `LEROBOT_ASYNC_SERVER_TORCH_COMPILE=0`.
- Measured `delay_steps_qmax` p95/max is `14`, so compile-on was skipped for WB1.
- If future live logs report sustained `delay_steps_qmax > 15` or `window_ok=False`, horizon alone cannot fix the window at `H=30`; compile-on or another latency reduction must be revisited.

## Code Changes

`policy_server.py` now logs WB1 window state:

- On policy load:
  - `policy_chunk_size_H`
  - `actions_per_chunk`
  - `execution_horizon_s`
  - `environment_dt`
  - `torch_compile`
- On every RTC merge:
  - current delay step
  - conservative queue max delay step
  - rolling delay history count/mean/p95/max
  - `H-d`
  - `window_ok`

Example log prefixes:

```text
WB1 RTC window config | policy_chunk_size_H=30 | actions_per_chunk=30 | execution_horizon_s=15
WB1 RTC window delay | ... delay_steps_qmax=... | window_upper_H_minus_d=... | window_ok=...
```

## Verification Completed

Local compile check:

```text
uv run python -m py_compile src/lerobot/async_inference/policy_server.py
```

Result: pass.

Verifier compile check:

```text
UV_CACHE_DIR=/tmp/uv-cache uv run python -m py_compile audits/openarm_folding/wb1_synthetic_grpc_client.py src/lerobot/async_inference/policy_server.py
```

Result: pass.

Scoped diff check:

```text
git diff --check -- src/lerobot/async_inference/policy_server.py audits/openarm_folding/wb1_rtc_window_restore_20260611.md
```

Result: pass.

Policy server unit test:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/async_inference/test_policy_server.py -q
```

Result:

```text
6 passed in 0.14s
```

Note: plain pytest without `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` failed before collection because the system ROS `launch_testing` plugin imports `lark`, which is not installed in the current environment.

HF config check:

```text
chunk_size 30
n_action_steps 30
```

Result: pass.

8081 reachability:

```text
LISTEN 0 4096 *:8081 *:* users:(("python3",pid=604002,fd=7))
```

Result: current server is reachable and is running this WB1 patch.

Warmup after lazy policy load:

```text
Policy warmup: preprocess 18.49ms, no-prefix 8656.05ms, RTC no-leftover nanms, guided RTC 1108.36ms, compile extras none
```

Full no-robot synthetic gRPC run after restart:

```text
summary: /tmp/k1_server_logs/wb1_synthetic_grpc_summary_bf16.json
chunks: 4
all_actions_finite: true
all_chunks_nonempty: true
max_get_actions_ms: 436.60
```

No-reset steady-state synthetic gRPC run:

```text
summary: /tmp/k1_server_logs/wb1_synthetic_grpc_summary_bf16_noreset.json
chunks: 8
all_actions_finite: true
all_chunks_nonempty: true
max_get_actions_ms: 473.13
```

Final analyzer output:

```text
summary: /tmp/k1_server_logs/wb1_rtc_window_summary_bf16_12chunks.json
delay_count: 12
delay_steps_current: mean=13.25 p95=14 max=14
delay_steps_qmax: mean=13.67 p95=14 max=14
window_ok_count: 12
window_false_count: 0
window_ok_rate: 1.0
```

## Restart Status

Completed on a6000 without destroying the tmux session.

Process-only respawn:

```bash
tmux respawn-pane -k -t k1_policy_server -c /home/syh/workspace/lerobot bash
```

Server command:

```bash
CUDA_VISIBLE_DEVICES=1 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
LEROBOT_ASYNC_SERVER_TORCH_COMPILE=0 \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8081 \
  --fps=30
```

GPU state after policy load and synthetic verification:

```text
GPU0 used/free/util: 3811 MiB / 44740 MiB / 0%
GPU1 used/free/util: 10758 MiB / 37793 MiB / 0%
GPU2 used/free/util: 41947 MiB / 6605 MiB / 100%
GPU3 used/free/util: 41946 MiB / 6605 MiB / 100%
```

Colleague heavy jobs on GPU2/3 were left untouched.

## Decision Rule Result

- `delay_steps_qmax <= 15` and `window_ok_rate=1.0`: bf16+horizon15 is valid enough for D07q.
- Any steady `window_ok=False`: `H=30` cannot be fixed by raising `s`; restart compile-on or reduce latency before D07q.

Result: bf16+horizon15 passed the server-side no-robot gate. Compile-on was skipped.

## Next Gate

Server is left running on `10.252.205.103:8081` for operator D07q:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/k4_eval_runner.py \
  --trial D07q --obj banana --profile diag_handover_grip --duration-s 60 \
  --task "Pick the banana, hand it over to the other arm, and place it at the target." \
  2>&1 | tee /home/syhlabtop/k4_logs/trial_D07q_banana.log
```

The D07q local summary includes the exact profile spec, max-relative-target dict,
chunk trigger, aggregation mode, interpolation multiplier, and FPS so the live
result can be compared against the server-side WB1 window log.
