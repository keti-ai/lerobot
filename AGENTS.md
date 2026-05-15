This file provides guidance to AI agents when working with code in this repository.

> **User-facing help → [`AGENT_GUIDE.md`](./AGENT_GUIDE.md)** (SO-101 setup, recording, picking a policy, training duration, eval — with copy-pasteable commands).

## Project Overview

LeRobot is a PyTorch-based library for real-world robotics, providing datasets, pretrained policies, and tools for training, evaluation, data collection, and robot control. It integrates with Hugging Face Hub for model/dataset sharing.

## Tech Stack

Python 3.12+ · PyTorch · Hugging Face (datasets, Hub, accelerate) · draccus (config/CLI) · Gymnasium (envs) · uv (package management)

## Development Setup

```bash
uv sync --locked                            # Base dependencies
uv sync --locked --extra test --extra dev   # Test + dev tools
uv sync --locked --extra all                # Everything
git lfs install && git lfs pull             # Test artifacts
```

## Key Commands

```bash
uv run pytest tests -svv --maxfail=10                 # All tests
DEVICE=cuda make test-end-to-end                      # All E2E tests
pre-commit run --all-files                           # Lint + format (ruff, typos, bandit, etc.)
```

## Architecture (`src/lerobot/`)

- **`scripts/`** — CLI entry points (`lerobot-train`, `lerobot-eval`, `lerobot-record`, etc.), mapped in `pyproject.toml [project.scripts]`.
- **`configs/`** — Dataclass configs parsed by draccus. `train.py` has `TrainPipelineConfig` (top-level). `policies.py` has `PreTrainedConfig` base. Polymorphism via `draccus.ChoiceRegistry` with `@register_subclass("name")` decorators.
- **`policies/`** — Each policy in its own subdir. All inherit `PreTrainedPolicy` (`nn.Module` + `HubMixin`) from `pretrained.py`. Factory with lazy imports in `factory.py`.
- **`processor/`** — Data transformation pipeline. `ProcessorStep` base with registry. `DataProcessorPipeline` / `PolicyProcessorPipeline` chain steps.
- **`datasets/`** — `LeRobotDataset` (episode-aware sampling + video decoding) and `LeRobotDatasetMetadata`.
- **`envs/`** — `EnvConfig` base in `configs.py`, factory in `factory.py`. Each env subclass defines `gym_kwargs` and `create_envs()`.
- **`robots/`, `motors/`, `cameras/`, `teleoperators/`** — Hardware abstraction layers.
- **`types.py`** and **`configs/types.py`** — Core type aliases and feature type definitions.

## Repository Structure (outside `src/`)

- **`tests/`** — Pytest suite organized by module. Fixtures in `tests/fixtures/`, mocks in `tests/mocks/`. Hardware tests use skip decorators from `tests/utils.py`. E2E tests via `Makefile` write to `tests/outputs/`.
- **`.github/workflows/`** — CI: `quality.yml` (pre-commit), `fast_tests.yml` (base deps, every PR), `full_tests.yml` (all extras + E2E + GPU, post-approval), `latest_deps_tests.yml` (daily lockfile upgrade), `security.yml` (TruffleHog), `release.yml` (PyPI publish on tags).
- **`docs/source/`** — HF documentation (`.mdx` files). Per-policy READMEs, hardware guides, tutorials. Built separately via `docs-requirements.txt` and CI workflows.
- **`examples/`** — End-user tutorials and scripts organized by use case (dataset creation, training, hardware setup).
- **`docker/`** — Dockerfiles for user (`Dockerfile.user`) and CI (`Dockerfile.internal`).
- **`benchmarks/`** — Performance benchmarking scripts.
- **Root files**: `pyproject.toml` (single source of truth for deps, build, tool config), `Makefile` (E2E test targets), `uv.lock`, `CONTRIBUTING.md` & `README.md` (general information).

## Notes

- **Mypy is gradual**: strict only for `lerobot.envs`, `lerobot.configs`, `lerobot.optim`, `lerobot.model`, `lerobot.cameras`, `lerobot.motors`, `lerobot.transport`. Add type annotations when modifying these modules.
- **Optional dependencies**: many policies, envs, and robots are behind extras (e.g., `lerobot[aloha]`). New imports for optional packages must be guarded or lazy. See `pyproject.toml [project.optional-dependencies]`.
- **Video decoding**: datasets can store observations as video files. `LeRobotDataset` handles frame extraction, but tests need ffmpeg installed.
- **Prioritize use of `uv run`** to execute Python commands (not raw `python` or `pip`).

---

## OpenArm Fork Operations

This fork adds OpenArm folding deployment work on top of upstream LeRobot.
The single source of truth is **`docs/PLAN.md`** (strategy) and **`docs/STATUS.md`**
(current state). Reference these before any change.

### Fork-specific directories

- `audits/openarm_folding/` — current operational docs and live scripts (8 md + 8 py + 1 sh).
- `audits/openarm_printing/` — 3D-print plans for OpenArm hardware (mini teleop, Arducam holder).
- `bashs/` — shell wrappers for SO-101/OpenArm training, eval, data collection (cali.sh, run_train_*.sh, tele.sh).
- `cali/lerobot/` — calibration data captured for connected motors/cameras.
- `outputs/` — training outputs (gitignored). Do not commit.
- `docs/_archive/openarm_folding/` — historical Stage10–40 work, kept for git history. See `docs/_archive/INDEX.md`.

### Hard rules (no exceptions without explicit operator approval)

1. **`new_stage_numbers: forbidden`** — do not introduce new `stage*` files.
   Use `rollout_trial_<timestamp>/` for new sessions.
2. **Never call `OpenArmFollower.connect()` on the rollout path** — it triggers
   `set_zero_position` and `enable_torque`.
3. **Never use `send_action()` or `lerobot-rollout` for actual motion** — both
   reach `robot.send_action()` and bypass the guarded path.
4. **Stage35–40 packet artifacts are consumed history** — never reuse.
5. **Any motion needs an operator approval envelope** generated by
   `audits/openarm_folding/syhlabtop_live_guarded_rollout.py` in draft mode first.
6. **`full_folding` checkpoint `004000` is NOT a deploy candidate** (replay gate
   FAIL, delta ratio 0.128–0.282 vs threshold 0.25–4.0).
7. **A6000 server requires HF offline env vars**: `HF_HOME=/mnt/nas/huggingface`,
   `HF_HUB_CACHE=/mnt/nas/huggingface/hub`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.
8. **Do not change Damiao motor persistent settings** before physical axis sign probe.

### Tracks

| Track | Goal | State |
|---|---|---|
| A | level2 live rollout on real robot | unblocked, awaiting axis probe + camera align |
| B | full_folding retrain | complete, replay FAIL → not a deploy candidate |
| C | full_folding ckpt 002000/003000 replay gate compare | not started |
| D | axis direction probe + base camera alignment | not started |

### Hardware contract (16D action / state)

```
order:   right_joint_{1..7}.pos, right_gripper.pos,
         left_joint_{1..7}.pos,  left_gripper.pos
units:   degrees
gripper: [-65, 0] deg (larger jaws installed)
chunk:   30
runtime: absolute targets (A6000 postprocessor converts relative→absolute)
buses:   right=can1, left=can0
motors:  J1-2 dm8009, J3-4 dm4340, J5-7/gripper dm4310 (both sides)
cameras: left_wrist=315122270766, right_wrist=230322273311, base=213622075840
```

### Current serving checkpoint

```
http://10.252.205.103:8766  (live)
http://10.252.205.103:8765  (snapshot backup)

model: pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
gate:  recipe PASS, replay PASS
loss:  0.066 at step 4000/4000
```
