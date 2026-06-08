# a6000 K1 async inference server

Executed: 2026-06-08 20:33 KST

## Hugging Face push

- Checkpoint: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_clean_alpha2prime_20260605_015232/checkpoints/030000/pretrained_model`
- Repo: <https://huggingface.co/KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime>
- Repo type: model
- Private: `True`
- File count: `8`
- `model.safetensors`: present
- Upload commit message: `α'' 030000 — handover v0 clean 60 ep multi3 30k`

Verified repo files:

```text
.gitattributes
config.json
model.safetensors
policy_postprocessor.json
policy_postprocessor_step_0_unnormalizer_processor.safetensors
policy_preprocessor.json
policy_preprocessor_step_3_normalizer_processor.safetensors
train_config.json
```

## policy_server

- tmux session: `k1_policy_server`
- Log: `/tmp/k1_server_logs/policy_server_20260608_203241.log`
- Bind: `0.0.0.0:8081`
- K1c endpoint: `10.252.205.103:8081`
- Note: `8080` was already occupied by another user's `code-server`, so K1 server was started on confirmed-free port `8081`. Existing `8765/8766` serving ports were not used.

Command:

```bash
CUDA_VISIBLE_DEVICES=0 \
UV_CACHE_DIR=/tmp/uv-cache \
UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515 \
uv run --no-sync python -m lerobot.async_inference.policy_server \
  --host=0.0.0.0 \
  --port=8081 \
  --fps=30
```

Startup log:

```text
INFO 2026-06-08 20:32:46 y_server.py:420 {'fps': 30,
 'host': '0.0.0.0',
 'inference_latency': 0.03333333333333333,
 'obs_queue_timeout': 2,
 'port': 8081}
INFO 2026-06-08 20:32:46 y_server.py:430 PolicyServer started on 0.0.0.0:8081
```

Port verification:

```text
LISTEN 0      4096                    *:8081             *:*    users:(("python3",pid=3274265,fd=7))
```

## GPU selection and impact

- Selected GPU: `0`
- Reason: GPU 0 satisfied the policy threshold with `44768 MB` free and `0%` utilization.
- All GPUs were checked before and after start:

```text
0, 44768, 0
1, 48262, 0
2, 48262, 0
3, 48262, 0
```

- Existing low-memory colleague processes were left untouched; no high-utilization training workload was present.
- No colleague service was stopped or moved. The existing `8080` code-server listener was left untouched.
- policy_server did not reduce reported free GPU memory after startup because the server waits for the client-provided `pretrained_name_or_path` before loading a policy.

## Next

- K1c syhlabtop should run `robot_client` against `10.252.205.103:8081`.
