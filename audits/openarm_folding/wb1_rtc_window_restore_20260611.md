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
Already up to date.
```

The active 8081 port is reachable from syhlabtop:

```text
Connection to 10.252.205.103 8081 port [tcp/tproxy] succeeded!
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

Authoritative server-side WB1 delay logging is added in this change, but the patched server has not yet been restarted because SSH to a6000 failed:

```text
syhlabtop@10.252.205.103: Permission denied (publickey,password).
```

Existing server-side evidence from K13/K11 logs:

| source | mean | p95 | max |
|---|---:|---:|---:|
| old server action total | 552.3 ms | 689.5 ms | 861.3 ms |
| old RTC merge latency | 549.4 ms | 685.9 ms | 858.9 ms |
| old real delay steps | 16.9 | 21-22 | 26 |

Latest client-side D07p evidence:

| metric | mean | p95 | max |
|---|---:|---:|---:|
| network latency | 629.0 ms | 794.3 ms | 1338.7 ms |
| delay steps at 30 FPS | 19 | 24 | 41 |
| delay steps at last avg FPS 17.27 | 11 | 14 | 24 |

Interpretation:

- RTC currently uses server-side pipeline latency (`_merge_rtc_action_chunk(..., total_latency)`), not client network latency.
- The available server-side evidence already shows bf16/no-compile p95 `d > 15`.
- With `H=30`, the RTC paper window `d <= s <= H - d` has no solution when `d > 15`.

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
- This patch does not force compile on.
- First restart should run bf16/no-compile with `s=15` only if the goal is to measure the new WB1 `window_ok` logs.
- If `WB1 RTC window delay` reports `delay_steps_qmax > 15` or `window_ok=False`, compile is not optional; horizon alone cannot fix the window at `H=30`.

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
Connection to 10.252.205.103 8081 port [tcp/tproxy] succeeded!
```

Result: current server is still reachable, but it is not yet proven to be running this WB1 patch.

## Restart Status

Not completed in this session.

Reason: SSH authentication to a6000 failed:

```text
Permission denied (publickey,password).
```

Therefore the following requested items are still pending:

- a6000 `git pull`
- process-only restart inside `k1_policy_server`
- PID/GPU/bind capture after restart
- patched synthetic gRPC no-robot run
- live `WB1 RTC window delay` d distribution

The no-robot verifier added for the pending synthetic run is:

```text
audits/openarm_folding/wb1_synthetic_grpc_client.py
```

The log analyzer for the resulting server log is:

```text
audits/openarm_folding/wb1_analyze_rtc_window_log.py
```

It exercises the same RPC sequence as `RobotClient` without OpenArm hardware:

1. `Ready`, unless `--skip-ready` is set
2. `SendPolicyInstructions`, unless `--skip-policy-setup` is set
3. repeated `SendObservations` + `GetActions`

Run after the a6000 process has been restarted with the WB1 patch. This full mode intentionally resets server state and loads the policy:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/wb1_synthetic_grpc_client.py \
  --server-address 10.252.205.103:8081 \
  --num-chunks 2 \
  --summary-json /home/syhlabtop/k4_logs/wb1_synthetic_grpc_summary.json
```

If the server is already patched and policy-loaded, use the non-reset probe mode:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/wb1_synthetic_grpc_client.py \
  --server-address 10.252.205.103:8081 \
  --skip-ready \
  --skip-policy-setup \
  --num-chunks 2 \
  --summary-json /home/syhlabtop/k4_logs/wb1_synthetic_grpc_summary_noreset.json
```

Expected client-side pass criteria:

- every chunk returns `num_actions=30`
- `all_actions_finite=true`
- `all_chunks_nonempty=true`

Expected server-side log evidence:

- `WB1 RTC window config | policy_chunk_size_H=30 | ... execution_horizon_s=15`
- `WB1 RTC window delay | ... window_ok=...`

Summarize the server log after the verifier or D07q:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/wb1_analyze_rtc_window_log.py \
  /tmp/k1_server_logs/<policy_server_wb1_log>.log \
  --summary-json /tmp/k1_server_logs/wb1_rtc_window_summary.json
```

Decision rule:

- `delay_steps_qmax <= 15` and `window_ok_rate=1.0`: bf16+horizon15 is valid enough for D07q.
- Any steady `window_ok=False`: `H=30` cannot be fixed by raising `s`; restart compile-on or reduce latency before D07q.

When SSH is available, restart command should follow the existing K15/K15-recovery pattern and leave colleague GPU processes untouched. Start bf16 first only for measurement:

```bash
CUDA_VISIBLE_DEVICES=<free_gpu> \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
LEROBOT_ASYNC_SERVER_TORCH_COMPILE=0 \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8081 \
  --fps=30
```

If the new WB1 logs show `window_ok=False` because `delay_steps_qmax > 15`, restart with compile-on using the MB2 pattern:

```bash
CUDA_VISIBLE_DEVICES=<free_gpu> \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1 \
TORCH_LOGS=recompiles,graph_breaks \
PYTORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor-wb1-server \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8081 \
  --fps=30
```

## Next Gate

1. Restart patched server on a6000.
2. Confirm log:
   - `execution_horizon_s=15`
   - `policy_chunk_size_H=30`
   - `window_ok=True` on steady chunks
3. Run `wb1_synthetic_grpc_client.py`.
4. Run `wb1_analyze_rtc_window_log.py` on the server log.
5. If `window_ok=False`, enable compile; do not try `s>15` with `H=30`.
6. After server window is valid, run operator D07q:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python audits/openarm_folding/k4_eval_runner.py \
  --trial D07q --obj banana --profile diag_handover_grip --duration-s 60 \
  --task "Pick the banana, hand it over to the other arm, and place it at the target." \
  2>&1 | tee /home/syhlabtop/k4_logs/trial_D07q_banana.log
```

The D07q local summary includes the exact profile spec, max-relative-target dict,
chunk trigger, aggregation mode, interpolation multiplier, and FPS so the live
result can be compared against the server-side WB1 window log.
