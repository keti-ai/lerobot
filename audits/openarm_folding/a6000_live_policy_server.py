#!/usr/bin/env python
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from lerobot.configs import PreTrainedConfig
from lerobot.policies import get_policy_class, make_pre_post_processors
from lerobot.policies.rtc.relative import reanchor_relative_rtc_prefix
from lerobot.policies.utils import prepare_observation_for_inference
from lerobot.processor import NormalizerProcessorStep, RelativeActionsProcessorStep


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
ARM_ACTION_NAMES = [name for name in ACTION_NAMES if "gripper" not in name]
IMAGE_KEYS = ["left_wrist", "right_wrist", "base"]
ROBOT_CONFIG_ID = "openarms_follower:16d:3cam:v1"
ACTION_SPACE_VERSION = "openarm_folding_abs_16d_deg_v1"
ACTION_UNITS = "degrees"
LIMITS = {
    "right_joint_1.pos": (-75.0, 75.0),
    "right_joint_2.pos": (-9.0, 90.0),
    "right_joint_3.pos": (-85.0, 85.0),
    "right_joint_4.pos": (0.0, 135.0),
    "right_joint_5.pos": (-85.0, 85.0),
    "right_joint_6.pos": (-40.0, 40.0),
    "right_joint_7.pos": (-80.0, 80.0),
    "right_gripper.pos": (-65.0, 0.0),
    "left_joint_1.pos": (-75.0, 75.0),
    "left_joint_2.pos": (-90.0, 9.0),
    "left_joint_3.pos": (-85.0, 85.0),
    "left_joint_4.pos": (0.0, 135.0),
    "left_joint_5.pos": (-85.0, 85.0),
    "left_joint_6.pos": (-40.0, 40.0),
    "left_joint_7.pos": (-80.0, 80.0),
    "left_gripper.pos": (-65.0, 0.0),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def live_observation_checksum(*, obs_seq: int, state: np.ndarray, image_sha256: dict[str, str]) -> str:
    payload = {
        "image_sha256": image_sha256,
        "obs_seq": int(obs_seq),
        "state": [float(value) for value in state],
        "state_names": ACTION_NAMES,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def decode_image(entry: dict[str, Any], key: str) -> tuple[np.ndarray, str]:
    if entry.get("encoding") not in {"jpeg_base64", "png_base64"}:
        raise ValueError(f"{key} unsupported encoding={entry.get('encoding')!r}")
    raw = base64.b64decode(str(entry["data"]), validate=True)
    digest = sha256_bytes(raw)
    expected = entry.get("sha256")
    if expected is not None and str(expected) != digest:
        raise ValueError(f"{key} image sha256 mismatch")
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    return np.asarray(image, dtype=np.uint8), digest


def read_live_request(request: dict[str, Any]) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, str], str]:
    state_names = request.get("state_names")
    if state_names is not None and state_names != ACTION_NAMES:
        raise ValueError("state_names mismatch")
    state = np.asarray([float(value) for value in request["state"]], dtype=np.float32)
    if state.shape != (16,):
        raise ValueError(f"expected 16 state values, got {state.shape}")
    images_in = request.get("images")
    if not isinstance(images_in, dict):
        raise ValueError("request images must be a dict")
    images: dict[str, np.ndarray] = {}
    image_sha256: dict[str, str] = {}
    for key in IMAGE_KEYS:
        if key not in images_in:
            raise ValueError(f"missing image key {key}")
        images[key], image_sha256[key] = decode_image(images_in[key], key)
    checksum = live_observation_checksum(
        obs_seq=int(request["obs_seq"]),
        state=state,
        image_sha256=image_sha256,
    )
    request_checksum = request.get("obs_checksum")
    if request_checksum is not None and str(request_checksum) != checksum:
        raise ValueError(f"obs_checksum mismatch: request={request_checksum!r} server={checksum!r}")
    return state, images, image_sha256, checksum


def find_step(pipeline: Any, cls: type) -> Any | None:
    for step in getattr(pipeline, "steps", []):
        if isinstance(step, cls):
            return step
    return None


class LivePolicyService:
    def __init__(self, *, model_dir: Path, device: str) -> None:
        self.model_dir = model_dir.resolve()
        self.device = device
        cfg = PreTrainedConfig.from_pretrained(self.model_dir)
        cfg.device = device
        if hasattr(cfg, "compile_model"):
            cfg.compile_model = False

        policy_cls = get_policy_class(cfg.type)
        self.preprocessor, self.postprocessor = make_pre_post_processors(
            policy_cfg=cfg,
            pretrained_path=str(self.model_dir),
            preprocessor_overrides={"device_processor": {"device": device}},
            postprocessor_overrides={"device_processor": {"device": "cpu"}},
        )
        self.policy = policy_cls.from_pretrained(str(self.model_dir), config=cfg, local_files_only=True)
        self.policy.eval()
        self.model_id = f"{cfg.type}:{self.model_dir.name}"
        self.checkpoint_id = self._checkpoint_id()
        self.action_normalization_id = self._action_normalization_id()
        self.relative_step = find_step(self.preprocessor, RelativeActionsProcessorStep)
        self.normalizer_step = find_step(self.preprocessor, NormalizerProcessorStep)

    def _checkpoint_id(self) -> str:
        if self.model_dir.name == "pretrained_model":
            return self.model_dir.parent.name
        return self.model_dir.name

    def _action_normalization_id(self) -> str:
        names = [
            "policy_preprocessor.json",
            "policy_postprocessor.json",
            "policy_preprocessor_step_3_normalizer_processor.safetensors",
            "policy_postprocessor_step_0_unnormalizer_processor.safetensors",
        ]
        digest = hashlib.sha256()
        for name in names:
            path = self.model_dir / name
            if not path.exists():
                continue
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(file_sha256(path).encode("ascii"))
            digest.update(b"\n")
        return f"processor_sha256:{digest.hexdigest()}"

    def _prepare_prev_leftover(self, request: dict[str, Any], state: np.ndarray) -> torch.Tensor | None:
        raw = request.get("prev_leftover_abs_action_chunk")
        if raw is None:
            return None
        if self.relative_step is None or not getattr(self.relative_step, "enabled", False):
            return torch.as_tensor(raw, dtype=torch.float32, device=self.device)
        prev_abs = torch.as_tensor(raw, dtype=torch.float32)
        current_state = torch.as_tensor(state, dtype=torch.float32).unsqueeze(0)
        return reanchor_relative_rtc_prefix(
            prev_abs,
            current_state,
            self.relative_step,
            self.normalizer_step,
            torch.device(self.device),
        )

    def predict_live(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("send_action") is not False:
            raise ValueError("send_action must be false")
        state, images, image_sha256, obs_checksum = read_live_request(request)
        task = str(request.get("task") or "Fold the T-shirt properly")
        robot_type = str(request.get("robot_type") or "openarms_follower")
        observation = {
            "observation.state": state,
            "observation.images.left_wrist": images["left_wrist"],
            "observation.images.right_wrist": images["right_wrist"],
            "observation.images.base": images["base"],
        }
        prepared = prepare_observation_for_inference(
            observation,
            device=torch.device(self.device),
            task=task,
            robot_type=robot_type,
        )
        prev_leftover = self._prepare_prev_leftover(request, state)
        rtc_kwargs: dict[str, Any] = {}
        if prev_leftover is not None:
            rtc_kwargs["prev_chunk_left_over"] = prev_leftover
            rtc_kwargs["inference_delay"] = int(request.get("inference_delay_steps", 0))
            if request.get("execution_horizon") is not None:
                rtc_kwargs["execution_horizon"] = int(request["execution_horizon"])

        started = time.time()
        # RTC guidance temporarily enables gradients inside the denoiser, so avoid
        # inference_mode here. no_grad can be locally overridden by torch.enable_grad().
        with torch.no_grad():
            preprocessed = self.preprocessor(prepared)
            raw_actions = self.policy.predict_action_chunk(preprocessed, **rtc_kwargs)
            postprocessed = self.postprocessor(raw_actions).detach().cpu()
        latency_ms = (time.time() - started) * 1000.0

        first = postprocessed[0, 0].numpy()
        chunk = postprocessed.numpy()
        deltas = first - state
        rows = []
        for idx, key in enumerate(ACTION_NAMES):
            lo, hi = LIMITS[key]
            proposed = float(first[idx])
            rows.append(
                {
                    "key": key,
                    "current_deg": float(state[idx]),
                    "proposed_deg": proposed,
                    "clamped_deg": max(lo, min(hi, proposed)),
                    "delta_deg": float(deltas[idx]),
                    "limit_min_deg": lo,
                    "limit_max_deg": hi,
                    "send_allowed": False,
                }
            )
        arm_delta = [abs(float(row["delta_deg"])) for row in rows if row["key"] in ARM_ACTION_NAMES]
        return {
            "schema": "openarm_folding_live_action_proposal_v1",
            "obs_seq": int(request["obs_seq"]),
            "obs_timestamp": request.get("obs_timestamp"),
            "obs_checksum": obs_checksum,
            "image_sha256": image_sha256,
            "model_dir": str(self.model_dir),
            "model_id": self.model_id,
            "checkpoint_id": self.checkpoint_id,
            "robot_config_id": ROBOT_CONFIG_ID,
            "action_normalization_id": self.action_normalization_id,
            "action_space_version": ACTION_SPACE_VERSION,
            "joint_order": ACTION_NAMES,
            "action_units": ACTION_UNITS,
            "is_absolute_action": True,
            "device": self.device,
            "action_names": ACTION_NAMES,
            "action_shape": list(postprocessed.shape),
            "all_finite": bool(torch.isfinite(postprocessed).all().item()),
            "predicted_abs_action": [float(value) for value in first],
            "predicted_abs_action_chunk": chunk.tolist(),
            "delta_deg": [float(value) for value in deltas],
            "max_abs_arm_delta_deg": max(arm_delta) if arm_delta else None,
            "rows": rows,
            "rtc": {
                "prev_leftover_supplied": prev_leftover is not None,
                "inference_delay_steps": int(request.get("inference_delay_steps", 0)),
                "execution_horizon": request.get("execution_horizon"),
            },
            "send_allowed": False,
            "motion_allowed": False,
            "actuator_commands_sent": False,
            "server_latency_ms": latency_ms,
            "inference_timestamp": time.strftime("%Y%m%d_%H%M%S"),
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        }


def make_handler(service: LivePolicyService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "OpenArmLivePolicyServer/1.0"

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/health":
                self._send_json(404, {"status": "not_found"})
                return
            self._send_json(
                200,
                {
                    "status": "ok",
                    "mode": "live",
                    "model_dir": str(service.model_dir),
                    "model_id": service.model_id,
                    "checkpoint_id": service.checkpoint_id,
                    "robot_config_id": ROBOT_CONFIG_ID,
                    "action_normalization_id": service.action_normalization_id,
                    "action_space_version": ACTION_SPACE_VERSION,
                    "joint_order": ACTION_NAMES,
                    "action_units": ACTION_UNITS,
                    "device": service.device,
                    "send_allowed": False,
                    "motion_allowed": False,
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/predict_live":
                self._send_json(404, {"status": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                payload = service.predict_live(request)
                self._send_json(200, payload)
            except Exception as exc:
                self._send_json(
                    400,
                    {
                        "schema": "openarm_folding_live_action_proposal_v1",
                        "status": "blocked",
                        "error": repr(exc),
                        "traceback": traceback.format_exc(),
                        "send_allowed": False,
                        "motion_allowed": False,
                        "actuator_commands_sent": False,
                    },
                )

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"{self.address_string()} - {fmt % args}", flush=True)

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="A6000 live inline-observation policy HTTP server.")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    service = LivePolicyService(model_dir=args.model_dir, device=args.device)
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    print(
        json.dumps(
            {
                "status": "serving",
                "mode": "live",
                "host": args.host,
                "port": args.port,
                "model_dir": str(service.model_dir),
                "model_id": service.model_id,
                "checkpoint_id": service.checkpoint_id,
                "device": service.device,
                "send_allowed": False,
                "motion_allowed": False,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
