from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file

import stage22_dataset_replay_and_ablation as replay


def quantile_normalize(values: np.ndarray, q01: np.ndarray, q99: np.ndarray) -> np.ndarray:
    denom = q99 - q01
    denom = np.where(denom == 0.0, 1e-8, denom)
    return 2.0 * (values - q01) / denom - 1.0


def load_action_quantiles(model_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    tensors = load_file(str(model_dir / "policy_postprocessor_step_0_unnormalizer_processor.safetensors"))
    return tensors["action.q01"].cpu().numpy(), tensors["action.q99"].cpu().numpy()


def model_raw_action(policy, preprocessor, sample: replay.DatasetSample, device: str) -> np.ndarray:
    observation = {
        "observation.state": sample.state.copy(),
        **{key: value.copy() for key, value in sample.images.items()},
    }
    prepared = replay.prepare_observation_for_inference(
        observation,
        device=torch.device(device),
        task=sample.task,
        robot_type="openarms_follower",
    )
    with torch.inference_mode():
        preprocessed = preprocessor(prepared)
        raw = policy.predict_action_chunk(preprocessed)
    return raw[0, 0].detach().cpu().numpy().astype(np.float32)


def write_markdown(path: Path, payload: dict) -> None:
    lines = [
        "# Stage 24 Normalized Target Probe",
        "",
        "## Decision",
        "",
        "The loaded model's raw normalized output does not match the normalized target computed from",
        "`recorded_action - observation.state` using the checkpoint action quantiles. This confirms",
        "that the current A6000 `folding_latest` runtime path is not reproducing dataset behavior before",
        "any robot-specific input is involved.",
        "",
        "Motion remains blocked.",
        "",
        "## Frame Summary",
        "",
    ]
    for frame in payload["frames"]:
        lines.append(
            f"- frame `{frame['frame_index']}`: mean_abs_raw_error="
            f"{frame['mean_abs_raw_error']:.3f}, max_abs_raw_error="
            f"{frame['max_abs_raw_error']:.3f} at `{frame['max_abs_raw_error_key']}`"
        )
    lines.extend(["", "## Worst Rows", ""])
    for frame in payload["frames"]:
        lines.append(f"### Frame {frame['frame_index']}")
        for row in frame["worst_rows"][:8]:
            lines.append(
                f"- `{row['key']}` raw={row['model_raw_normalized']:.3f}, "
                f"target={row['target_normalized_delta']:.3f}, "
                f"error={row['raw_minus_target']:.3f}, "
                f"recorded_delta={row['recorded_delta_deg']:.3f} deg"
            )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare raw policy output with normalized recorded relative targets.")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--episode-index", type=int, default=0)
    parser.add_argument("--frames", default="0,1,10,30")
    parser.add_argument("--video-backend", default="ffmpeg")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    info = replay.read_info(args.dataset_root)
    episode_row = replay.load_episode_row(args.dataset_root, args.episode_index)
    frame_indices = replay.parse_frame_indices(args.frames, int(episode_row["length"]))
    samples = replay.load_dataset_samples(
        args.dataset_root, info, episode_row, frame_indices, args.video_backend
    )
    q01, q99 = load_action_quantiles(args.model_dir)
    cfg, policy, preprocessor, _postprocessor = replay.load_model(args.model_dir, args.device)

    payload = {
        "model_dir": str(args.model_dir),
        "dataset_root": str(args.dataset_root),
        "episode_index": args.episode_index,
        "policy_type": cfg.type,
        "action_names": replay.ACTION_NAMES,
        "frames": [],
        "safety": {"robot_io": False, "send_action": False},
    }
    for sample in samples:
        recorded_delta = sample.action - sample.state
        target = quantile_normalize(recorded_delta, q01, q99)
        raw = model_raw_action(policy, preprocessor, sample, args.device)
        error = raw - target
        abs_error = np.abs(error)
        order = np.argsort(-abs_error)
        payload["frames"].append(
            {
                "frame_index": sample.frame_index,
                "timestamp": sample.timestamp,
                "mean_abs_raw_error": float(np.mean(abs_error)),
                "max_abs_raw_error": float(abs_error[order[0]]),
                "max_abs_raw_error_key": replay.ACTION_NAMES[int(order[0])],
                "worst_rows": [
                    {
                        "key": replay.ACTION_NAMES[int(i)],
                        "model_raw_normalized": float(raw[i]),
                        "target_normalized_delta": float(target[i]),
                        "raw_minus_target": float(error[i]),
                        "recorded_delta_deg": float(recorded_delta[i]),
                    }
                    for i in order[: len(replay.ACTION_NAMES)]
                ],
            }
        )

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    print(json.dumps({"json_out": str(args.json_out), "md_out": str(args.md_out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
