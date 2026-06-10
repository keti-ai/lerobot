#!/usr/bin/env python
"""No-robot synthetic gRPC verifier for WB1 RTC window logging.

This connects to an already running policy_server and exercises the same RPCs as
RobotClient without connecting OpenArm hardware:

1. Ready
2. SendPolicyInstructions
3. repeated SendObservations + GetActions

Use after the a6000 `k1_policy_server` has been restarted with the WB1 patch.
The server log should then contain `WB1 RTC window config` and
`WB1 RTC window delay` lines.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle  # nosec B403 - internal gRPC payload format used by async inference
import time
from pathlib import Path
from typing import Any

import grpc
import numpy as np
import torch

from lerobot.async_inference.helpers import RemotePolicyConfig, TimedObservation
from lerobot.transport import services_pb2, services_pb2_grpc
from lerobot.transport.utils import grpc_channel_options, send_bytes_in_chunks
from lerobot.utils.constants import OBS_STR
from lerobot.utils.feature_utils import hw_to_dataset_features

POLICY_REPO = "KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime"
SERVER_ADDRESS = "10.252.205.103:8081"
LOG_DIR = Path("/home/syhlabtop/k4_logs")

STATE_NAMES = tuple(
    [f"right_joint_{idx}.pos" for idx in range(1, 8)]
    + ["right_gripper.pos"]
    + [f"left_joint_{idx}.pos" for idx in range(1, 8)]
    + ["left_gripper.pos"]
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WB1 no-robot synthetic gRPC verifier.")
    parser.add_argument("--server-address", default=SERVER_ADDRESS)
    parser.add_argument("--policy-repo", default=POLICY_REPO)
    parser.add_argument("--policy-type", default="pi05")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--actions-per-chunk", type=int, default=30)
    parser.add_argument("--num-chunks", type=int, default=2)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--image-width", type=int, default=640)
    parser.add_argument("--image-height", type=int, default=480)
    parser.add_argument("--setup-timeout-s", type=float, default=600.0)
    parser.add_argument("--rpc-timeout-s", type=float, default=120.0)
    parser.add_argument(
        "--skip-policy-setup",
        action="store_true",
        help="Skip SendPolicyInstructions when the server already has the policy loaded.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=LOG_DIR / "wb1_synthetic_grpc_summary.json",
    )
    return parser.parse_args()


def build_lerobot_features(image_shape: tuple[int, int, int]) -> dict[str, dict[str, Any]]:
    hw_features: dict[str, type | tuple[int, int, int]] = {name: float for name in STATE_NAMES}
    hw_features.update(
        {
            "left_wrist": image_shape,
            "right_wrist": image_shape,
            "base": image_shape,
        }
    )
    return hw_to_dataset_features(hw_features, OBS_STR, use_video=False)


def build_observation(*, timestep: int, image_shape: tuple[int, int, int], task: str) -> TimedObservation:
    raw_obs: dict[str, Any] = {name: 0.0 for name in STATE_NAMES}
    image = np.zeros(image_shape, dtype=np.uint8)
    raw_obs.update(
        {
            "left_wrist": image,
            "right_wrist": image,
            "base": image,
            "task": task,
        }
    )
    return TimedObservation(
        timestamp=time.time(),
        timestep=timestep,
        observation=raw_obs,
        must_go=True,
    )


def finite_action_stats(timed_actions: list[Any]) -> dict[str, Any]:
    tensors = [timed_action.get_action().detach().cpu().float() for timed_action in timed_actions]
    if not tensors:
        return {
            "num_actions": 0,
            "finite": False,
            "shape": None,
            "min": None,
            "max": None,
            "first_timestep": None,
            "last_timestep": None,
        }

    stacked = torch.stack(tensors)
    return {
        "num_actions": len(timed_actions),
        "finite": bool(torch.isfinite(stacked).all().item()),
        "shape": list(stacked.shape),
        "min": float(stacked.min().item()),
        "max": float(stacked.max().item()),
        "first_timestep": int(timed_actions[0].get_timestep()),
        "last_timestep": int(timed_actions[-1].get_timestep()),
    }


def main() -> None:
    args = parse_args()
    if args.num_chunks <= 0:
        raise ValueError("--num-chunks must be positive")
    if args.actions_per_chunk <= 0:
        raise ValueError("--actions-per-chunk must be positive")
    if args.fps <= 0:
        raise ValueError("--fps must be positive")

    image_shape = (args.image_height, args.image_width, 3)
    task = "Pick the banana, hand it over to the other arm, and place it at the target."
    lerobot_features = build_lerobot_features(image_shape)
    policy_config = RemotePolicyConfig(
        policy_type=args.policy_type,
        pretrained_name_or_path=args.policy_repo,
        lerobot_features=lerobot_features,
        actions_per_chunk=args.actions_per_chunk,
        device=args.device,
    )

    channel = grpc.insecure_channel(
        args.server_address,
        grpc_channel_options(
            max_receive_message_length=16 * 1024 * 1024,
            max_send_message_length=16 * 1024 * 1024,
            initial_backoff=f"{1.0 / args.fps:.4f}s",
        ),
    )
    stub = services_pb2_grpc.AsyncInferenceStub(channel)

    summary: dict[str, Any] = {
        "server_address": args.server_address,
        "policy_repo": args.policy_repo,
        "policy_type": args.policy_type,
        "device": args.device,
        "actions_per_chunk": args.actions_per_chunk,
        "num_chunks": args.num_chunks,
        "fps": args.fps,
        "image_shape_hwc": list(image_shape),
        "chunks": [],
    }

    start = time.perf_counter()
    stub.Ready(services_pb2.Empty(), timeout=args.rpc_timeout_s)
    summary["ready_ms"] = (time.perf_counter() - start) * 1000.0

    if not args.skip_policy_setup:
        setup = services_pb2.PolicySetup(data=pickle.dumps(policy_config))  # nosec B301/B403
        start = time.perf_counter()
        stub.SendPolicyInstructions(setup, timeout=args.setup_timeout_s)
        summary["send_policy_instructions_ms"] = (time.perf_counter() - start) * 1000.0
    else:
        summary["send_policy_instructions_ms"] = None

    for idx in range(args.num_chunks):
        obs = build_observation(timestep=idx * args.actions_per_chunk, image_shape=image_shape, task=task)
        obs_bytes = pickle.dumps(obs)  # nosec B301/B403

        start_send = time.perf_counter()
        stub.SendObservations(
            send_bytes_in_chunks(obs_bytes, services_pb2.Observation, log_prefix="wb1", silent=True),
            timeout=args.rpc_timeout_s,
        )
        send_ms = (time.perf_counter() - start_send) * 1000.0

        start_get = time.perf_counter()
        actions_response = stub.GetActions(services_pb2.Empty(), timeout=args.rpc_timeout_s)
        get_ms = (time.perf_counter() - start_get) * 1000.0

        timed_actions = pickle.loads(actions_response.data) if actions_response.data else []  # nosec B301
        action_stats = finite_action_stats(timed_actions)
        summary["chunks"].append(
            {
                "idx": idx,
                "obs_timestep": obs.get_timestep(),
                "send_observation_ms": send_ms,
                "get_actions_ms": get_ms,
                **action_stats,
            }
        )

        sleep_s = max(1.0 / args.fps - (time.perf_counter() - start_get), 0.0)
        if sleep_s > 0 and idx < args.num_chunks - 1:
            time.sleep(sleep_s)

    finite = [chunk["finite"] for chunk in summary["chunks"]]
    action_counts = [chunk["num_actions"] for chunk in summary["chunks"]]
    summary["all_actions_finite"] = all(finite)
    summary["all_chunks_nonempty"] = all(count > 0 for count in action_counts)
    summary["max_get_actions_ms"] = max((chunk["get_actions_ms"] for chunk in summary["chunks"]), default=math.nan)

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
