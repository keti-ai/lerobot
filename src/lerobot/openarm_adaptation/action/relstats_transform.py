"""Transform an absolute-action LeRobotDataset into a relative-chunk-stats variant.

D-34 P2 — D-33 (handover dataset relstats 변환) 의 즉시 도구.

The output dataset keeps the original action/state/video frames byte-identical
but rewrites action stats to the relative-chunk distribution (sampler slices a
chunk of action rows and applies to_relative_actions before stats aggregation),
and drops a .relstats_complete marker so stage22/stage29 gates auto-detect the
relative path.
"""

from __future__ import annotations

import copy
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from lerobot.datasets.compute_stats import RunningQuantileStats, get_feature_stats
from lerobot.datasets.io_utils import write_stats
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.processor.relative_action_processor import to_relative_actions


_MAX_GET_FEATURE_STATS_ROWS = 1_000_000
_CHUNK_BATCH_SIZE = 10_000


@dataclass(frozen=True)
class RelstatsTransformResult:
    source_repo_id: str
    target_repo_id: str
    target_root: Path
    marker_path: Path
    source_action_stats: dict[str, Any]
    target_action_stats: dict[str, Any]
    verification: dict[str, Any]
    pushed_to_hub: bool


def _build_mask(action_dim: int, exclude_joint_indices: tuple[int, ...]) -> list[bool]:
    mask = [True] * action_dim
    for idx in exclude_joint_indices:
        if idx < 0 or idx >= action_dim:
            raise ValueError(f"exclude_joint_indices contains out-of-range index {idx} for action_dim={action_dim}")
        mask[idx] = False
    return mask


def _valid_chunk_starts(episode_indices: np.ndarray, chunk_size: int) -> np.ndarray:
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
    total = len(episode_indices)
    if total < chunk_size:
        return np.array([], dtype=np.int64)
    starts = np.arange(total - chunk_size + 1, dtype=np.int64)
    return starts[episode_indices[starts] == episode_indices[starts + chunk_size - 1]]


def _relative_chunk_batch(
    actions: np.ndarray,
    states: np.ndarray,
    start_indices: np.ndarray,
    chunk_size: int,
    mask: list[bool],
) -> np.ndarray:
    offsets = np.arange(chunk_size, dtype=np.int64)
    frame_indices = start_indices[:, None] + offsets[None, :]
    action_chunks = torch.as_tensor(actions[frame_indices], dtype=torch.float32)
    chunk_states = torch.as_tensor(states[start_indices], dtype=torch.float32)
    relative = to_relative_actions(action_chunks, chunk_states, mask)
    return relative.numpy().reshape(-1, actions.shape[-1])


def _compute_relative_chunk_action_stats(
    dataset: LeRobotDataset,
    *,
    action_key: str,
    state_key: str,
    chunk_size: int,
    mask: list[bool],
) -> tuple[dict[str, np.ndarray], dict[str, int | str]]:
    hf_dataset = dataset.hf_dataset
    actions = np.asarray(hf_dataset[action_key], dtype=np.float32)
    states = np.asarray(hf_dataset[state_key], dtype=np.float32)
    episode_indices = np.asarray(hf_dataset["episode_index"])

    if actions.ndim != 2:
        raise ValueError(f"{action_key!r} must be a 2D array, got shape={actions.shape}")
    if states.ndim != 2:
        raise ValueError(f"{state_key!r} must be a 2D array, got shape={states.shape}")
    if states.shape[1] < actions.shape[1]:
        raise ValueError(
            f"{state_key!r} dim must be >= {action_key!r} dim, got state_dim={states.shape[1]} "
            f"and action_dim={actions.shape[1]}"
        )

    valid_starts = _valid_chunk_starts(episode_indices, chunk_size)
    if len(valid_starts) == 0:
        raise RuntimeError(
            f"No valid single-episode chunks found for chunk_size={chunk_size}, total_frames={len(episode_indices)}"
        )

    relative_rows = int(len(valid_starts) * chunk_size)
    batches = [
        valid_starts[i : i + _CHUNK_BATCH_SIZE] for i in range(0, len(valid_starts), _CHUNK_BATCH_SIZE)
    ]

    if relative_rows <= _MAX_GET_FEATURE_STATS_ROWS:
        relative_chunks = [
            _relative_chunk_batch(actions, states, batch, chunk_size, mask) for batch in batches
        ]
        all_relative = np.concatenate(relative_chunks, axis=0)
        stats = get_feature_stats(all_relative, axis=0, keepdims=all_relative.ndim == 1)
        method = "get_feature_stats"
    else:
        running_stats = RunningQuantileStats()
        for batch in batches:
            running_stats.update(_relative_chunk_batch(actions, states, batch, chunk_size, mask))
        stats = running_stats.get_statistics()
        method = "RunningQuantileStats"

    return stats, {
        "valid_chunks": int(len(valid_starts)),
        "relative_rows": relative_rows,
        "stats_method": method,
    }


def _copy_dataset_tree(source_root: Path, target_root: Path) -> None:
    source_resolved = source_root.resolve()
    target_resolved = target_root.resolve(strict=False)
    if target_resolved == source_resolved or source_resolved in target_resolved.parents:
        raise ValueError(f"target_root must not be source_root or inside source_root: {target_root}")
    if target_root.exists() and any(target_root.iterdir()):
        raise FileExistsError(f"target_root already exists and is not empty: {target_root}")
    target_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_root, target_root, copy_function=shutil.copy2, dirs_exist_ok=target_root.exists())


def _verify_relative_like(
    stats: dict[str, Any],
    *,
    mask: list[bool],
    verify_mean_abs_max: float,
    verify_q_range_max: float,
) -> dict[str, Any]:
    converted = np.asarray(mask, dtype=bool)
    if not converted.any():
        raise ValueError("At least one action dimension must remain relative after exclusions")

    mean = np.asarray(stats["mean"], dtype=np.float32)
    q01 = np.asarray(stats["q01"], dtype=np.float32)
    q99 = np.asarray(stats["q99"], dtype=np.float32)

    mean_abs_max = float(np.max(np.abs(mean[converted])))
    quantile_abs_max = float(max(np.max(np.abs(q01[converted])), np.max(np.abs(q99[converted]))))
    is_relative_like = mean_abs_max < verify_mean_abs_max and quantile_abs_max < verify_q_range_max

    return {
        "is_relative_like": bool(is_relative_like),
        "mean_abs_max": mean_abs_max,
        "quantile_abs_max": quantile_abs_max,
        "verify_mean_abs_max": float(verify_mean_abs_max),
        "verify_q_range_max": float(verify_q_range_max),
        "converted_indices": np.flatnonzero(converted).astype(int).tolist(),
        "excluded_indices": np.flatnonzero(~converted).astype(int).tolist(),
    }


def transform_dataset_to_relative_chunk(
    source_repo_id: str,
    target_repo_id: str,
    target_root: Path,
    source_root: Path | None = None,
    chunk_size: int = 30,
    exclude_joint_indices: tuple[int, ...] = (7, 15),
    state_key: str = "observation.state",
    action_key: str = "action",
    push_to_hub: bool = False,
    private: bool = True,
    verify: bool = True,
    verify_mean_abs_max: float = 5.0,
    verify_q_range_max: float = 70.0,
) -> RelstatsTransformResult:
    """Build a relative-chunk-stats variant of ``source_repo_id``.

    The target dataset keeps source frames unchanged, rewrites ``meta/stats.json``
    action stats to the chunk-aware relative distribution, and writes a
    ``.relstats_complete`` marker for stage22/stage29 auto-detection.
    """
    target_root = Path(target_root)
    source_dataset = LeRobotDataset(source_repo_id, root=source_root)

    features = source_dataset.meta.features
    if action_key not in features:
        raise KeyError(f"{action_key!r} not found in source dataset features")
    if state_key not in features:
        raise KeyError(f"{state_key!r} not found in source dataset features")

    action_dim = int(features[action_key]["shape"][0])
    mask = _build_mask(action_dim, exclude_joint_indices)
    relative_action_stats, chunk_info = _compute_relative_chunk_action_stats(
        source_dataset,
        action_key=action_key,
        state_key=state_key,
        chunk_size=chunk_size,
        mask=mask,
    )

    verification = _verify_relative_like(
        relative_action_stats,
        mask=mask,
        verify_mean_abs_max=verify_mean_abs_max,
        verify_q_range_max=verify_q_range_max,
    )
    verification.update(
        {
            "chunk_size": int(chunk_size),
            "action_dim": action_dim,
            **chunk_info,
        }
    )
    if verify and not verification["is_relative_like"]:
        raise ValueError(f"Relative chunk stats did not pass relative-like verification: {verification}")

    source_action_stats = {}
    if source_dataset.meta.stats and action_key in source_dataset.meta.stats:
        source_action_stats = copy.deepcopy(source_dataset.meta.stats[action_key])
    target_stats = copy.deepcopy(source_dataset.meta.stats) if source_dataset.meta.stats else {}
    target_stats[action_key] = relative_action_stats

    _copy_dataset_tree(source_dataset.root, target_root)
    write_stats(target_stats, target_root)

    marker_path = target_root / ".relstats_complete"
    marker_path.write_text(
        "\n".join(
            [
                f"source_repo_id={source_repo_id}",
                f"target_repo_id={target_repo_id}",
                f"chunk_size={chunk_size}",
                f"exclude_joint_indices={','.join(str(idx) for idx in exclude_joint_indices)}",
                f"relative_rows={chunk_info['relative_rows']}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    pushed_to_hub = False
    if push_to_hub:
        target_dataset = LeRobotDataset(target_repo_id, root=target_root)
        target_dataset.push_to_hub(private=private)
        pushed_to_hub = True

    return RelstatsTransformResult(
        source_repo_id=source_repo_id,
        target_repo_id=target_repo_id,
        target_root=target_root,
        marker_path=marker_path,
        source_action_stats=source_action_stats,
        target_action_stats=relative_action_stats,
        verification=verification,
        pushed_to_hub=pushed_to_hub,
    )
