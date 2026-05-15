#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path

from guarded_first_motion_runtime_preflight import (
    APPROVED_DRY_RUN_SHA256,
    APPROVED_SNAPSHOT_ID,
    compare,
    read_current_features,
    sha256,
    validate_dry_run,
)


APPROVED_PREFLIGHT_SHA256 = "e29ca7aa1ec00a124a0f141842b7efa1a01a8bbb45397ad6ade6f9db3dcc49aa"
CONFIRMATION_PHRASE = "I_UNDERSTAND_THIS_IS_STILL_NO_SEND"


def validate_preflight(path: Path) -> dict:
    digest = sha256(path)
    if digest != APPROVED_PREFLIGHT_SHA256:
        raise SystemExit(f"Rejected preflight checksum {digest}; expected {APPROVED_PREFLIGHT_SHA256}")
    payload = json.loads(path.read_text())
    if payload.get("mode") != "runtime_preflight_no_send":
        raise SystemExit(f"Rejected preflight mode={payload.get('mode')!r}")
    if payload.get("send_allowed") is not False or payload.get("motion_allowed") is not False:
        raise SystemExit("Rejected preflight because send_allowed/motion_allowed is not false")
    if payload.get("approved_snapshot_id") != APPROVED_SNAPSHOT_ID:
        raise SystemExit(f"Rejected preflight snapshot={payload.get('approved_snapshot_id')!r}")
    if payload.get("dry_run_sha256") != APPROVED_DRY_RUN_SHA256:
        raise SystemExit(f"Rejected preflight dry_run_sha256={payload.get('dry_run_sha256')!r}")
    if payload.get("all_within_drift_limit") is not True:
        raise SystemExit("Rejected preflight because not all rows were within drift limit")
    if payload.get("blocking_keys"):
        raise SystemExit(f"Rejected preflight blocking_keys={payload.get('blocking_keys')!r}")
    if payload.get("requires_separate_operator_motion_gate") is not True:
        raise SystemExit("Rejected preflight because separate operator gate is not required")
    return {"sha256": digest, "payload": payload}


def build_packet_rows(rows: list[dict]) -> list[dict]:
    packet_rows = []
    for row in rows:
        packet_rows.append(
            {
                "key": row["key"],
                "fresh_current_deg": row["fresh_current_deg"],
                "stage15_target_deg": row["stage15_target_deg"],
                "target_delta_from_fresh_deg": row["target_delta_from_fresh_deg"],
                "held": row["held"],
                "within_drift_limit": row["within_drift_limit"],
                "would_send": False,
                "send_block_reason": "stage17_execution_not_enabled",
            }
        )
    return packet_rows


def print_table(rows: list[dict]) -> None:
    columns = [
        ("key", 18),
        ("fresh", 9),
        ("target", 9),
        ("delta", 9),
        ("held", 7),
        ("would", 7),
        ("reason", 29),
    ]
    print("".join(label.ljust(width) for label, width in columns))
    print("".join("-" * (width - 1) + " " for _, width in columns))
    for row in rows:
        values = {
            "key": row["key"],
            "fresh": f"{row['fresh_current_deg']:.3f}",
            "target": f"{row['stage15_target_deg']:.3f}",
            "delta": f"{row['target_delta_from_fresh_deg']:.3f}",
            "held": str(row["held"]).lower(),
            "would": str(row["would_send"]).lower(),
            "reason": row["send_block_reason"],
        }
        print("".join(values[label].ljust(width) for label, width in columns))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 17 no-send execution packet builder. It validates gates and prints targets, but never sends commands."
    )
    parser.add_argument("--dry-run-json", type=Path, required=True)
    parser.add_argument("--preflight-json", type=Path, required=True)
    parser.add_argument("--arm-drift-limit-deg", type=float, default=1.0)
    parser.add_argument("--gripper-drift-limit-deg", type=float, default=3.0)
    parser.add_argument("--confirm", default="")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    if args.confirm != CONFIRMATION_PHRASE:
        raise SystemExit(f"Refusing to build packet; pass --confirm {CONFIRMATION_PHRASE}")

    dry_run = validate_dry_run(args.dry_run_json)
    preflight = validate_preflight(args.preflight_json)
    current = read_current_features()
    rows = compare(
        dry_run["payload"]["plan"],
        current,
        args.arm_drift_limit_deg,
        args.gripper_drift_limit_deg,
    )
    blocking_rows = [row for row in rows if not row["within_drift_limit"]]
    if blocking_rows:
        raise SystemExit(f"Fresh readback drift check failed: {[row['key'] for row in blocking_rows]}")

    packet_rows = build_packet_rows(rows)
    payload = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "stage17_execution_packet_no_send",
        "approved_snapshot_id": APPROVED_SNAPSHOT_ID,
        "dry_run_json": str(args.dry_run_json),
        "dry_run_sha256": dry_run["sha256"],
        "preflight_json": str(args.preflight_json),
        "preflight_sha256": preflight["sha256"],
        "send_allowed": False,
        "motion_allowed": False,
        "execution_allowed": False,
        "actuator_commands_sent": False,
        "operator_confirmation_seen": True,
        "confirmation_phrase": CONFIRMATION_PHRASE,
        "read_path": "fresh DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no enable, disable, zero, goal, send_action, rollout, record, or replay",
        "requires_new_code_for_actuator_write": True,
        "requires_hold_abort_procedure": True,
        "requires_final_operator_motion_gate": True,
        "rows": packet_rows,
    }

    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    print()
    print_table(packet_rows)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
