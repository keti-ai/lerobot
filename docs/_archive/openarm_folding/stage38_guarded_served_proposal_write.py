#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audits.openarm_folding import stage37_guarded_served_proposal_write as shared


APPROVED_SNAPSHOT_ID = "snapshot_20260513_130926"
APPROVED_PROPOSAL_SHA256 = "b8c6843dd3e9fde8e397f2c6f3917cdca512d4dc2c9d151da983c5d73295e182"
CONFIRMATION_PHRASE = "SEND_STAGE38_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_130926"
RIGHT_PORT = "can1"
DRIFT_LIMIT_DEG = 1.0
DELTA_LIMIT_DEG = 2.0
TARGET_TABLE = [
    {
        "key": "right_joint_1.pos",
        "proposal_current_deg": -4.775741100311279,
        "proposal_deg": -4.406299114227295,
        "proposal_delta_deg": 0.3694419860839844,
        "target_deg": -4.406299114227295,
        "target_delta_from_proposal_current_deg": 0.3694419860839844,
    },
    {
        "key": "right_joint_2.pos",
        "proposal_current_deg": -1.344201683998108,
        "proposal_deg": -1.2012239694595337,
        "proposal_delta_deg": 0.14297771453857422,
        "target_deg": -1.2012239694595337,
        "target_delta_from_proposal_current_deg": 0.14297771453857422,
    },
    {
        "key": "right_joint_3.pos",
        "proposal_current_deg": 14.939217567443848,
        "proposal_deg": 15.165236473083496,
        "proposal_delta_deg": 0.22601890563964844,
        "target_deg": 15.165236473083496,
        "target_delta_from_proposal_current_deg": 0.22601890563964844,
    },
    {
        "key": "right_joint_4.pos",
        "proposal_current_deg": 8.622562408447266,
        "proposal_deg": 8.81686019897461,
        "proposal_delta_deg": 0.19429779052734375,
        "target_deg": 8.81686019897461,
        "target_delta_from_proposal_current_deg": 0.19429779052734375,
    },
    {
        "key": "right_joint_5.pos",
        "proposal_current_deg": -3.988891363143921,
        "proposal_deg": -3.4155004024505615,
        "proposal_delta_deg": 0.5733909606933594,
        "target_deg": -3.4155004024505615,
        "target_delta_from_proposal_current_deg": 0.5733909606933594,
    },
    {
        "key": "right_joint_6.pos",
        "proposal_current_deg": -0.25135478377342224,
        "proposal_deg": -0.13464698195457458,
        "proposal_delta_deg": 0.11670780181884766,
        "target_deg": -0.13464698195457458,
        "target_delta_from_proposal_current_deg": 0.11670780181884766,
    },
    {
        "key": "right_joint_7.pos",
        "proposal_current_deg": -2.5244765281677246,
        "proposal_deg": -0.4752955436706543,
        "proposal_delta_deg": 2.0491809844970703,
        "target_deg": -0.6244765281677247,
        "target_delta_from_proposal_current_deg": 1.9,
    },
]


def configure_shared_constants() -> None:
    shared.APPROVED_SNAPSHOT_ID = APPROVED_SNAPSHOT_ID
    shared.APPROVED_PROPOSAL_SHA256 = APPROVED_PROPOSAL_SHA256
    shared.CONFIRMATION_PHRASE = CONFIRMATION_PHRASE
    shared.RIGHT_PORT = RIGHT_PORT
    shared.DRIFT_LIMIT_DEG = DRIFT_LIMIT_DEG
    shared.DELTA_LIMIT_DEG = DELTA_LIMIT_DEG
    shared.TARGET_TABLE = TARGET_TABLE


def validate_proposal(path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    digest = shared.sha256(path)
    payload = json.loads(path.read_text())
    proposal = payload.get("proposal", {})

    shared.require(digest == APPROVED_PROPOSAL_SHA256, f"proposal checksum mismatch: {digest}", errors)
    shared.require(payload.get("schema") == "openarm_folding_remote_proposal_client_result_v1", "unexpected client schema", errors)
    shared.require(proposal.get("schema") == "openarm_folding_action_proposal_v1", "unexpected proposal schema", errors)
    shared.require(proposal.get("obs_id") == APPROVED_SNAPSHOT_ID, f"unexpected obs_id: {proposal.get('obs_id')!r}", errors)
    shared.require(proposal.get("action_shape") == [1, 30, 16], "unexpected action_shape", errors)
    shared.require(proposal.get("all_finite") is True, "proposal is not all_finite", errors)
    shared.require(proposal.get("send_allowed") is False, "proposal send_allowed is not false", errors)
    shared.require(proposal.get("motion_allowed") is False, "proposal motion_allowed is not false", errors)
    shared.require(proposal.get("actuator_commands_sent") is False, "proposal actuator_commands_sent is not false", errors)

    proposal_rows = {row.get("key"): row for row in proposal.get("rows", []) if isinstance(row, dict)}
    tolerance = 1e-3
    for target in TARGET_TABLE:
        key = target["key"]
        row = proposal_rows.get(key)
        shared.require(row is not None, f"proposal missing {key}", errors)
        if row is None:
            continue
        shared.require(
            abs(float(row["current_deg"]) - float(target["proposal_current_deg"])) <= tolerance,
            f"{key} current mismatch",
            errors,
        )
        shared.require(
            abs(float(row["proposed_deg"]) - float(target["proposal_deg"])) <= tolerance,
            f"{key} proposal mismatch",
            errors,
        )
        shared.require(
            abs(float(row["delta_deg"]) - float(target["proposal_delta_deg"])) <= tolerance,
            f"{key} delta mismatch",
            errors,
        )
    return {"sha256": digest, "payload": payload}, errors


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 38 Guarded Served Proposal Write",
        "",
        "## Status",
        "",
        f"- Execute requested: `{payload['execute_requested']}`",
        f"- Motion approval: `{payload['operator_motion_approval']}`",
        f"- Proposal validation passed: `{payload['proposal_validation_passed']}`",
        f"- Fresh target validation passed: `{payload['fresh_target_validation_passed']}`",
        f"- Actuator commands sent: `{payload['actuator_commands_sent']}`",
        f"- Motion status: `{payload['motion_status']}`",
        "",
        "## Rows",
        "",
        "| Key | Fresh current deg | Target deg | Delta from fresh deg | Drift deg | Would send | Validated |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['key']}` | {row['fresh_current_deg']:.6f} | {row['target_deg']:.6f} | "
            f"{row['target_delta_from_fresh_deg']:.6f} | {row['drift_from_proposal_current_deg']:.6f} | "
            f"`{row['would_send']}` | `{row['fresh_validated']}` |"
        )
    if payload["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{error}`" for error in payload["errors"])
    lines.extend(["", "## Boundary", ""])
    lines.append("This artifact records a Stage 38 write attempt." if payload["actuator_commands_sent"] else "No actuator command was sent by this run.")
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 38 guarded write from A6000 served proposal.")
    parser.add_argument("--proposal-json", type=Path, required=True)
    parser.add_argument("--right-port", default=RIGHT_PORT)
    parser.add_argument("--hold-seconds", type=float, default=1.0)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--operator-motion-approval-given", action="store_true")
    parser.add_argument("--operator-at-robot", action="store_true")
    parser.add_argument("--power-held", action="store_true")
    parser.add_argument("--abort-ready", action="store_true")
    parser.add_argument("--estop-ready", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser.parse_args()


def main() -> int:
    configure_shared_constants()
    args = parse_args()
    if args.hold_seconds < 0:
        raise SystemExit("hold-seconds must be non-negative")
    if args.execute and args.json_out is None:
        raise SystemExit("--json-out is required with --execute")

    pre_errors: list[str] = []
    if args.execute:
        shared.require(args.operator_motion_approval_given, "--operator-motion-approval-given is required", pre_errors)
        shared.require(args.operator_at_robot, "--operator-at-robot is required", pre_errors)
        shared.require(args.power_held, "--power-held is required", pre_errors)
        shared.require(args.abort_ready, "--abort-ready is required", pre_errors)
        shared.require(args.estop_ready, "--estop-ready is required", pre_errors)
        shared.require(args.confirm == CONFIRMATION_PHRASE, f"--confirm must equal {CONFIRMATION_PHRASE}", pre_errors)
    if pre_errors:
        raise SystemExit("; ".join(pre_errors))

    proposal, proposal_errors = validate_proposal(args.proposal_json)
    selected_motors = [shared.FEATURE_TO_MOTOR[key] for key in shared.RIGHT_ARM_FEATURES]
    payload: dict[str, Any] = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "hostname": socket.gethostname(),
        "mode": "stage38_guarded_served_proposal_write",
        "approved_snapshot_id": APPROVED_SNAPSHOT_ID,
        "proposal_json": str(args.proposal_json),
        "proposal_sha256": proposal["sha256"],
        "right_port": args.right_port,
        "selected_features": shared.RIGHT_ARM_FEATURES,
        "selected_motors": selected_motors,
        "excluded": ["left_arm", "right_gripper", "left_gripper"],
        "execute_requested": bool(args.execute),
        "operator_motion_approval": "GIVEN" if args.operator_motion_approval_given else "NOT_GIVEN",
        "operator_at_robot": bool(args.operator_at_robot),
        "power_held": bool(args.power_held),
        "abort_ready": bool(args.abort_ready),
        "estop_ready": bool(args.estop_ready),
        "confirmation_phrase_matched": args.confirm == CONFIRMATION_PHRASE,
        "proposal_validation_passed": not proposal_errors,
        "fresh_target_validation_passed": False,
        "send_allowed": False,
        "motion_allowed": False,
        "execution_allowed": False,
        "actuator_commands_sent": False,
        "motion_status": "BLOCKED",
        "hold_seconds": args.hold_seconds,
        "drift_limit_deg": DRIFT_LIMIT_DEG,
        "delta_limit_deg": DELTA_LIMIT_DEG,
        "read_path": "DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states(); no OpenArmFollower.connect()",
        "write_path": "enable selected right-arm joints; one MIT batch; hold/readback; disable selected joints"
        if args.execute
        else "not_run",
        "rows": [],
        "post_write_readback_deg": None,
        "post_hold_readback_deg": None,
        "final_readback_deg": None,
        "errors": proposal_errors.copy(),
    }

    bus = shared.make_right_bus(args.right_port)
    connected = False
    torque_enabled = False
    exit_code = 0
    try:
        if proposal_errors:
            raise RuntimeError(f"proposal validation failed: {proposal_errors}")
        bus.connect(handshake=False)
        connected = True
        rows, fresh_errors = shared.build_rows(shared.read_selected(bus, selected_motors))
        payload["rows"] = rows
        payload["fresh_target_validation_passed"] = not fresh_errors
        if fresh_errors:
            payload["errors"].append(f"fresh_target_validation_failed: {fresh_errors}")
            exit_code = 2
        elif args.execute:
            payload["send_allowed"] = True
            payload["motion_allowed"] = True
            payload["execution_allowed"] = True
            payload["motion_status"] = "APPROVED_FOR_SINGLE_WRITE"
            commands = shared.build_commands(rows)
            for row in rows:
                row["would_send"] = True
            bus.enable_torque(selected_motors)
            torque_enabled = True
            bus._mit_control_batch(commands)
            payload["actuator_commands_sent"] = True
            payload["post_write_readback_deg"] = shared.read_selected(bus, selected_motors)
            time.sleep(args.hold_seconds)
            payload["post_hold_readback_deg"] = shared.read_selected(bus, selected_motors)
            bus.disable_torque(selected_motors, num_retry=2)
            torque_enabled = False
            payload["final_readback_deg"] = shared.read_selected(bus, selected_motors)
            payload["motion_status"] = "SINGLE_WRITE_ATTEMPTED"
        print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    except Exception as exc:
        payload["errors"].append(repr(exc))
        exit_code = 2
        print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))
    finally:
        if connected and torque_enabled:
            try:
                bus.disable_torque(selected_motors, num_retry=2)
            except Exception as exc:
                payload["errors"].append(f"final_disable_failed: {exc!r}")
                exit_code = 2
        if connected:
            try:
                bus.disconnect(disable_torque=False)
            except Exception as exc:
                payload["errors"].append(f"disconnect_failed: {exc!r}")
                exit_code = 2
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        if args.md_out is not None:
            args.md_out.parent.mkdir(parents=True, exist_ok=True)
            write_markdown(args.md_out, payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
