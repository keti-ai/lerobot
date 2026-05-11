from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

import stage22_dataset_replay_and_ablation as replay


def iter_state_action_rows(dataset_root: Path, max_rows: int) -> tuple[np.ndarray, np.ndarray]:
    states: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    for path in sorted((dataset_root / "data").glob("**/*.parquet")):
        import pyarrow.parquet as pq

        table = pq.read_table(path, columns=["observation.state", "action"])
        for row in table.to_pylist():
            states.append(replay.vector(row["observation.state"]))
            actions.append(replay.vector(row["action"]))
            if max_rows > 0 and len(states) >= max_rows:
                break
        if max_rows > 0 and len(states) >= max_rows:
            break
    if not states:
        raise ValueError(f"No state/action rows found under {dataset_root / 'data'}")
    return np.stack(states), np.stack(actions)


def keyed(values: np.ndarray) -> dict[str, float]:
    return {name: float(values[i]) for i, name in enumerate(replay.ACTION_NAMES)}


def summarize(values: np.ndarray) -> dict[str, Any]:
    q01 = np.percentile(values, 1, axis=0)
    q50 = np.percentile(values, 50, axis=0)
    q99 = np.percentile(values, 99, axis=0)
    return {
        "q01": keyed(q01),
        "q50": keyed(q50),
        "q99": keyed(q99),
        "span_q99_minus_q01": keyed(q99 - q01),
        "mean_abs": keyed(np.mean(np.abs(values), axis=0)),
        "max_abs": keyed(np.max(np.abs(values), axis=0)),
    }


def build_payload(dataset_repo: str, dataset_root: Path, max_rows: int) -> dict[str, Any]:
    info = replay.read_info(dataset_root)
    states, actions = iter_state_action_rows(dataset_root, max_rows=max_rows)
    relative = actions - states
    arm_relative = np.abs(relative[:, replay.ARM_ACTION_MASK])
    arm_idx = np.unravel_index(int(np.argmax(arm_relative)), arm_relative.shape)
    arm_names = np.asarray(replay.ACTION_NAMES)[replay.ARM_ACTION_MASK]
    return {
        "dataset_repo": dataset_repo,
        "dataset_root": str(dataset_root),
        "rows": int(relative.shape[0]),
        "max_rows_requested": int(max_rows),
        "robot_type": info.get("robot_type"),
        "features_action_names": info.get("features", {}).get("action", {}).get("names"),
        "locked_recipe": replay.LOCKED_FOLDING_RECIPE,
        "source_map": replay.FOLDING_RECIPE_SOURCE_MAP,
        "absolute_action_stats": summarize(actions),
        "relative_action_stats": summarize(relative),
        "state_stats": summarize(states),
        "arm_relative_summary": {
            "mean_abs_delta_deg": float(np.mean(arm_relative)),
            "p99_abs_delta_deg": float(np.percentile(arm_relative, 99)),
            "max_abs_delta_deg": float(arm_relative[arm_idx]),
            "max_abs_delta_key": str(arm_names[arm_idx[1]]),
        },
        "safety": {
            "model_weights_loaded": False,
            "videos_loaded": False,
            "robot_io": False,
            "send_action": False,
            "artifact_mutation": False,
        },
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    rel = payload["arm_relative_summary"]
    lines = [
        "# Stage 30 Relative Recipe Reference",
        "",
        "## Decision",
        "",
        "This file is a training/export reference only. It is not a deployable checkpoint mutation.",
        "A corrected checkpoint still must pass Stage 29 recipe gate and Stage 31 dataset replay.",
        "",
        "## Dataset",
        "",
        f"- Dataset: `{payload['dataset_repo']}`",
        f"- Rows sampled: `{payload['rows']}`",
        f"- Robot type: `{payload['robot_type']}`",
        "",
        "## Relative Action Summary",
        "",
        f"- Arm mean abs delta: `{rel['mean_abs_delta_deg']:.3f}` deg",
        f"- Arm p99 abs delta: `{rel['p99_abs_delta_deg']:.3f}` deg",
        f"- Arm max abs delta: `{rel['max_abs_delta_deg']:.3f}` deg at `{rel['max_abs_delta_key']}`",
        "",
        "## Required Alignment",
        "",
        "- `policy.use_relative_actions=true`",
        "- `policy.relative_exclude_joints=[\"gripper\"]`",
        "- postprocessor action stats must match `relative_action_stats`, not `absolute_action_stats`",
        "- processor-only stat swapping remains blocked for deployment; retrain or re-export from the corrected recipe",
        "",
        "## Safety",
        "",
        "- No model weights, videos, robot connection, torque, zeroing, or action send were used.",
    ]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write relative-action recipe stats for OpenArm folding retrain/export.")
    parser.add_argument("--dataset-repo", default="lerobot-data-collection/level2_final_quality3_t_0_hil_data_c")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--dataset-revision")
    parser.add_argument("--max-rows", type=int, default=0, help="0 means all available rows")
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    dataset_root = replay.resolve_dataset_root(args.dataset_repo, args.dataset_root, args.dataset_revision)
    payload = build_payload(args.dataset_repo, dataset_root, max_rows=args.max_rows)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out), "rows": payload["rows"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
