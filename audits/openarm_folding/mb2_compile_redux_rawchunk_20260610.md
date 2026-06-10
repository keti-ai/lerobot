# MB2 compile redux + raw-chunk wrist diagnostics

Executed: 2026-06-10 KST

## Context

- Branch: `audit/openarm-folding-baseline`
- Base before MB2 edit: `d3a99be6`
- Server: `k1_policy_server`, `0.0.0.0:8081`
- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- Active MB2 log: `/tmp/k1_server_logs/policy_server_mb2_compile_20260610_214354.log`
- GPU: `CUDA_VISIBLE_DEVICES=1`
- Compile serving: `LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1`
- Allocator mitigation: `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
- RTC: horizon 10, max guidance 10, EXP schedule

## Code Changes

Changed only `src/lerobot/async_inference/policy_server.py`.

### 1. RTC prefix pad for compile stability

K15 OOM hypothesis was live `prev_chunk_left_over` length variation causing Dynamo/Inductor graph variants and cache growth.

MB2 adds `_pad_rtc_prefix_for_compile(...)`:

- only active when `_torch_compile_enabled` is true
- pads/truncates `prev_chunk_left_over` to fixed `chunk_size`
- preserves RTC short-prefix semantics by clamping `execution_horizon` to the original leftover length before padding
- keeps compile-off path unchanged

Warmup now covers padded-prefix delays `6..15`, after the existing no-prefix and RTC no-leftover warmups. This covers the observed server real-delay range after compile (`7..11` in synthetic).

### 2. Raw wrist chunk diagnostics

MB2 logs wrist joint chunk trajectories at three server-side stages:

- `raw_policy_pre_postprocess_pre_merge`
- `postprocessed_pre_merge`
- `rtc_queue_after_merge`

Joint selection uses `action_feature_names` matching `joint_6` and `joint_7`.
For this checkpoint those are:

- `right_joint_6.pos`
- `right_joint_7.pos`
- `left_joint_6.pos`
- `left_joint_7.pos`

Logged metrics per chunk:

- `first`
- `last`
- `delta`
- `range`
- `std`

The server cannot observe the final client-side `weighted_average` aggregation or interpolation output. The closest server-side executed proxy is `rtc_queue_after_merge`, which is what is returned to the robot client before client aggregation/interpolation.

## Server Restart

The existing no-compile server was stopped without touching colleague processes. The `k1_policy_server` tmux session was kept alive by respawning its pane into a persistent shell, then launching the server inside that shell.

Launch:

```bash
CUDA_VISIBLE_DEVICES=1 \
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1 \
TORCH_LOGS=recompiles,graph_breaks \
PYTORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor-mb2-server \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8081 \
  --fps=30
```

Current status:

```text
LISTEN *:8081 users:(("python3",pid=4038113,fd=7))
tmux: k1_policy_server
GPU1 server memory: 9638 MiB
```

Colleague GPU processes were not touched:

- GPU0: `1037966`, `2987934`
- GPU2: `3879959`
- GPU3: `3879960`

## Warmup

Final warmup log:

```text
K15 torch.compile serving requested | policy_type=pi05 | mode=default | device=cuda
K14 serving precision | config_dtype=bfloat16 | device=cuda | autocast_dtype=bfloat16
Injected robot-folding RTCConfig: enabled=True | execution_horizon=10 | max_guidance_weight=10.0 | prefix_attention_schedule=RTCAttentionSchedule.EXP
Policy warmup: preprocess 14.41ms, no-prefix 39718.76ms, RTC no-leftover 8962.62ms, guided RTC 61394.88ms,
compile extras len18/delay6 212.39ms, len18/delay7 208.88ms, len18/delay8 217.91ms, len18/delay9 229.31ms,
len18/delay10 229.93ms, len18/delay11 223.58ms, len18/delay12 251.06ms, len18/delay13 224.48ms,
len18/delay14 226.24ms, len18/delay15 236.05ms
Time taken to put policy on cuda: 257.8335 seconds
```

Full warmup still shows expected Dynamo graph breaks/recompiles around:

- `copy.deepcopy(past_key_values)`
- `prev_chunk_left_over is None` vs tensor
- RTC scalar `time`

The important post-warmup result is clean:

```text
after_load: recompiles=0 graph_break_lines=0 oom=0
```

## Compile Memory Stability

Synthetic gRPC sequence:

- `Ready`
- `SendPolicyInstructions`
- 16 repeated `SendObservations` + `GetActions`
- 16D state
- 3 cameras: left wrist, right wrist, base
- variable timesteps
- observed RTC real-delay steps: `7..11`

Client summary:

```text
policy_load_warmup_s=257.84 mem_after_load=9636MiB
summary get_mean_ms=266.27 get_median_ms=261.79 get_max_ms=340.31
mem_min=9636MiB mem_max=9638MiB mem_delta_after_first=2MiB
```

Server log summary:

```text
full: recompiles=19 graph_break_lines=38 oom=0
after_load: recompiles=0 graph_break_lines=0 oom=0
inference: n=16 steady_mean=228.22ms median=227.89ms max=287.17ms
predict_total: n=16 steady_mean=261.36ms median=256.84ms max=335.88ms
handler_ready: n=16 steady_mean=263.78ms median=259.22ms max=338.11ms
real_delay_steps: n=16 steady_mean=8.31 median=8.00 min=7 max=11
```

Conclusion:

- MB2 restored compile latency with `d ~= 8 <= s=10`.
- GPU memory stayed flat after load.
- No post-load recompile/graph-break/OOM occurred in synthetic dynamic-delay requests.

## Action Sanity

One additional loaded-server request was unpickled and checked:

```text
action_sanity get_ms=252.97 count=30 shape=(30, 16) finite=True
min=-6.52711 max=3.81761 mem_before=9638MiB mem_after=9638MiB
```

## Raw Wrist Diagnostic Result

Wrist range summary across 16 chunks:

| stage | joint | mean abs delta | mean range | max range | mean std |
|---|---|---:|---:|---:|---:|
| raw policy | right_joint_6 | 0.0203 | 0.0425 | 0.0789 | 0.0107 |
| raw policy | right_joint_7 | 0.0233 | 0.0434 | 0.1095 | 0.0118 |
| raw policy | left_joint_6 | 0.0970 | 0.1875 | 0.3851 | 0.0546 |
| raw policy | left_joint_7 | 0.0128 | 0.0426 | 0.0605 | 0.0103 |
| postprocessed | right_joint_6 | 0.2928 | 0.6130 | 1.1383 | 0.1537 |
| postprocessed | right_joint_7 | 0.8145 | 1.5138 | 3.8225 | 0.4123 |
| postprocessed | left_joint_6 | 0.1871 | 0.3617 | 0.7431 | 0.1054 |
| postprocessed | left_joint_7 | 0.3551 | 1.1832 | 1.6803 | 0.2875 |
| RTC queue | right_joint_6 | 0.2217 | 0.5185 | 0.9825 | 0.1363 |
| RTC queue | right_joint_7 | 0.6161 | 1.2590 | 3.7146 | 0.3430 |
| RTC queue | left_joint_6 | 0.1766 | 0.2563 | 0.4812 | 0.0722 |
| RTC queue | left_joint_7 | 0.2968 | 1.0540 | 1.4011 | 0.2614 |

Example log:

```text
obs=0 raw_policy_pre_postprocess_pre_merge
right_joint_6 range=0.07891 std=0.01584
right_joint_7 range=0.02789 std=0.00823
left_joint_6 range=0.07370 std=0.01648
left_joint_7 range=0.06048 std=0.01259

obs=0 postprocessed_pre_merge
right_joint_6 range=1.13826 std=0.22854
right_joint_7 range=0.97341 std=0.28711
left_joint_6 range=0.14220 std=0.03180
left_joint_7 range=1.68027 std=0.34975

obs=0 rtc_queue_after_merge
right_joint_6 range=0.72206 std=0.18856
right_joint_7 range=0.93972 std=0.27540
left_joint_6 range=0.09913 std=0.02704
left_joint_7 range=1.40109 std=0.34062
```

Interpretation:

- Raw policy output is not perfectly flat; it contains wrist signal.
- After unnormalization/postprocessing, wrist roll/yaw motion is large and visible.
- The server RTC queue still preserves wrist variation after delay trimming.
- Therefore the policy/server path is producing wrist rotation. If live execution still looks like wrist rotation is washed out, the remaining likely suspects are client-side aggregation/interpolation or downstream robot execution, not dataset coverage alone.

## Aggregation Note

Current client aggregation registry:

```text
weighted_average = 0.3 * old + 0.7 * new
latest_only = new
average = 0.5 * old + 0.5 * new
conservative = 0.7 * old + 0.3 * new
```

MB2 did not change aggregation. Based on raw/server-queue wrist variation, the next measured change to consider after D07o is `weighted_average -> latest_only` if live wrist rotation still appears damped.

## Verification

```text
uv run --no-sync python -m py_compile src/lerobot/async_inference/policy_server.py
OK
```

Compile-off regression risk:

- compile remains default-off unless `LEROBOT_ASYNC_SERVER_TORCH_COMPILE=1`
- prefix padding is gated by `_torch_compile_enabled`
- raw wrist diagnostics are logging-only

## Next

- Run D07o live on current MB2 server.
- Watch for `d <= s` in live logs and GPU1 memory staying near 9.6 GiB.
- If wrist rotation is still damped live, test client `aggregate_fn_name=latest_only` in a separate controlled run.
