from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import torch
from huggingface_hub import snapshot_download
from PIL import Image
from safetensors.torch import load_file

from lerobot.configs import PreTrainedConfig
from lerobot.policies import get_policy_class, make_pre_post_processors
from lerobot.policies.utils import prepare_observation_for_inference
from lerobot.processor.relative_action_processor import RelativeActionsProcessorStep


ACTION_NAMES = [
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

IMAGE_KEYS = [
    "observation.images.left_wrist",
    "observation.images.right_wrist",
    "observation.images.base",
]

ARM_ACTION_MASK = np.asarray(["gripper" not in name for name in ACTION_NAMES], dtype=bool)
EXPECTED_IMAGE_SHAPES = {
    "observation.images.left_wrist": [720, 1280, 3],
    "observation.images.right_wrist": [720, 1280, 3],
    "observation.images.base": [480, 640, 3],
}
FOLDING_RECIPE_SOURCE_MAP = {
    "robot_folding_space": "https://huggingface.co/spaces/lerobot/robot-folding#hardware",
    "pi05_docs": "docs/source/policy_pi05_README.md",
    "relative_actions_docs": "docs/source/action_representations.mdx",
    "pi05_processor_contract": "src/lerobot/policies/pi05/processor_pi05.py",
    "relative_action_processor": "src/lerobot/processor/relative_action_processor.py",
    "rtc_inference": "src/lerobot/rollout/inference/rtc.py",
    "action_interpolation": "src/lerobot/utils/action_interpolator.py",
    "sarm_rabc": "src/lerobot/rewards/sarm/rabc.py",
    "openarm_docs": "docs/source/openarm.mdx",
}
LOCKED_FOLDING_RECIPE = {
    "robot": "bimanual OpenArm / openarms_follower",
    "hardware": "+5 cm upper arm extension and larger gripper jaws expected for final deployment",
    "state_action_order": ACTION_NAMES,
    "camera_keys": IMAGE_KEYS,
    "camera_shapes": EXPECTED_IMAGE_SHAPES,
    "model": "pi05",
    "chunk_size": 30,
    "n_action_steps": 30,
    "action_representation": "relative trajectory",
    "relative_exclude_joints": ["gripper"],
    "training_techniques": ["SARM", "RABC"],
    "rtc_execution_horizon": 20,
    "action_interpolation_multiplier": 3,
}


@dataclass(frozen=True)
class DatasetSample:
    episode_index: int
    frame_index: int
    timestamp: float
    task: str
    state: np.ndarray
    action: np.ndarray
    images: dict[str, np.ndarray]


def resolve_dataset_root(repo_id: str, root: Path, revision: str | None) -> Path:
    if (root / "meta").exists() and (root / "data").exists():
        return root
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        local_dir=root,
        allow_patterns=["meta/**", "data/**", "README.md"],
        ignore_patterns=["videos/**"],
    )
    return root


def read_info(dataset_root: Path) -> dict[str, Any]:
    return json.loads((dataset_root / "meta" / "info.json").read_text())


def parquet_rows(path: Path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


def load_episode_row(dataset_root: Path, episode_index: int) -> dict[str, Any]:
    for path in sorted((dataset_root / "meta" / "episodes").glob("**/*.parquet")):
        for row in parquet_rows(path):
            if int(row["episode_index"]) == episode_index:
                return row
    raise ValueError(f"Episode {episode_index} not found under {dataset_root / 'meta' / 'episodes'}")


def data_file_path(dataset_root: Path, info: dict[str, Any], episode_row: dict[str, Any]) -> Path:
    rel = info["data_path"].format(
        chunk_index=int(episode_row["data/chunk_index"]),
        file_index=int(episode_row["data/file_index"]),
    )
    return dataset_root / rel


def video_file_path(dataset_root: Path, info: dict[str, Any], episode_row: dict[str, Any], image_key: str) -> Path:
    rel = info["video_path"].format(
        video_key=image_key,
        chunk_index=int(episode_row[f"videos/{image_key}/chunk_index"]),
        file_index=int(episode_row[f"videos/{image_key}/file_index"]),
    )
    return dataset_root / rel


def ensure_episode_videos(
    repo_id: str,
    dataset_root: Path,
    revision: str | None,
    info: dict[str, Any],
    episode_row: dict[str, Any],
) -> list[Path]:
    paths = [video_file_path(dataset_root, info, episode_row, key) for key in IMAGE_KEYS]
    missing = [path for path in paths if not path.exists()]
    if missing:
        allow_patterns = [str(path.relative_to(dataset_root)) for path in paths]
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            local_dir=dataset_root,
            allow_patterns=allow_patterns,
        )
    missing = [path for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing video files after download: {[str(p) for p in missing]}")
    return paths


def select_episode_rows(dataset_root: Path, info: dict[str, Any], episode_row: dict[str, Any]) -> list[dict[str, Any]]:
    rows = parquet_rows(data_file_path(dataset_root, info, episode_row))
    episode_index = int(episode_row["episode_index"])
    return [row for row in rows if int(row["episode_index"]) == episode_index]


def load_training_config(model_dir: Path) -> dict[str, Any]:
    path = model_dir / "train_config.json"
    return json.loads(path.read_text()) if path.exists() else {}


def load_checkpoint_action_quantiles(model_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    path = model_dir / "policy_postprocessor_step_0_unnormalizer_processor.safetensors"
    tensors = load_file(str(path))
    return tensors["action.q01"].cpu().numpy(), tensors["action.q99"].cpu().numpy()


def sample_relative_action_stats(
    dataset_root: Path,
    max_rows: int,
) -> dict[str, Any]:
    states: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    for path in sorted((dataset_root / "data").glob("**/*.parquet")):
        import pyarrow.parquet as pq

        table = pq.read_table(path, columns=["observation.state", "action"])
        for row in table.to_pylist():
            states.append(vector(row["observation.state"]))
            actions.append(vector(row["action"]))
            if len(states) >= max_rows:
                break
        if len(states) >= max_rows:
            break
    if not states:
        raise ValueError(f"No rows loaded from {dataset_root / 'data'}")
    state_arr = np.stack(states)
    action_arr = np.stack(actions)
    rel = action_arr - state_arr
    return {
        "rows": int(rel.shape[0]),
        "relative_q01": np.percentile(rel, 1, axis=0),
        "relative_q99": np.percentile(rel, 99, axis=0),
        "absolute_q01": np.percentile(action_arr, 1, axis=0),
        "absolute_q99": np.percentile(action_arr, 99, axis=0),
    }


def abs_max(values: np.ndarray, mask: np.ndarray) -> float:
    return float(np.max(np.abs(values[mask])))


def validate_folding_recipe(
    *,
    cfg: PreTrainedConfig,
    model_dir: Path,
    dataset_repo: str,
    dataset_root: Path,
    info: dict[str, Any],
    max_rows: int,
    relative_stats_tolerance_deg: float,
    action_span_ratio_limit: float,
) -> dict[str, Any]:
    train_cfg = load_training_config(model_dir)
    train_dataset_repo = train_cfg.get("dataset", {}).get("repo_id")
    train_policy = train_cfg.get("policy", {})
    q01, q99 = load_checkpoint_action_quantiles(model_dir)
    sampled = sample_relative_action_stats(dataset_root, max_rows=max_rows)
    rel_q01 = sampled["relative_q01"]
    rel_q99 = sampled["relative_q99"]
    abs_q01 = sampled["absolute_q01"]
    abs_q99 = sampled["absolute_q99"]
    post_span = q99 - q01
    rel_span = rel_q99 - rel_q01
    span_ratio = post_span / np.maximum(rel_span, 1e-6)

    checks = []

    def add_check(name: str, passed: bool, details: dict[str, Any]) -> None:
        checks.append({"name": name, "passed": bool(passed), **details})

    features = info.get("features", {})
    image_features = {key: features.get(key, {}) for key in IMAGE_KEYS}
    add_check("policy_type_pi05", getattr(cfg, "type", None) == "pi05", {"actual": getattr(cfg, "type", None)})
    add_check(
        "model_training_dataset_matches_replay_dataset",
        train_dataset_repo in {None, dataset_repo},
        {"train_dataset_repo": train_dataset_repo, "replay_dataset_repo": dataset_repo},
    )
    add_check(
        "dataset_robot_type_openarms_follower",
        info.get("robot_type") == "openarms_follower",
        {"actual": info.get("robot_type")},
    )
    add_check(
        "action_names_match_folding_16d",
        features.get("action", {}).get("names") == ACTION_NAMES,
        {"actual": features.get("action", {}).get("names")},
    )
    add_check(
        "state_names_match_folding_16d",
        features.get("observation.state", {}).get("names") == ACTION_NAMES,
        {"actual": features.get("observation.state", {}).get("names")},
    )
    add_check(
        "camera_keys_and_shapes_match_space_recipe",
        all(image_features[key].get("shape") == EXPECTED_IMAGE_SHAPES[key] for key in IMAGE_KEYS),
        {"actual": {key: image_features[key].get("shape") for key in IMAGE_KEYS}},
    )
    add_check(
        "use_relative_actions_enabled",
        bool(getattr(cfg, "use_relative_actions", False)),
        {"actual": bool(getattr(cfg, "use_relative_actions", False))},
    )
    add_check(
        "relative_exclude_gripper_only",
        list(getattr(cfg, "relative_exclude_joints", [])) == ["gripper"],
        {"actual": list(getattr(cfg, "relative_exclude_joints", []))},
    )
    add_check("chunk_size_30", int(getattr(cfg, "chunk_size", -1)) == 30, {"actual": getattr(cfg, "chunk_size", None)})
    add_check(
        "n_action_steps_30",
        int(getattr(cfg, "n_action_steps", -1)) == 30,
        {"actual": getattr(cfg, "n_action_steps", None)},
    )
    add_check(
        "rabc_recorded_in_train_config",
        bool(train_cfg.get("use_rabc", False)),
        {
            "use_rabc": train_cfg.get("use_rabc"),
            "rabc_kappa": train_cfg.get("rabc_kappa"),
            "rabc_progress_path": train_cfg.get("rabc_progress_path"),
        },
    )

    max_post_vs_rel_q01_error = abs_max(q01 - rel_q01, ARM_ACTION_MASK)
    max_post_vs_rel_q99_error = abs_max(q99 - rel_q99, ARM_ACTION_MASK)
    max_post_vs_abs_q01_error = abs_max(q01 - abs_q01, ARM_ACTION_MASK)
    max_post_vs_abs_q99_error = abs_max(q99 - abs_q99, ARM_ACTION_MASK)
    max_arm_span_ratio = float(np.max(span_ratio[ARM_ACTION_MASK]))
    add_check(
        "postprocessor_action_stats_are_relative_for_arm_joints",
        max_post_vs_rel_q01_error <= relative_stats_tolerance_deg
        and max_post_vs_rel_q99_error <= relative_stats_tolerance_deg
        and max_arm_span_ratio <= action_span_ratio_limit,
        {
            "sample_rows": sampled["rows"],
            "relative_stats_tolerance_deg": relative_stats_tolerance_deg,
            "action_span_ratio_limit": action_span_ratio_limit,
            "max_post_vs_relative_q01_error_deg": max_post_vs_rel_q01_error,
            "max_post_vs_relative_q99_error_deg": max_post_vs_rel_q99_error,
            "max_post_vs_absolute_q01_error_deg": max_post_vs_abs_q01_error,
            "max_post_vs_absolute_q99_error_deg": max_post_vs_abs_q99_error,
            "max_arm_span_ratio_postprocessor_over_sampled_relative": max_arm_span_ratio,
            "worst_span_ratio_key": ACTION_NAMES[int(np.argmax(np.where(ARM_ACTION_MASK, span_ratio, -1.0)))],
        },
    )

    return {
        "source": FOLDING_RECIPE_SOURCE_MAP["robot_folding_space"],
        "source_map": FOLDING_RECIPE_SOURCE_MAP,
        "locked_recipe": LOCKED_FOLDING_RECIPE,
        "summary": {
            "passed": all(check["passed"] for check in checks),
            "failed_checks": [check["name"] for check in checks if not check["passed"]],
        },
        "expected_runtime": {
            "robot": "bimanual OpenArm",
            "action_dim": 16,
            "camera_keys": IMAGE_KEYS,
            "model": "pi05",
            "chunk_size": 30,
            "rtc_execution_horizon": 20,
            "action_interpolation_multiplier": 3,
            "action_representation": "relative trajectory; grippers excluded",
            "training_techniques": ["SARM", "RABC", "DAgger/HIL", "high-quality data fine-tuning"],
        },
        "checks": checks,
    }


def parse_frame_indices(raw: str, episode_length: int) -> list[int]:
    if raw == "auto":
        candidates = [0, 1, 2, 10, 30, 60, 120, 300]
        return [idx for idx in candidates if idx < episode_length]
    result = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        idx = int(item)
        if idx < 0 or idx >= episode_length:
            raise ValueError(f"Frame index {idx} outside episode length {episode_length}")
        result.append(idx)
    if not result:
        raise ValueError("No frame indices selected")
    return result


def tensor_frame_to_hwc_uint8(frame: torch.Tensor) -> np.ndarray:
    arr = frame.detach().cpu()
    if arr.ndim != 3:
        raise ValueError(f"Expected single frame tensor, got shape {tuple(arr.shape)}")
    if arr.shape[0] in {1, 3}:
        arr = arr.permute(1, 2, 0)
    out = arr.numpy()
    if out.dtype != np.uint8:
        out = np.clip(out * 255.0, 0, 255).astype(np.uint8)
    return out


def decode_video_frame_with_cv2(video_path: Path, timestamp: float, fps: float) -> np.ndarray:
    import cv2

    frame_index = max(0, int(round(timestamp * fps)))
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video with cv2: {video_path}")
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
            ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"Failed to decode frame {frame_index} at {timestamp:.3f}s from {video_path}")
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    finally:
        cap.release()


def decode_video_frame_with_ffmpeg(video_path: Path, timestamp: float) -> np.ndarray:
    output = subprocess.check_output(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp:.6f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ]
    )
    if not output:
        raise RuntimeError(f"ffmpeg returned no frame for {video_path} at {timestamp:.3f}s")
    return np.asarray(Image.open(BytesIO(output)).convert("RGB"))


def decode_dataset_images(
    dataset_root: Path,
    info: dict[str, Any],
    episode_row: dict[str, Any],
    timestamp: float,
    backend: str,
) -> dict[str, np.ndarray]:
    images = {}
    fps = float(info["fps"])
    for key in IMAGE_KEYS:
        video_path = video_file_path(dataset_root, info, episode_row, key)
        video_timestamp = float(episode_row[f"videos/{key}/from_timestamp"]) + timestamp
        if backend == "cv2":
            try:
                images[key] = decode_video_frame_with_cv2(video_path, video_timestamp, fps)
            except Exception:
                images[key] = decode_video_frame_with_ffmpeg(video_path, video_timestamp)
        elif backend == "ffmpeg":
            images[key] = decode_video_frame_with_ffmpeg(video_path, video_timestamp)
        else:
            raise ValueError("This audit script supports --video-backend cv2 or ffmpeg")
    return images


def vector(value: Any) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float32).reshape(-1)
    if arr.shape != (len(ACTION_NAMES),):
        raise ValueError(f"Expected {len(ACTION_NAMES)} values, got {arr.shape}")
    return arr


def load_dataset_samples(
    dataset_root: Path,
    info: dict[str, Any],
    episode_row: dict[str, Any],
    frame_indices: list[int],
    video_backend: str,
) -> list[DatasetSample]:
    rows_by_frame = {int(row["frame_index"]): row for row in select_episode_rows(dataset_root, info, episode_row)}
    task = episode_row["tasks"][0] if episode_row.get("tasks") else "Fold the T-shirt properly"
    samples = []
    for frame_index in frame_indices:
        row = rows_by_frame[frame_index]
        timestamp = float(row["timestamp"])
        samples.append(
            DatasetSample(
                episode_index=int(row["episode_index"]),
                frame_index=frame_index,
                timestamp=timestamp,
                task=task,
                state=vector(row["observation.state"]),
                action=vector(row["action"]),
                images=decode_dataset_images(dataset_root, info, episode_row, timestamp, video_backend),
            )
        )
    return samples


def read_state_csv(path: Path) -> np.ndarray:
    with path.open(newline="") as f:
        rows = [row for row in csv.reader(f) if row]
    values = rows[1] if rows and rows[0] == ACTION_NAMES else rows[0]
    return vector(values)


def read_snapshot_images(snapshot_dir: Path) -> dict[str, np.ndarray]:
    return {
        "observation.images.left_wrist": np.asarray(Image.open(snapshot_dir / "left_wrist.png").convert("RGB")),
        "observation.images.right_wrist": np.asarray(Image.open(snapshot_dir / "right_wrist.png").convert("RGB")),
        "observation.images.base": np.asarray(Image.open(snapshot_dir / "base.png").convert("RGB")),
    }


def find_relative_step(preprocessor) -> RelativeActionsProcessorStep:
    for step in preprocessor.steps:
        if isinstance(step, RelativeActionsProcessorStep):
            return step
    raise RuntimeError("No RelativeActionsProcessorStep in preprocessor")


def load_model(model_dir: Path, device: str):
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


def run_policy_case(
    policy,
    preprocessor,
    postprocessor,
    state: np.ndarray,
    images: dict[str, np.ndarray],
    task: str,
    robot_type: str,
    device: str,
) -> dict[str, Any]:
    observation = {"observation.state": state, **images}
    prepared = prepare_observation_for_inference(
        observation,
        device=torch.device(device),
        task=task,
        robot_type=robot_type,
    )
    with torch.inference_mode():
        preprocessed = preprocessor(prepared)
        model_action = policy.predict_action_chunk(preprocessed)
        postprocessed = postprocessor(model_action)
    absolute = postprocessed[0, 0].detach().cpu().numpy().astype(np.float32)
    relative_step = find_relative_step(preprocessor)
    cached_state = relative_step.get_cached_state()
    cached_state_np = cached_state[0].detach().cpu().numpy().astype(np.float32)
    deltas = absolute - cached_state_np[: len(ACTION_NAMES)]
    abs_deltas = np.abs(deltas)
    idx = int(np.argmax(abs_deltas))
    return {
        "action_shape": list(postprocessed.shape),
        "max_abs_delta_deg": float(abs_deltas[idx]),
        "max_abs_delta_key": ACTION_NAMES[idx],
        "mean_abs_delta_deg": float(np.mean(abs_deltas)),
        "rows": [
            {
                "key": key,
                "state_deg": float(cached_state_np[i]),
                "predicted_abs_deg": float(absolute[i]),
                "predicted_delta_deg": float(deltas[i]),
            }
            for i, key in enumerate(ACTION_NAMES)
        ],
    }


def compare_to_recorded(case: dict[str, Any], recorded_action: np.ndarray, state: np.ndarray) -> dict[str, Any]:
    recorded_delta = recorded_action - state
    model_delta = np.asarray([row["predicted_delta_deg"] for row in case["rows"]], dtype=np.float32)
    error = model_delta - recorded_delta
    abs_error = np.abs(error)
    idx = int(np.argmax(abs_error))
    return {
        "recorded_mean_abs_delta_deg": float(np.mean(np.abs(recorded_delta))),
        "recorded_max_abs_delta_deg": float(np.max(np.abs(recorded_delta))),
        "model_minus_recorded_mean_abs_error_deg": float(np.mean(abs_error)),
        "model_minus_recorded_max_abs_error_deg": float(abs_error[idx]),
        "model_minus_recorded_max_abs_error_key": ACTION_NAMES[idx],
        "rows": [
            {
                "key": key,
                "recorded_action_deg": float(recorded_action[i]),
                "recorded_delta_deg": float(recorded_delta[i]),
                "model_delta_deg": float(model_delta[i]),
                "model_minus_recorded_delta_deg": float(error[i]),
            }
            for i, key in enumerate(ACTION_NAMES)
        ],
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 22 Dataset Replay And Stage 23 Ablation",
        "",
        "## Recipe Gate",
        "",
    ]
    recipe_gate = payload.get("recipe_gate")
    if recipe_gate:
        status = "PASS" if recipe_gate["summary"]["passed"] else "FAIL"
        lines.append(f"- Status: `{status}`")
        lines.append(f"- Source: {recipe_gate['source']}")
        if recipe_gate["summary"]["failed_checks"]:
            lines.append(f"- Failed checks: `{', '.join(recipe_gate['summary']['failed_checks'])}`")
        for check in recipe_gate["checks"]:
            mark = "PASS" if check["passed"] else "FAIL"
            lines.append(f"- `{check['name']}`: {mark}")
    else:
        lines.append("- Not requested.")
    if payload.get("recipe_gate_only"):
        lines.extend(
            [
                "",
                "## Decision Inputs",
                "",
                f"- Dataset: `{payload['dataset_repo']}`",
                f"- Model: `{payload['model_dir']}`",
                f"- Mode: `recipe_gate_only`",
                "",
                "## Safety",
                "",
                "- No model weights, videos, robot connection, motor initialization, torque enable, "
                "zeroing, or action send is performed by this mode.",
                "- This is an offline recipe/artifact contract gate only.",
            ]
        )
        path.write_text("\n".join(lines) + "\n")
        return
    lines.extend([
        "",
        "## Decision Inputs",
        "",
        f"- Dataset: `{payload['dataset_repo']}` episode `{payload['episode_index']}`",
        f"- Model: `{payload['model_dir']}`",
        f"- Video backend: `{payload['video_backend']}`",
        f"- Robot type: `{payload['robot_type']}`",
        f"- Snapshot: `{payload.get('snapshot_dir') or 'not provided'}`",
        "",
        "## Dataset Replay",
        "",
    ])
    for sample in payload["dataset_replay"]:
        summary = sample["model_summary"]
        cmp_summary = sample["recorded_comparison"]
        lines.append(
            f"- frame `{sample['frame_index']}`: model mean_abs_delta="
            f"{summary['mean_abs_delta_deg']:.3f}, max_abs_delta="
            f"{summary['max_abs_delta_deg']:.3f} at `{summary['max_abs_delta_key']}`; "
            f"recorded mean_abs_delta={cmp_summary['recorded_mean_abs_delta_deg']:.3f}, "
            f"model-vs-recorded max_error={cmp_summary['model_minus_recorded_max_abs_error_deg']:.3f} "
            f"at `{cmp_summary['model_minus_recorded_max_abs_error_key']}`"
        )
    if payload.get("ablations"):
        lines.extend(["", "## State / Visual Ablation", ""])
        for name, case in payload["ablations"].items():
            summary = case["model_summary"]
            lines.append(
                f"- `{name}`: mean_abs_delta={summary['mean_abs_delta_deg']:.3f}, "
                f"max_abs_delta={summary['max_abs_delta_deg']:.3f} at `{summary['max_abs_delta_key']}`"
            )
    lines.extend(["", "## Safety", ""])
    lines.append("- No robot connection, motor initialization, torque enable, zeroing, or action send is performed by this script.")
    lines.append("- This is an offline A6000 policy/input contract probe only.")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline dataset replay and state/visual ablation for OpenArm folding.")
    parser.add_argument("--dataset-repo", default="lerobot/full_folding")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--dataset-revision")
    parser.add_argument("--episode-index", type=int, default=0)
    parser.add_argument("--frames", default="auto")
    parser.add_argument("--video-backend", default="cv2")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--snapshot-dir", type=Path)
    parser.add_argument("--ablation-frame", type=int, default=0)
    parser.add_argument("--robot-type", default="openarms_follower")
    parser.add_argument("--no-recipe-gate", action="store_true")
    parser.add_argument(
        "--recipe-gate-only",
        action="store_true",
        help="Run only the offline recipe gate. Does not load model weights, videos, snapshots, or robot IO.",
    )
    parser.add_argument("--recipe-gate-max-rows", type=int, default=5000)
    parser.add_argument("--recipe-gate-relative-stats-tolerance-deg", type=float, default=2.0)
    parser.add_argument("--recipe-gate-action-span-ratio-limit", type=float, default=3.0)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    dataset_root = resolve_dataset_root(args.dataset_repo, args.dataset_root, args.dataset_revision)
    info = read_info(dataset_root)
    cfg = PreTrainedConfig.from_pretrained(args.model_dir)
    recipe_gate = None
    if not args.no_recipe_gate:
        recipe_gate = validate_folding_recipe(
            cfg=cfg,
            model_dir=args.model_dir,
            dataset_repo=args.dataset_repo,
            dataset_root=dataset_root,
            info=info,
            max_rows=args.recipe_gate_max_rows,
            relative_stats_tolerance_deg=args.recipe_gate_relative_stats_tolerance_deg,
            action_span_ratio_limit=args.recipe_gate_action_span_ratio_limit,
        )
    if args.recipe_gate_only:
        payload = {
            "dataset_repo": args.dataset_repo,
            "dataset_root": str(dataset_root),
            "model_dir": str(args.model_dir),
            "policy_type": cfg.type,
            "use_relative_actions": bool(getattr(cfg, "use_relative_actions", False)),
            "relative_exclude_joints": list(getattr(cfg, "relative_exclude_joints", [])),
            "recipe_gate": recipe_gate,
            "recipe_gate_only": True,
            "safety": {
                "model_weights_loaded": False,
                "videos_loaded": False,
                "robot_io": False,
                "motor_initialization": False,
                "torque_enable": False,
                "zeroing": False,
                "send_action": False,
            },
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        write_markdown(args.md_out, payload)
        if recipe_gate is not None and not recipe_gate["summary"]["passed"]:
            print(
                json.dumps(
                    {"json_out": str(args.json_out), "md_out": str(args.md_out), "recipe_gate": "FAIL"},
                    indent=2,
                )
            )
            return 2
        print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out)}, indent=2))
        return 0

    episode_row = load_episode_row(dataset_root, args.episode_index)
    ensure_episode_videos(args.dataset_repo, dataset_root, args.dataset_revision, info, episode_row)
    frame_indices = parse_frame_indices(args.frames, int(episode_row["length"]))
    samples = load_dataset_samples(dataset_root, info, episode_row, frame_indices, args.video_backend)

    cfg, policy, preprocessor, postprocessor = load_model(args.model_dir, args.device)
    payload: dict[str, Any] = {
        "dataset_repo": args.dataset_repo,
        "dataset_root": str(dataset_root),
        "episode_index": args.episode_index,
        "model_dir": str(args.model_dir),
        "policy_type": cfg.type,
        "use_relative_actions": bool(getattr(cfg, "use_relative_actions", False)),
        "relative_exclude_joints": list(getattr(cfg, "relative_exclude_joints", [])),
        "video_backend": args.video_backend,
        "robot_type": args.robot_type,
        "action_names": ACTION_NAMES,
        "recipe_gate": recipe_gate,
        "dataset_replay": [],
        "ablations": {},
        "safety": {
            "robot_io": False,
            "motor_initialization": False,
            "torque_enable": False,
            "zeroing": False,
            "send_action": False,
        },
    }

    for sample in samples:
        model_summary = run_policy_case(
            policy,
            preprocessor,
            postprocessor,
            sample.state,
            sample.images,
            sample.task,
            args.robot_type,
            args.device,
        )
        payload["dataset_replay"].append(
            {
                "episode_index": sample.episode_index,
                "frame_index": sample.frame_index,
                "timestamp": sample.timestamp,
                "task": sample.task,
                "model_summary": model_summary,
                "recorded_comparison": compare_to_recorded(model_summary, sample.action, sample.state),
            }
        )

    if args.snapshot_dir is not None:
        snapshot_state = read_state_csv(args.snapshot_dir / "state_16.csv")
        snapshot_images = read_snapshot_images(args.snapshot_dir)
        ablation_sample = next((sample for sample in samples if sample.frame_index == args.ablation_frame), samples[0])
        ablation_cases = {
            "dataset_images__dataset_state": (ablation_sample.images, ablation_sample.state),
            "dataset_images__snapshot_state": (ablation_sample.images, snapshot_state),
            "snapshot_images__dataset_state": (snapshot_images, ablation_sample.state),
            "snapshot_images__snapshot_state": (snapshot_images, snapshot_state),
        }
        payload["snapshot_dir"] = str(args.snapshot_dir)
        payload["ablation_dataset_frame"] = ablation_sample.frame_index
        for name, (images, state) in ablation_cases.items():
            payload["ablations"][name] = {
                "model_summary": run_policy_case(
                    policy,
                    preprocessor,
                    postprocessor,
                    state,
                    images,
                    ablation_sample.task,
                    args.robot_type,
                    args.device,
                )
            }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    if recipe_gate is not None and not recipe_gate["summary"]["passed"]:
        print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out), "recipe_gate": "FAIL"}, indent=2))
        return 2
    print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
