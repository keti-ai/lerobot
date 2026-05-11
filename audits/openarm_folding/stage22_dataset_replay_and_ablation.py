from __future__ import annotations

import argparse
import csv
import json
import subprocess
from io import BytesIO
from dataclasses import dataclass
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
    ]
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
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    dataset_root = resolve_dataset_root(args.dataset_repo, args.dataset_root, args.dataset_revision)
    info = read_info(dataset_root)
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
    print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
