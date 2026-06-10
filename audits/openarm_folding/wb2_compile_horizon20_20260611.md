# WB2 Compile-On Horizon 20

Executed: 2026-06-11 KST

## Scope

- Repo: `/home/syh/workspace/lerobot`
- Branch: `audit/openarm-folding-baseline`
- Base after pull: `20c9d562`
- Server: `k1_policy_server`, `0.0.0.0:8081`
- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- GPU: `CUDA_VISIBLE_DEVICES=1`

## Code Changes

`src/lerobot/async_inference/policy_server.py`

1. RTC horizon changed:

```text
_ROBOT_FOLDING_RTC_EXECUTION_HORIZON = 15 -> 20
```

2. Added a same-policy reuse guard in `SendPolicyInstructions`.

Rationale: the normal `RobotClient.start()` path always sends `Ready()` and
`SendPolicyInstructions()`. Without a reuse guard, a preloaded server still
reloads and recompiles the policy when D07r starts. The guard keeps the client
thin and server-side only: identical policy specs skip reload/compile warmup,
reset RTC state, log the RTC window config, and return.

## Launch

Final server command:

```bash
CUDA_VISIBLE_DEVICES=1 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1 \
TORCH_LOGS=recompiles \
PYTORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor-wb2-server \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8081 \
  --fps=30
```

Final process:

```text
pid: 797370
bind: *:8081
log: /tmp/k1_server_logs/policy_server_wb2_compile_horizon20_reuse_20260611_024412.log
```

GPU after final reuse-handshake validation:

```text
GPU0 used/free/util: 3811 MiB / 44740 MiB / 0%
GPU1 used/free/util: 9932 MiB / 38619 MiB / 0%
GPU2 used/free/util: 41947 MiB / 6605 MiB / 100%
GPU3 used/free/util: 41946 MiB / 6605 MiB / 100%
```

Colleague GPU2/3 jobs were not touched.

## H, d, s Window

Known WB1 deployment values:

```text
policy_chunk_size_H=30
actions_per_chunk=30
execution_horizon_s=20
environment_dt=0.033333s
torch_compile=True
```

Final D07r-facing validation used the normal client handshake:

1. `Ready()`
2. `SendPolicyInstructions()` with the same policy spec
3. server reuse guard skipped reload/compile warmup
4. 12 synthetic no-robot chunks

Evidence:

```text
Reusing already-loaded policy instructions; skipping policy reload and compile warmup
send_policy_instructions_ms: 0.8767
```

RTC window analyzer on the final reuse-handshake segment:

```text
summary: /tmp/k1_server_logs/wb2_rtc_window_summary_compile_reuse_handshake.json
delay_count: 12
delay_steps_current: mean=7.67 p95=9 max=9
delay_steps_qmax: mean=8.00 p95=9 max=9
window_upper_H_minus_d: latest=21
window_ok_count: 12
window_false_count: 0
window_ok_rate: 1.0
```

Final window:

```text
d=9, s=20, H-d=21  =>  9 <= 20 <= 21
```

## Forward Timing

K13 timing summary on the final reuse-handshake segment:

```text
summary: /tmp/k1_server_logs/wb2_k13_predict_reuse_handshake_summary.json
count: 12
inference_ms: mean=210.20 p50=214.65 p95=249.11 max=249.11
pipeline_core_ms: mean=239.89 p50=241.79 p95=281.86 max=281.86
predict_total_ms: mean=241.29 p50=243.07 p95=283.87 max=283.87
```

Client-side synthetic gRPC:

```text
summary: /tmp/k1_server_logs/wb2_synthetic_grpc_summary_compile_reuse_handshake_steady.json
chunks: 12
all_actions_finite: true
all_chunks_nonempty: true
max_get_actions_ms: 289.58
```

## Compile Behavior

Initial policy setup/warmup still specializes RTC time-step branches and logs
Dynamo recompiles during warmup. The final normal-client reuse path had:

```text
recompiles_after_last_ready: none
```

Memory stayed flat after repeated compiled requests:

```text
GPU1 after initial steady 32-chunk probe: 9932 MiB
GPU1 after final reuse-handshake probe: 9932 MiB
```

The initial full policy setup run had one post-setup spike:

```text
obs=30 inference_ms=731.43, real_delay=23, window_ok=False
```

That spike occurred before the reuse-guarded final normal-client segment. It is
treated as setup artifact, not steady D07r path. The final D07r-facing path is
the already-loaded, reuse-guarded server.

## Parity

Direct deterministic parity probe:

```text
script: /tmp/wb2_direct_parity_capture.py
fixed obs sequence, prefix_steps=20, inference_delay=9, execution_horizon=20
bf16/no-compile actions: /tmp/k1_server_logs/wb2_parity_bf16_actions.npz
compile-on actions: /tmp/k1_server_logs/wb2_parity_compile_actions.npz
```

Diff:

```text
summary: /tmp/k1_server_logs/wb2_parity_diff_summary.json
max_abs_diff: 0.19043
mean_abs_diff: 0.01649
per_chunk_max_abs_diff: [0.15581, 0.19043]
```

Per-dimension checks:

```text
summary: /tmp/k1_server_logs/wb2_parity_diff_per_dim.json
joint_2 max_abs_diff: 0.07786
joint_6 max_abs_diff: 0.02817
joint_7 max_abs_diff: 0.08888
```

Interpretation: parity is not bitwise/zero, but the mean absolute difference is
small and joint_2 is bounded in the deterministic no-robot probe. Final server
action sanity was finite across all gRPC chunks. If D07r shows a top-down
regression, compile numerical drift remains a candidate and bf16/horizon20 is
the fallback.

## Verification

```text
py_compile: pass
full setup gRPC: pass, all finite, initial setup spike observed
reuse-handshake gRPC: pass, all finite
steady RTC window: pass, d=9, s=20, H-d=21
recompile after final Ready: none
GPU memory: flat at 9932 MiB
8081: listening
```

Final listener:

```text
LISTEN *:8081 users:(("python3",pid=797370,fd=7))
```

## Decision

Keep final server as compile-on + horizon20 for D07r.

Next: operator D07r live against `10.252.205.103:8081`.
