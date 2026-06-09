# a6000 K8a policy_server autograd cold warmup discard

Executed: 2026-06-09 KST

## Context

- Branch baseline before edit: `a12f896e`
- Policy: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- Checkpoint source: alpha-prime-prime 030000, HF private model repo
- K6 finding: warm RTC guided inference is real-time plausible, but the first cold no-prefix/guided server chunks paid CUDA/autograd lazy-init and caused the D07 latency spike.
- K7 RTC server remains the base; no checkpoint, client, RTC primitive, or torch.compile change was made.

## Implementation

Changed `src/lerobot/async_inference/policy_server.py`.

- `SendPolicyInstructions` now calls `_warmup_policy_autograd()` after:
  - policy load,
  - device placement,
  - K7 RTCConfig injection,
  - pre/postprocessor construction,
  - RTC processor discovery.
- `_make_warmup_observation()` creates synthetic inputs from `policy.config.input_features`, with a fallback to `robot_state_feature`.
- `_warmup_policy_autograd()` runs the real server preprocessing path, then discards:
  - one no-prefix `policy.predict_action_chunk(preprocessed_observation)`,
  - one guided RTC `policy.predict_action_chunk(..., prev_chunk_left_over=..., inference_delay=0, execution_horizon=rtc_config.execution_horizon)` when RTC is enabled.
- `_make_warmup_rtc_prefix()` builds a dummy leftover prefix with length `rtc_config.execution_horizon` and action dim from `policy.config.action_feature`.
- Relative-action policies re-anchor the dummy prefix through `reanchor_relative_rtc_prefix(...)` after preprocessing caches the dummy state.
- `_synchronize_policy_device()` uses `torch.cuda.synchronize()` around timed CUDA work when the requested policy device is CUDA.
- Warmup is wrapped in `try/except`; failure logs `Policy warmup failed; continuing without warmup` and does not kill the server.
- `_reset_rtc_state()` runs after warmup, including on failure, so the discard forwards do not populate RTC queue or latency state.

Expected log shape:

```text
Policy warmup: preprocess <X>ms, no-prefix <Y>ms, guided RTC <Z>ms
```

If RTC is disabled or unavailable:

```text
Policy warmup: preprocess <X>ms, no-prefix <Y>ms, guided RTC skipped
```

## Real-policy no-robot smoke

Command environment:

```bash
CUDA_VISIBLE_DEVICES=1 \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python ...
```

The smoke instantiated `PolicyServer`, sent a local `RemotePolicyConfig`, let `SendPolicyInstructions` execute the new warmup, then timed one no-prefix and one guided RTC forward after warmup.

Observed policy schema:

| feature | shape |
|---|---:|
| `observation.state` | `(16,)` |
| `observation.images.left_wrist` | `(3, 720, 1280)` |
| `observation.images.right_wrist` | `(3, 720, 1280)` |
| `observation.images.base` | `(3, 480, 640)` |

Observed RTC config:

- `enabled=True`
- `execution_horizon=20`
- `max_guidance_weight=10.0`
- `prefix_attention_schedule=RTCAttentionSchedule.EXP`

Smoke logs:

```text
Injected robot-folding RTCConfig: enabled=True | execution_horizon=20 | max_guidance_weight=10.0 | prefix_attention_schedule=RTCAttentionSchedule.EXP
RTC processor initialized on policy and model
RTC relative-action prefix re-anchoring enabled
Policy warmup: preprocess 144.27ms, no-prefix 2138.93ms, guided RTC 405.79ms
Time taken to put policy on cuda: 113.4595 seconds
```

Post-warmup first forwards:

| path | latency |
|---|---:|
| first no-prefix after warmup | `333.38 ms` |
| first guided RTC after warmup | `398.03 ms` |

Interpretation:

- The warmup paid the cold CUDA/autograd cost before any client action chunk.
- The first guided RTC forward after warmup is in the K6 warm band, about `0.4s`, not the D07 cold `1.5-1.7s` band.
- The no-prefix warmup absorbed most of the cold cost in this run; the guided discard still executes and verifies the RTC/autograd path before motion.

## Compatibility checks

Final commands:

```bash
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
  uv run --no-sync python -m py_compile src/lerobot/async_inference/policy_server.py
```

Result: pass.

```bash
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
  uv run --with ruff --no-sync ruff check src/lerobot/async_inference/policy_server.py
```

Result: `All checks passed!`

```bash
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
  uv run --with pytest --no-sync pytest tests/async_inference/test_policy_server.py -q
```

Result: `6 passed in 0.30s`.

Additional lightweight smoke:

- RTC enabled mock policy received two calls:
  - `{}` no-prefix call,
  - guided RTC kwargs with `prev_chunk_left_over`, `inference_delay=0`, and `execution_horizon`.
- RTC disabled mock policy received one no-prefix call and skipped guided RTC.

## Restart status

The running `k1_policy_server` was intentionally left alive during implementation and verification.

After this K8a commit is pushed, restart target:

- tmux session: `k1_policy_server`
- bind: `0.0.0.0:8081`
- venv: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- expected first policy-load log: `Policy warmup: preprocess ..., no-prefix ..., guided RTC ...`

## Next

- Restart `k1_policy_server` with K8a code on a free GPU.
- Let syhlabtop K1c connect normally; the client remains thin and will send `RemotePolicyConfig`.
- Confirm the first live chunk remains in the warm band before D07 motion.
