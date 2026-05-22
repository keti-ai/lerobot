"""Smoke + correctness test for transform_dataset_to_relative_chunk."""

from pathlib import Path

import numpy as np
import pytest

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.openarm_adaptation.action import transform_dataset_to_relative_chunk


def _build_tiny_absolute_dataset(tmp_path: Path) -> tuple[str, Path]:
    """Create a tmp 16D absolute-action dataset with two short episodes."""
    repo_id = "local-test/source"
    root = tmp_path / "source"
    names = [
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
    features = {
        "action": {"dtype": "float32", "shape": (16,), "names": names},
        "observation.state": {"dtype": "float32", "shape": (16,), "names": names},
    }
    dataset = LeRobotDataset.create(repo_id=repo_id, fps=30, features=features, root=root, use_videos=False)

    dim_offsets = np.arange(16, dtype=np.float32) * 0.1
    for ep_idx in range(2):
        base_state = np.full(16, 100.0 + ep_idx * 10.0, dtype=np.float32) + dim_offsets
        base_state[7] = 0.0
        base_state[15] = 0.0
        for frame_idx in range(40):
            delta = np.sin((frame_idx + np.arange(16, dtype=np.float32)) * 0.2).astype(np.float32) * 2.0
            action = base_state + delta
            action[7] = 3.0
            action[15] = -4.0
            dataset.add_frame(
                {
                    "action": action.astype(np.float32),
                    "observation.state": base_state.copy(),
                    "task": f"episode_{ep_idx}",
                }
            )
        dataset.save_episode()
    dataset.finalize()
    return repo_id, root


def test_transform_dataset_to_relative_chunk(tmp_path: Path) -> None:
    source_repo, source_root = _build_tiny_absolute_dataset(tmp_path)
    target_root = tmp_path / "target"

    result = transform_dataset_to_relative_chunk(
        source_repo_id=source_repo,
        source_root=source_root,
        target_repo_id="local-test/target",
        target_root=target_root,
        chunk_size=10,
        exclude_joint_indices=(7, 15),
        push_to_hub=False,
        verify=True,
    )

    assert result.marker_path == target_root / ".relstats_complete"
    assert result.marker_path.exists()
    assert result.verification["is_relative_like"] is True
    assert result.verification["valid_chunks"] == 62
    assert result.verification["relative_rows"] == 620

    target_stats = result.target_action_stats
    converted_indices = result.verification["converted_indices"]
    excluded_indices = result.verification["excluded_indices"]
    assert np.abs(target_stats["mean"][converted_indices]).max() < 5.0
    quantile_abs_max = max(
        np.abs(target_stats["q01"][converted_indices]).max(),
        np.abs(target_stats["q99"][converted_indices]).max(),
    )
    assert quantile_abs_max < 60.0
    np.testing.assert_allclose(target_stats["mean"][excluded_indices], np.array([3.0, -4.0]), atol=1e-6)

    source_dataset = LeRobotDataset(source_repo, root=source_root)
    target_dataset = LeRobotDataset("local-test/target", root=target_root)
    np.testing.assert_allclose(
        np.asarray(source_dataset.hf_dataset["action"], dtype=np.float32),
        np.asarray(target_dataset.hf_dataset["action"], dtype=np.float32),
    )


def test_verify_fails_when_threshold_is_too_strict(tmp_path: Path) -> None:
    source_repo, source_root = _build_tiny_absolute_dataset(tmp_path)

    with pytest.raises(ValueError, match="relative-like verification"):
        transform_dataset_to_relative_chunk(
            source_repo_id=source_repo,
            source_root=source_root,
            target_repo_id="local-test/target-fail",
            target_root=tmp_path / "target-fail",
            chunk_size=10,
            exclude_joint_indices=(7, 15),
            push_to_hub=False,
            verify=True,
            verify_q_range_max=0.5,
        )
