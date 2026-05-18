from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from huggingface_hub import snapshot_download

import stage22_dataset_replay_and_ablation as replay
from lerobot.configs import PreTrainedConfig


DEFAULT_CANDIDATES = [
    "lerobot/folding_latest",
    "lerobot-data-collection/folding_final10",
    "lerobot-data-collection/folding_final",
    "lerobot-data-collection/ablation2-5_0",
]

LIGHTWEIGHT_MODEL_PATTERNS = [
    "config.json",
    "train_config.json",
    "policy_preprocessor.json",
    "policy_postprocessor.json",
    "policy_preprocessor_step_*_normalizer_processor.safetensors",
    "policy_postprocessor_step_*_unnormalizer_processor.safetensors",
    "README.md",
]


@dataclass(frozen=True)
class Candidate:
    name: str
    path: Path
    source: str
    revision: str | None = None


def parse_candidate(raw: str) -> tuple[str, str | None]:
    if "@" not in raw:
        return raw, None
    repo_id, revision = raw.rsplit("@", 1)
    return repo_id, revision


def candidate_name(raw: str) -> str:
    return raw.replace("/", "__").replace("@", "__")


def resolve_candidate(raw: str, cache_dir: Path, local_only: bool) -> Candidate:
    path = Path(raw)
    if path.exists():
        return Candidate(name=path.name, path=path, source="local")
    if local_only:
        raise FileNotFoundError(f"Candidate is not a local path and --local-only is set: {raw}")
    repo_id, revision = parse_candidate(raw)
    local_dir = cache_dir / candidate_name(raw)
    snapshot_download(
        repo_id=repo_id,
        repo_type="model",
        revision=revision,
        local_dir=local_dir,
        allow_patterns=LIGHTWEIGHT_MODEL_PATTERNS,
        ignore_patterns=["model.safetensors", "*.bin", "*.pt", "*.pth"],
    )
    return Candidate(name=raw, path=local_dir, source="hub", revision=revision)


def gate_candidate(
    candidate: Candidate,
    *,
    dataset_repo: str,
    dataset_root: Path,
    info: dict[str, Any],
    max_rows: int,
    relative_stats_tolerance_deg: float,
    action_span_ratio_limit: float,
    action_is_relative: bool,
    action_is_relative_source: str,
) -> dict[str, Any]:
    cfg = PreTrainedConfig.from_pretrained(candidate.path)
    gate = replay.validate_folding_recipe(
        cfg=cfg,
        model_dir=candidate.path,
        dataset_repo=dataset_repo,
        dataset_root=dataset_root,
        info=info,
        max_rows=max_rows,
        relative_stats_tolerance_deg=relative_stats_tolerance_deg,
        action_span_ratio_limit=action_span_ratio_limit,
        action_is_relative=action_is_relative,
        action_is_relative_source=action_is_relative_source,
    )
    failed_checks = set(gate["summary"]["failed_checks"])
    recipe_failures_without_dataset = sorted(failed_checks - {"model_training_dataset_matches_replay_dataset"})
    train_dataset_repo = None
    relative_stats = None
    for check in gate["checks"]:
        if check["name"] == "model_training_dataset_matches_replay_dataset":
            train_dataset_repo = check.get("train_dataset_repo")
        elif check["name"] == "postprocessor_action_stats_are_relative_for_arm_joints":
            relative_stats = {
                "max_post_vs_relative_q01_error_deg": check.get("max_post_vs_relative_q01_error_deg"),
                "max_post_vs_relative_q99_error_deg": check.get("max_post_vs_relative_q99_error_deg"),
                "max_post_vs_absolute_q01_error_deg": check.get("max_post_vs_absolute_q01_error_deg"),
                "max_post_vs_absolute_q99_error_deg": check.get("max_post_vs_absolute_q99_error_deg"),
                "max_arm_span_ratio_postprocessor_over_sampled_relative": check.get(
                    "max_arm_span_ratio_postprocessor_over_sampled_relative"
                ),
                "worst_span_ratio_key": check.get("worst_span_ratio_key"),
            }
    return {
        "name": candidate.name,
        "source": candidate.source,
        "revision": candidate.revision,
        "path": str(candidate.path),
        "policy_type": cfg.type,
        "use_relative_actions": bool(getattr(cfg, "use_relative_actions", False)),
        "relative_exclude_joints": list(getattr(cfg, "relative_exclude_joints", [])),
        "train_dataset_repo": train_dataset_repo,
        "relative_stats_summary": relative_stats,
        "gate": gate,
        "deploy_candidate": bool(gate["summary"]["passed"]),
        "recipe_candidate_ignoring_training_dataset_match": not recipe_failures_without_dataset,
        "non_dataset_failed_checks": recipe_failures_without_dataset,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 29 Candidate Recipe Gate",
        "",
        "## Decision",
        "",
        "Only candidates with `deploy_candidate=true` may advance to Stage 31 dataset replay.",
        "A gate failure excludes the checkpoint from robot deployment.",
        "",
        "## Candidates",
        "",
    ]
    for result in payload["results"]:
        if "error" in result:
            lines.append(f"- `{result['name']}`: ERROR `{result['error']}`")
            continue
        status = "PASS" if result["gate"]["summary"]["passed"] else "FAIL"
        failed = ", ".join(result["gate"]["summary"]["failed_checks"]) or "none"
        rel = result.get("relative_stats_summary") or {}
        rel_bits = ""
        if rel:
            rel_bits = (
                f"; rel_q01_err={rel['max_post_vs_relative_q01_error_deg']:.3f}deg"
                f"; rel_q99_err={rel['max_post_vs_relative_q99_error_deg']:.3f}deg"
                f"; span_ratio={rel['max_arm_span_ratio_postprocessor_over_sampled_relative']:.3f}"
                f"; worst_span={rel['worst_span_ratio_key']}"
            )
        lines.append(
            f"- `{result['name']}`: {status}; deploy_candidate=`{str(result['deploy_candidate']).lower()}`; "
            f"train_dataset=`{result.get('train_dataset_repo')}`; failed_checks=`{failed}`{rel_bits}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- This script downloads/reads only lightweight model metadata and processor stats.",
            "- It does not load policy weights, videos, snapshots, robot connections, torque, or action sends.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate OpenArm folding checkpoint candidates without robot IO.")
    parser.add_argument("--dataset-repo")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--dataset-revision")
    parser.add_argument("--candidate", "--checkpoint", action="append", dest="candidates")
    parser.add_argument("--candidate-cache-dir", type=Path, default=Path("audits/openarm_folding/candidate_cache"))
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--relative-stats-tolerance-deg", type=float, default=2.0)
    parser.add_argument("--action-span-ratio-limit", type=float, default=3.0)
    parser.add_argument("--action-is-relative", choices=["auto", "true", "false"], default="auto")
    parser.add_argument("--json-out", "--output-json", type=Path, required=True)
    parser.add_argument("--md-out", "--output-md", type=Path, required=True)
    args = parser.parse_args()

    if (args.dataset_repo is None or args.dataset_root is None) and args.candidates and len(args.candidates) == 1:
        first_candidate = Path(args.candidates[0])
        if first_candidate.exists():
            train_cfg = replay.load_training_config(first_candidate)
            if args.dataset_repo is None:
                args.dataset_repo = train_cfg.get("dataset", {}).get("repo_id")
            if args.dataset_root is None and train_cfg.get("dataset", {}).get("root") is not None:
                args.dataset_root = Path(train_cfg["dataset"]["root"])
    if args.dataset_repo is None:
        args.dataset_repo = "lerobot-data-collection/level2_final_quality3_t_0_hil_data_c"
    if args.dataset_root is None:
        raise ValueError("--dataset-root is required unless a local checkpoint train_config provides dataset.root")
    dataset_root = replay.resolve_dataset_root(args.dataset_repo, args.dataset_root, args.dataset_revision)
    info = replay.read_info(dataset_root)
    action_is_relative, action_is_relative_source = replay.resolve_action_is_relative(
        args.action_is_relative,
        dataset_root,
        info,
    )
    args.candidate_cache_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "dataset_repo": args.dataset_repo,
        "dataset_root": str(dataset_root),
        "source_map": replay.FOLDING_RECIPE_SOURCE_MAP,
        "locked_recipe": replay.LOCKED_FOLDING_RECIPE,
        "action_is_relative": action_is_relative,
        "action_is_relative_source": action_is_relative_source,
        "candidates": args.candidates or DEFAULT_CANDIDATES,
        "results": [],
        "safety": {
            "model_weights_loaded": False,
            "videos_loaded": False,
            "robot_io": False,
            "send_action": False,
        },
    }
    for raw in payload["candidates"]:
        try:
            candidate = resolve_candidate(raw, args.candidate_cache_dir, args.local_only)
            payload["results"].append(
                gate_candidate(
                    candidate,
                    dataset_repo=args.dataset_repo,
                    dataset_root=dataset_root,
                    info=info,
                    max_rows=args.max_rows,
                    relative_stats_tolerance_deg=args.relative_stats_tolerance_deg,
                    action_span_ratio_limit=args.action_span_ratio_limit,
                    action_is_relative=action_is_relative,
                    action_is_relative_source=action_is_relative_source,
                )
            )
        except Exception as exc:
            payload["results"].append({"name": raw, "error": repr(exc), "deploy_candidate": False})

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    passing = [result["name"] for result in payload["results"] if result.get("deploy_candidate")]
    print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out), "passing": passing}, indent=2))
    return 0 if passing else 2


if __name__ == "__main__":
    raise SystemExit(main())
