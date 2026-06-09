# a6000 K7 RTC async server integration

Executed: 2026-06-09 KST

## Checkpoint RTC state

- Branch baseline before edit: `ef232ad5`
- α'' checkpoint:
  `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232/checkpoints/030000/pretrained_model`
- `config.json`: `"rtc_config": null`
- `train_config.json`: `"rtc_config": null`
- Result: K7 server-side injection is required for this PI0.5 checkpoint.

## K7 implementation

- `SendPolicyInstructions`: after `from_pretrained()` and `.to(device)`, policy-side RTC is configured before processor construction.
- `_configure_rtc_policy`: injects robot-folding RTC only for RTC-capable `pi05` policies whose config has `rtc_config=None`:
  - `enabled=True`
  - `execution_horizon=20`
  - `max_guidance_weight=10.0`
  - `prefix_attention_schedule=RTCAttentionSchedule.EXP`
  - calls `policy.init_rtc_processor()` and verifies the processor is attached to both policy and model.
- `_configure_rtc_processors`: creates `ActionQueue`, resets `LatencyTracker`, finds enabled `RelativeActionsProcessorStep`, finds `NormalizerProcessorStep`, and fills relative action names from policy config when needed.
- `_get_action_chunk`: in RTC mode, passes `prev_chunk_left_over`, `inference_delay`, and `execution_horizon` to `predict_action_chunk`; relative-action leftovers are re-anchored through `reanchor_relative_rtc_prefix`.
- `_predict_action_chunk` / `_merge_rtc_action_chunk`: keeps the existing postprocessing/client output path, then stores model-space and processed action chunks with `ActionQueue.merge(...)` and records latency with `LatencyTracker`.
- Non-RTC behavior is preserved for policies without RTC support or with disabled RTC config: `predict_action_chunk(observation)` is called without RTC kwargs.

## Verification

Commands ran under the torch 2.11 async-serving venv:

```bash
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
  uv run --no-sync python -m py_compile src/lerobot/async_inference/policy_server.py
```

Result: pass.

```bash
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
  uv run --with pytest --no-sync pytest tests/async_inference/test_policy_server.py -q
```

Result: `6 passed in 0.61s`.

```bash
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
  uv run --with ruff --no-sync ruff check src/lerobot/async_inference/policy_server.py
```

Result: `All checks passed!`

Standalone no-robot smoke validated:

- `pi05` + `rtc_config=None` injects the K7 RTC recipe.
- `init_rtc_processor()` attaches a processor to both policy and model.
- First chunk passes `prev_chunk_left_over=None`.
- Second chunk receives re-anchored relative leftovers.
- `inference_delay` and `execution_horizon=20` are forwarded.
- Non-RTC policy receives no extra kwargs.

Observed RTC logs from the smoke:

```text
Injected robot-folding RTCConfig: enabled=True | execution_horizon=20 | max_guidance_weight=10.0 | prefix_attention_schedule=RTCAttentionSchedule.EXP
RTC processor initialized on policy and model
RTC relative-action prefix re-anchoring enabled
RTC action queue merged | latency=0.0000s | real_delay=0 | remaining_actions=4
```

## RTCInferenceEngine adaptation

- Reused the same RTC primitives: `ActionQueue`, `LatencyTracker`, `RTCConfig`, and `reanchor_relative_rtc_prefix`.
- Kept the async server/client contract unchanged; `robot_client.py` remains thin and unmodified.
- The rollout `RTCInferenceEngine` consumes actions locally and can compare queue indices during inference. The async server does not execute actions locally, so it stores each generated server chunk and uses measured inference latency to trim the next prefix through `ActionQueue.merge`.
- No RTC background thread, queue threshold, compile warmup, or robot wrapper logic was added to `policy_server`.
- Existing `k1_policy_server` tmux was not restarted during K7; no live motion was run.

## Next

- Restart `k1_policy_server` with this commit so the server logs show RTC injection for the α'' PI0.5 policy load.
- Run D07 with operator on site: syhlabtop K1c client to the restarted server, arm15/grip65 cap, banana trial, compare chunk-boundary smoothness against D04/D05.
