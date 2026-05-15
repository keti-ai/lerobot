from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import torch
from huggingface_hub import snapshot_download
from PIL import Image

from lerobot.configs import PreTrainedConfig
from lerobot.policies import get_policy_class, make_pre_post_processors
from lerobot.policies.utils import prepare_observation_for_inference
from lerobot.processor import policy_action_to_transition, transition_to_policy_action
from lerobot.processor.relative_action_processor import RelativeActionsProcessorStep
from lerobot.types import TransitionKey


DEFAULT_ACTION_NAMES = [
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
    "right_gripper.pos",
    "left_joint_1.pos",
    "left_joint_2.pos",
    "left_joint_3.pos",
    "left_joint_4.pos",
    "left_joint_5.pos",
    "left_joint_6.pos",
    "left_joint_7.pos",
    "left_gripper.pos",
]


def read_state_csv(path: Path) -> np.ndarray:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"Empty state csv: {path}")
    values = rows[1] if rows[0] == DEFAULT_ACTION_NAMES else rows[0]
    state = np.asarray([float(v) for v in values], dtype=np.float32)
    if state.shape != (len(DEFAULT_ACTION_NAMES),):
        raise ValueError(f"Expected {len(DEFAULT_ACTION_NAMES)} state values, got {state.shape}")
    return state


def read_image(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def read_review_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    by_key = {row["key"]: row for row in rows if int(row["action_id"]) == 0}
    missing = [key for key in DEFAULT_ACTION_NAMES if key not in by_key]
    if missing:
        raise ValueError(f"{path} missing rows: {missing}")
    return [
        {
            "key": key,
            "current_deg": float(by_key[key]["current_deg"]),
            "proposed_deg": float(by_key[key]["proposed_deg"]),
            "clamped_deg": float(by_key[key]["clamped_deg"]),
            "delta_deg": float(by_key[key]["delta_deg"]),
        }
        for key in DEFAULT_ACTION_NAMES
    ]


def resolve_dataset_root(repo_id: str, root: Path | None, revision: str | None) -> Path:
    if root is not None and (root / "data").exists() and (root / "meta").exists():
        return root
    if root is None:
        raise ValueError("--dataset-root is required when dataset is not already downloaded")
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        local_dir=root,
        allow_patterns=["meta/**", "data/**", "README.md"],
        ignore_patterns=["videos/**"],
    )
    return root


def parquet_files(dataset_root: Path) -> list[Path]:
    return sorted((dataset_root / "data").glob("**/*.parquet"))


def as_vector(value: Any) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float32)
    if arr.ndim == 0:
        raise ValueError(f"Expected vector, got scalar {value!r}")
    return arr.reshape(-1)


def iter_dataset_rows(dataset_root: Path, max_rows: int, episodes: set[int] | None) -> Iterable[dict[str, Any]]:
    yielded = 0
    for path in parquet_files(dataset_root):
        table = pq.read_table(path)
        for row in table.to_pylist():
            if episodes is not None and "episode_index" in row and int(row["episode_index"]) not in episodes:
                continue
            yield row
            yielded += 1
            if yielded >= max_rows:
                return


def load_dataset_arrays(dataset_root: Path, max_rows: int, episodes: set[int] | None) -> tuple[np.ndarray, np.ndarray]:
    states: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    for row in iter_dataset_rows(dataset_root, max_rows, episodes):
        if "observation.state" not in row or "action" not in row:
            raise KeyError("Dataset row must contain observation.state and action")
        states.append(as_vector(row["observation.state"]))
        actions.append(as_vector(row["action"]))
    if not states:
        raise ValueError("No dataset rows loaded")
    return np.stack(states), np.stack(actions)


def stats(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "p01": float(np.percentile(values, 1)),
        "p05": float(np.percentile(values, 5)),
        "median": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }


def build_contract_report(
    states: np.ndarray,
    actions: np.ndarray,
    action_names: list[str],
    reviews: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    deltas = actions - states
    rows = []
    for idx, key in enumerate(action_names):
        is_gripper = "gripper" in key
        delta_values = deltas[:, idx]
        state_values = states[:, idx]
        action_values = actions[:, idx]
        row = {
            "key": key,
            "is_gripper": is_gripper,
            "dataset_state": stats(state_values),
            "dataset_action": stats(action_values),
            "dataset_action_minus_state": stats(delta_values),
            "snapshots": {},
        }
        for review_name, review_rows in reviews.items():
            review_row = next(item for item in review_rows if item["key"] == key)
            value = review_row["delta_deg"]
            abs_distribution = np.abs(delta_values)
            abs_value = abs(value)
            percentile = float(np.mean(abs_distribution <= abs_value) * 100.0)
            current = review_row["current_deg"]
            state_percentile = float(np.mean(state_values <= current) * 100.0)
            row["snapshots"][review_name] = {
                "current_deg": current,
                "proposed_deg": review_row["proposed_deg"],
                "delta_deg": value,
                "abs_delta_dataset_percentile": percentile,
                "current_state_dataset_percentile": state_percentile,
                "outside_dataset_state_minmax": bool(current < np.min(state_values) or current > np.max(state_values)),
            }
        rows.append(row)
    return {
        "dataset_rows": int(states.shape[0]),
        "feature_count": int(states.shape[1]),
        "rows": rows,
    }


def load_model_and_processors(model_dir: Path, device: str):
    cfg = PreTrainedConfig.from_pretrained(model_dir)
    cfg.device = device
    if hasattr(cfg, "compile_model"):
        cfg.compile_model = False
    policy_cls = get_policy_class(cfg.type)
    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=cfg,
        pretrained_path=str(model_dir),
        preprocessor_overrides={"device_processor": {"device": device}},
        postprocessor_overrides={"device_processor": {"device": "cpu"}},
    )
    policy = policy_cls.from_pretrained(str(model_dir), config=cfg, local_files_only=True)
    policy.eval()
    return cfg, policy, preprocessor, postprocessor


def find_relative_step(preprocessor) -> RelativeActionsProcessorStep:
    for step in preprocessor.steps:
        if isinstance(step, RelativeActionsProcessorStep):
            return step
    raise RuntimeError("No RelativeActionsProcessorStep in preprocessor")


def run_postprocess_probe(model_dir: Path, snapshot_dir: Path, device: str, action_names: list[str]) -> dict[str, Any]:
    cfg, policy, preprocessor, postprocessor = load_model_and_processors(model_dir, device)
    metadata_path = snapshot_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    state = read_state_csv(snapshot_dir / "state_16.csv")
    observation = {
        "observation.state": state,
        "observation.images.left_wrist": read_image(snapshot_dir / "left_wrist.png"),
        "observation.images.right_wrist": read_image(snapshot_dir / "right_wrist.png"),
        "observation.images.base": read_image(snapshot_dir / "base.png"),
    }
    prepared = prepare_observation_for_inference(
        observation,
        device=torch.device(device),
        task=metadata.get("task", "Fold the T-shirt properly"),
        robot_type=metadata.get("robot_type", "openarms_follower"),
    )
    with torch.inference_mode():
        preprocessed = preprocessor(prepared)
        model_action = policy.predict_action_chunk(preprocessed)

    relative_step = find_relative_step(preprocessor)
    cached_state = relative_step.get_cached_state()
    if cached_state is None:
        raise RuntimeError("Relative step did not cache state")

    transition = policy_action_to_transition(model_action)
    unnormalized_transition = postprocessor.steps[0](transition)
    unnormalized_relative = transition_to_policy_action(unnormalized_transition)
    absolute_transition = postprocessor.steps[1](unnormalized_transition)
    absolute_action = transition_to_policy_action(absolute_transition)
    full_postprocessed = postprocessor(model_action)

    rel0 = unnormalized_relative[0, 0].detach().cpu().numpy()
    abs0 = absolute_action[0, 0].detach().cpu().numpy()
    full0 = full_postprocessed[0, 0].detach().cpu().numpy()
    state0 = cached_state[0].detach().cpu().numpy()
    mask = np.asarray(relative_step._build_mask(len(action_names)), dtype=bool)
    reconstructed = rel0.copy()
    reconstructed[mask] = rel0[mask] + state0[: len(action_names)][mask]
    max_reconstruction_error = float(np.max(np.abs(reconstructed - abs0)))
    max_full_postprocess_error = float(np.max(np.abs(full0 - abs0)))

    rows = []
    for idx, key in enumerate(action_names):
        rows.append(
            {
                "key": key,
                "mask_relative": bool(mask[idx]),
                "cached_state_deg": float(state0[idx]),
                "unnormalized_relative_deg": float(rel0[idx]),
                "absolute_deg": float(abs0[idx]),
                "absolute_minus_state_deg": float(abs0[idx] - state0[idx]),
                "reconstruction_error_deg": float(reconstructed[idx] - abs0[idx]),
            }
        )

    return {
        "snapshot_dir": str(snapshot_dir),
        "model_dir": str(model_dir),
        "policy_type": cfg.type,
        "use_relative_actions": bool(getattr(cfg, "use_relative_actions", False)),
        "relative_exclude_joints": list(getattr(cfg, "relative_exclude_joints", [])),
        "action_shape": list(absolute_action.shape),
        "max_reconstruction_error_deg": max_reconstruction_error,
        "max_full_postprocess_error_deg": max_full_postprocess_error,
        "rows": rows,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 21 Action Contract Diagnosis",
        "",
        f"Dataset rows: {payload['dataset_contract']['dataset_rows']}",
        f"Feature count: {payload['dataset_contract']['feature_count']}",
        "",
        "## Snapshot Summary",
        "",
    ]
    for name, summary in payload["snapshot_summaries"].items():
        lines.append(
            f"- `{name}`: mean_abs_delta={summary['mean_abs_delta_deg']:.3f}, "
            f"max_abs_delta={summary['max_abs_delta_deg']:.3f} at `{summary['max_abs_delta_key']}`"
        )
    lines.extend(["", "## Postprocess Check", ""])
    for name, probe in payload["postprocess_probes"].items():
        lines.append(
            f"- `{name}`: max reconstruction error "
            f"{probe['max_reconstruction_error_deg']:.6f} deg; "
            f"full postprocess error {probe['max_full_postprocess_error_deg']:.6f} deg"
        )
    lines.extend(["", "## Highest Snapshot Delta Percentiles", ""])
    ranked = []
    for row in payload["dataset_contract"]["rows"]:
        for snapshot_name, snap in row["snapshots"].items():
            ranked.append((abs(snap["delta_deg"]), row["key"], snapshot_name, snap))
    for _, key, snapshot_name, snap in sorted(ranked, reverse=True)[:20]:
        lines.append(
            f"- `{snapshot_name}` `{key}` delta={snap['delta_deg']:.3f} deg, "
            f"abs percentile={snap['abs_delta_dataset_percentile']:.1f}, "
            f"state percentile={snap['current_state_dataset_percentile']:.1f}, "
            f"state_outside_minmax={snap['outside_dataset_state_minmax']}"
        )
    path.write_text("\n".join(lines) + "\n")


def summarize_review(rows: list[dict[str, Any]]) -> dict[str, Any]:
    abs_deltas = [abs(row["delta_deg"]) for row in rows]
    idx = int(np.argmax(abs_deltas))
    return {
        "mean_abs_delta_deg": float(np.mean(abs_deltas)),
        "max_abs_delta_deg": float(abs_deltas[idx]),
        "max_abs_delta_key": rows[idx]["key"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose LeRobot folding state/action contract without robot IO.")
    parser.add_argument("--dataset-repo", default="lerobot/full_folding")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--dataset-revision")
    parser.add_argument("--max-dataset-rows", type=int, default=2000)
    parser.add_argument("--episodes", default="0")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--snapshot", action="append", nargs=3, metavar=("NAME", "SNAPSHOT_DIR", "REVIEW_CSV"))
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    if not args.snapshot:
        raise SystemExit("At least one --snapshot NAME SNAPSHOT_DIR REVIEW_CSV is required")
    if args.max_dataset_rows <= 0:
        raise SystemExit("--max-dataset-rows must be positive")

    episodes = None if args.episodes.lower() in {"", "all", "none"} else {int(x) for x in args.episodes.split(",")}
    action_names = DEFAULT_ACTION_NAMES
    dataset_root = resolve_dataset_root(args.dataset_repo, args.dataset_root, args.dataset_revision)
    states, actions = load_dataset_arrays(dataset_root, args.max_dataset_rows, episodes)
    if states.shape[1] != len(action_names) or actions.shape[1] != len(action_names):
        raise SystemExit(f"Expected 16-dim state/action, got state={states.shape}, action={actions.shape}")

    reviews = {}
    snapshot_dirs = {}
    for name, snapshot_dir, review_csv in args.snapshot:
        reviews[name] = read_review_csv(Path(review_csv))
        snapshot_dirs[name] = Path(snapshot_dir)

    payload = {
        "dataset_repo": args.dataset_repo,
        "dataset_root": str(dataset_root),
        "episodes": sorted(episodes) if episodes is not None else "all",
        "max_dataset_rows": args.max_dataset_rows,
        "action_names": action_names,
        "dataset_contract": build_contract_report(states, actions, action_names, reviews),
        "snapshot_summaries": {name: summarize_review(rows) for name, rows in reviews.items()},
        "postprocess_probes": {
            name: run_postprocess_probe(args.model_dir, snapshot_dir, args.device, action_names)
            for name, snapshot_dir in snapshot_dirs.items()
        },
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    print(json.dumps({k: v for k, v in payload.items() if k not in {"dataset_contract", "postprocess_probes"}}, indent=2))
    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
