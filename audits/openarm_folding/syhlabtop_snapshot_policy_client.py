#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


STATE_NAMES = [
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


def read_state_csv(path: Path) -> list[float]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"empty state csv: {path}")
    values = rows[1] if rows[0] == STATE_NAMES else rows[0]
    if len(values) != 16:
        raise ValueError(f"expected 16 state values, got {len(values)}")
    return [float(value) for value in values]


def post_json(url: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"server returned HTTP {exc.code}: {text}") from exc


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    proposal = payload["proposal"]
    lines = [
        "# syhlabtop A6000 Snapshot Policy Proposal",
        "",
        "## Status",
        "",
        f"- Request snapshot: `{payload['local_snapshot_dir']}`",
        f"- A6000 snapshot: `{payload['a6000_snapshot_dir']}`",
        f"- Server URL: `{payload['server_url']}`",
        f"- Proposal schema: `{proposal.get('schema')}`",
        f"- All finite: `{proposal.get('all_finite')}`",
        f"- Max abs arm delta deg: `{proposal.get('max_abs_arm_delta_deg')}`",
        "- Send allowed: `false`",
        "- Motion allowed: `false`",
        "- Actuator commands sent: `false`",
        "",
        "## Watched Deltas",
        "",
    ]
    for key, value in proposal.get("watched_deltas", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Key | Current deg | Proposed deg | Delta deg | Send allowed |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in proposal.get("rows", []):
        lines.append(
            f"| `{row['key']}` | {row['current_deg']:.6f} | {row['proposed_deg']:.6f} | "
            f"{row['delta_deg']:.6f} | `{row['send_allowed']}` |"
        )
    lines.extend(["", "## Boundary", "", "This client never sends robot actions."])
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="syhlabtop no-send client for the A6000 snapshot policy server.")
    parser.add_argument("--server-url", required=True)
    parser.add_argument("--local-snapshot-dir", type=Path, required=True)
    parser.add_argument("--a6000-snapshot-dir", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()

    metadata_path = args.local_snapshot_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    obs_id = str(metadata.get("obs_id") or args.local_snapshot_dir.name)
    request_payload = {
        "schema": "openarm_folding_observation_ref_v1",
        "obs_id": obs_id,
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "robot_type": metadata.get("robot_type", "openarms_follower"),
        "task": metadata.get("task", "Fold the T-shirt properly"),
        "state_names": STATE_NAMES,
        "state": read_state_csv(args.local_snapshot_dir / "state_16.csv"),
        "snapshot_dir": args.a6000_snapshot_dir,
        "image_keys": ["left_wrist", "right_wrist", "base"],
        "send_action": False,
    }
    proposal = post_json(args.server_url, request_payload, args.timeout_s)
    payload = {
        "schema": "openarm_folding_remote_proposal_client_result_v1",
        "server_url": args.server_url,
        "local_snapshot_dir": str(args.local_snapshot_dir),
        "a6000_snapshot_dir": args.a6000_snapshot_dir,
        "request": request_payload,
        "proposal": proposal,
        "send_allowed": False,
        "motion_allowed": False,
        "actuator_commands_sent": False,
        "motion_status": "BLOCKED",
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(args.md_out, payload)
    print(json.dumps({k: v for k, v in payload.items() if k not in {"request", "proposal"}}, indent=2, sort_keys=True))
    return 0 if proposal.get("all_finite") is True and proposal.get("send_allowed") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
