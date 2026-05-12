#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
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
from lerobot.policies.utils import prepare_observation_for_inference


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


def read_state_csv(path: Path) -> np.ndarray:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"empty state csv: {path}")
    values = rows[1] if rows[0] == ACTION_NAMES else rows[0]
    state = np.asarray([float(value) for value in values], dtype=np.float32)
    if state.shape != (16,):
        raise ValueError(f"expected 16 state values, got {state.shape}")
    return state


def read_image(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return np.asarray(image, dtype=np.uint8)


class SnapshotPolicyService:
    def __init__(self, *, model_dir: Path, device: str, allowed_snapshot_root: Path) -> None:
        self.model_dir = model_dir.resolve()
        self.device = device
        self.allowed_snapshot_root = allowed_snapshot_root.resolve()
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

    def resolve_snapshot_dir(self, raw: str) -> Path:
        snapshot_dir = Path(raw).resolve()
        if self.allowed_snapshot_root not in [snapshot_dir, *snapshot_dir.parents]:
            raise ValueError(f"snapshot_dir must be under {self.allowed_snapshot_root}: {snapshot_dir}")
        required = ["state_16.csv", "left_wrist.png", "right_wrist.png", "base.png"]
        missing = [name for name in required if not (snapshot_dir / name).exists()]
        if missing:
            raise FileNotFoundError(f"snapshot missing required files: {missing}")
        return snapshot_dir

    def predict_snapshot(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("send_action") is not False:
            raise ValueError("send_action must be false")
        snapshot_dir = self.resolve_snapshot_dir(str(request["snapshot_dir"]))
        metadata_path = snapshot_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        obs_id = str(request.get("obs_id") or metadata.get("obs_id") or snapshot_dir.name)
        task = str(request.get("task") or metadata.get("task") or "Fold the T-shirt properly")
        robot_type = str(request.get("robot_type") or metadata.get("robot_type") or "openarms_follower")

        state = read_state_csv(snapshot_dir / "state_16.csv")
        observation = {
            "observation.state": state,
            "observation.images.left_wrist": read_image(snapshot_dir / "left_wrist.png"),
            "observation.images.right_wrist": read_image(snapshot_dir / "right_wrist.png"),
            "observation.images.base": read_image(snapshot_dir / "base.png"),
        }
        prepared = prepare_observation_for_inference(
            observation,
            device=torch.device(self.device),
            task=task,
            robot_type=robot_type,
        )
        started = time.time()
        with torch.inference_mode():
            preprocessed = self.preprocessor(prepared)
            actions = self.policy.predict_action_chunk(preprocessed)
            postprocessed = self.postprocessor(actions).detach().cpu()
        latency_ms = (time.time() - started) * 1000.0

        first = postprocessed[0, 0].numpy()
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
        arm_delta = [
            abs(float(row["delta_deg"]))
            for row in rows
            if row["key"] in ARM_ACTION_NAMES
        ]
        return {
            "schema": "openarm_folding_action_proposal_v1",
            "obs_id": obs_id,
            "snapshot_dir": str(snapshot_dir),
            "model_dir": str(self.model_dir),
            "device": self.device,
            "action_names": ACTION_NAMES,
            "action_shape": list(postprocessed.shape),
            "all_finite": bool(torch.isfinite(postprocessed).all().item()),
            "predicted_abs_action": [float(value) for value in first],
            "delta_deg": [float(value) for value in deltas],
            "max_abs_arm_delta_deg": max(arm_delta) if arm_delta else None,
            "watched_deltas": {
                "right_joint_4.pos": float(deltas[ACTION_NAMES.index("right_joint_4.pos")]),
                "left_joint_4.pos": float(deltas[ACTION_NAMES.index("left_joint_4.pos")]),
                "right_joint_7.pos": float(deltas[ACTION_NAMES.index("right_joint_7.pos")]),
            },
            "rows": rows,
            "send_allowed": False,
            "motion_allowed": False,
            "actuator_commands_sent": False,
            "server_latency_ms": latency_ms,
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        }


def make_handler(service: SnapshotPolicyService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "OpenArmSnapshotPolicyServer/1.0"

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
                    "model_dir": str(service.model_dir),
                    "device": service.device,
                    "send_allowed": False,
                    "motion_allowed": False,
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/predict_snapshot":
                self._send_json(404, {"status": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                payload = service.predict_snapshot(request)
                self._send_json(200, payload)
            except Exception as exc:
                self._send_json(
                    400,
                    {
                        "schema": "openarm_folding_action_proposal_v1",
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
    parser = argparse.ArgumentParser(description="A6000 no-send snapshot policy HTTP server.")
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--allowed-snapshot-root", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    service = SnapshotPolicyService(
        model_dir=args.model_dir,
        device=args.device,
        allowed_snapshot_root=args.allowed_snapshot_root,
    )
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    print(
        json.dumps(
            {
                "status": "serving",
                "host": args.host,
                "port": args.port,
                "model_dir": str(service.model_dir),
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
