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


APPROVED_SNAPSHOT_ID = "snapshot_20260513_150206"
APPROVED_PROPOSAL_SHA256 = "e4ef68ec4acb02d05679988ce7c026531e6a697b34ae0724be2bd3b734b06854"
CONFIRMATION_PHRASE = "SEND_STAGE39_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260513_150206"
RIGHT_PORT = "can1"
DRIFT_LIMIT_DEG = 1.0
DELTA_LIMIT_DEG = 2.0
TARGET_TABLE = [
    {
        "key": "right_joint_1.pos",
        "proposal_current_deg": -4.49160099029541,
        "proposal_deg": -4.036126136779785,
        "proposal_delta_deg": 0.455474853515625,
        "target_deg": -4.036126136779785,
        "target_delta_from_proposal_current_deg": 0.455474853515625,
    },
    {
        "key": "right_joint_2.pos",
        "proposal_current_deg": -1.344201683998108,
        "proposal_deg": -0.7595068216323853,
        "proposal_delta_deg": 0.5846948623657227,
        "target_deg": -0.7595068216323853,
        "target_delta_from_proposal_current_deg": 0.5846948623657227,
    },
    {
        "key": "right_joint_3.pos",
        "proposal_current_deg": 15.048501968383789,
        "proposal_deg": 14.538318634033203,
        "proposal_delta_deg": -0.5101833343505859,
        "target_deg": 14.538318634033203,
        "target_delta_from_proposal_current_deg": -0.5101833343505859,
    },
    {
        "key": "right_joint_4.pos",
        "proposal_current_deg": 8.60070514678955,
        "proposal_deg": 7.540131568908691,
        "proposal_delta_deg": -1.0605735778808594,
        "target_deg": 7.540131568908691,
        "target_delta_from_proposal_current_deg": -1.0605735778808594,
    },
    {
        "key": "right_joint_5.pos",
        "proposal_current_deg": -3.529895544052124,
        "proposal_deg": -3.4797494411468506,
        "proposal_delta_deg": 0.05014610290527344,
        "target_deg": -3.4797494411468506,
        "target_delta_from_proposal_current_deg": 0.05014610290527344,
    },
    {
        "key": "right_joint_6.pos",
        "proposal_current_deg": -0.25135478377342224,
        "proposal_deg": 0.348043829202652,
        "proposal_delta_deg": 0.5993986129760742,
        "target_deg": 0.348043829202652,
        "target_delta_from_proposal_current_deg": 0.5993986129760742,
    },
    {
        "key": "right_joint_7.pos",
        "proposal_current_deg": -1.0600615739822388,
        "proposal_deg": -0.8324557542800903,
        "proposal_delta_deg": 0.22760581970214844,
        "target_deg": -0.8324557542800903,
        "target_delta_from_proposal_current_deg": 0.22760581970214844,
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
        "# Stage 39 Guarded Served Proposal Write",
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
    lines.append("This artifact records a Stage 39 write attempt." if payload["actuator_commands_sent"] else "No actuator command was sent by this run.")
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 39 guarded write from A6000 served proposal.")
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
        "mode": "stage39_guarded_served_proposal_write",
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
