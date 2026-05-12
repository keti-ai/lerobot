#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


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

RIGHT_ARM_JOINTS = {
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def parse_hold_keys(raw: str) -> set[str]:
    value = raw.strip()
    if value.lower() in {"", "none"}:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def load_rows(path: Path, action_id: int) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    selected = [row for row in rows if int(row["action_id"]) == action_id]
    if len(selected) != len(ACTION_NAMES):
        raise SystemExit(f"Expected {len(ACTION_NAMES)} rows for action_id={action_id}, got {len(selected)}")
    by_key = {row["key"]: row for row in selected}
    missing = [key for key in ACTION_NAMES if key not in by_key]
    if missing:
        raise SystemExit(f"Missing action rows: {missing}")
    return [by_key[key] for key in ACTION_NAMES]


def validate_artifacts(
    *,
    csv_path: Path,
    json_path: Path,
    expected_csv_sha256: str,
    expected_json_sha256: str,
    approved_snapshot_id: str,
    rows: list[dict[str, str]],
) -> dict[str, Any]:
    obs_ids = {row["obs_id"] for row in rows}
    if obs_ids != {approved_snapshot_id}:
        raise SystemExit(f"Rejected unexpected obs_id set: {sorted(obs_ids)}")
    if any(parse_bool(row["send_allowed"]) for row in rows):
        raise SystemExit("Rejected review CSV because at least one row has send_allowed=true")

    csv_digest = sha256(csv_path)
    if csv_digest != expected_csv_sha256:
        raise SystemExit(f"Rejected CSV checksum {csv_digest}; expected {expected_csv_sha256}")

    json_digest = sha256(json_path)
    if json_digest != expected_json_sha256:
        raise SystemExit(f"Rejected JSON checksum {json_digest}; expected {expected_json_sha256}")
    payload = json.loads(json_path.read_text())
    if payload.get("send_allowed") is not False:
        raise SystemExit("Rejected review JSON because send_allowed is not false")
    if payload.get("all_finite") is not True:
        raise SystemExit("Rejected review JSON because all_finite is not true")
    if payload.get("action_shape") != [1, 30, 16]:
        raise SystemExit(f"Rejected review JSON action_shape={payload.get('action_shape')}")
    if not str(payload.get("snapshot_dir", "")).endswith(approved_snapshot_id):
        raise SystemExit(f"Rejected review JSON snapshot_dir={payload.get('snapshot_dir')!r}")
    return {"csv_sha256": csv_digest, "json_sha256": json_digest, "json": payload}


def capped_target(current: float, clamped: float, cap: float) -> tuple[float, float]:
    delta = clamped - current
    if delta > cap:
        delta = cap
    elif delta < -cap:
        delta = -cap
    return current + delta, delta


def build_plan(rows: list[dict[str, str]], arm_cap: float, gripper_cap: float, hold_keys: set[str]) -> list[dict[str, Any]]:
    plan = []
    for row in rows:
        key = row["key"]
        current = float(row["current_deg"])
        proposed = float(row["proposed_deg"])
        clamped = float(row["clamped_deg"])
        limit_min = float(row["limit_min"])
        limit_max = float(row["limit_max"])
        raw_delta = proposed - current
        clamped_delta = clamped - current
        cap = gripper_cap if "gripper" in key else arm_cap
        held = key in hold_keys
        if held:
            final = current
            final_delta = 0.0
            reason = "held_by_stage34_option"
        else:
            final, final_delta = capped_target(current, clamped, cap)
            reason = "capped_from_clamped_target" if abs(final_delta - clamped_delta) > 1e-9 else "clamped_target_within_cap"
        plan.append(
            {
                "key": key,
                "current_deg": current,
                "proposed_deg": proposed,
                "clamped_deg": clamped,
                "limit_min_deg": limit_min,
                "limit_max_deg": limit_max,
                "raw_delta_deg": raw_delta,
                "clamped_delta_deg": clamped_delta,
                "cap_deg": cap,
                "final_target_deg": final,
                "final_delta_deg": final_delta,
                "current_within_review_limits": limit_min <= current <= limit_max,
                "final_target_within_review_limits": limit_min <= final <= limit_max,
                "held": held,
                "right_arm_first_write_candidate": key in RIGHT_ARM_JOINTS,
                "reason": reason,
            }
        )
    return plan


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Stage 34 Guarded First Motion Dry Run",
        "",
        "## Status",
        "",
        "- Mode: `dry_run_only`",
        "- Send allowed: `false`",
        "- Motion allowed: `false`",
        f"- Approved snapshot: `{payload['approved_snapshot_id']}`",
        f"- Review CSV SHA256: `{payload['csv_sha256']}`",
        f"- Review JSON SHA256: `{payload['json_sha256']}`",
        "",
        "This artifact does not authorize robot motion.",
        "",
        "## Summary",
        "",
        f"- Max absolute final delta: `{payload['max_abs_final_delta_deg']:.6f} deg`",
        f"- Max absolute right-arm first-write candidate delta: `{payload['max_abs_right_arm_candidate_delta_deg']:.6f} deg`",
        f"- Right-arm first-write candidate within review limits: `{str(payload['right_arm_candidate_targets_within_review_limits']).lower()}`",
        f"- Arm cap: `{payload['arm_cap_deg']} deg`",
        f"- Gripper cap: `{payload['gripper_cap_deg']} deg`",
        f"- Hold keys: `{payload['hold_keys']}`",
        "",
        "## Plan",
        "",
        "| Key | Current deg | Proposed deg | Target deg | Final delta deg | Limits deg | Target in limits | First write candidate | Reason |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in payload["plan"]:
        lines.append(
            f"| `{row['key']}` | {row['current_deg']:.3f} | {row['proposed_deg']:.3f} | "
            f"{row['final_target_deg']:.3f} | {row['final_delta_deg']:.3f} | "
            f"[{row['limit_min_deg']:.3f}, {row['limit_max_deg']:.3f}] | "
            f"{str(row['final_target_within_review_limits']).lower()} | "
            f"{str(row['right_arm_first_write_candidate']).lower()} | `{row['reason']}` |"
        )
    if payload["blocking_first_write_keys"]:
        lines.extend(["", "## First-Write Blockers", ""])
        for key in payload["blocking_first_write_keys"]:
            lines.append(f"- `{key}` target is outside the review limits after applying the dry-run cap.")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "Run fresh syhlabtop runtime preflight before any actuator-write discussion.",
            "The fresh preflight must verify current readback drift against this dry-run table.",
            "Actuator write remains blocked until a separate explicit human approval.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parameterized guarded first-motion dry-run planner. This script never touches robot IO."
    )
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--review-json", type=Path, required=True)
    parser.add_argument("--approved-snapshot-id", required=True)
    parser.add_argument("--expected-csv-sha256", required=True)
    parser.add_argument("--expected-json-sha256", required=True)
    parser.add_argument("--action-id", type=int, default=0)
    parser.add_argument("--arm-cap-deg", type=float, default=2.0)
    parser.add_argument("--gripper-cap-deg", type=float, default=5.0)
    parser.add_argument("--hold-keys", default="none")
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()

    if args.arm_cap_deg <= 0 or args.gripper_cap_deg <= 0:
        raise SystemExit("Caps must be positive")
    hold_keys = parse_hold_keys(args.hold_keys)
    unknown_holds = sorted(hold_keys - set(ACTION_NAMES))
    if unknown_holds:
        raise SystemExit(f"Unknown hold keys: {unknown_holds}")

    rows = load_rows(args.review_csv, args.action_id)
    validation = validate_artifacts(
        csv_path=args.review_csv,
        json_path=args.review_json,
        expected_csv_sha256=args.expected_csv_sha256,
        expected_json_sha256=args.expected_json_sha256,
        approved_snapshot_id=args.approved_snapshot_id,
        rows=rows,
    )
    plan = build_plan(rows, args.arm_cap_deg, args.gripper_cap_deg, hold_keys)
    right_arm_candidate_deltas = [
        abs(row["final_delta_deg"]) for row in plan if row["right_arm_first_write_candidate"]
    ]
    blocking_first_write_keys = [
        row["key"]
        for row in plan
        if row["right_arm_first_write_candidate"] and not row["final_target_within_review_limits"]
    ]
    payload = {
        "mode": "dry_run_only",
        "send_allowed": False,
        "motion_allowed": False,
        "approved_snapshot_id": args.approved_snapshot_id,
        "action_id": args.action_id,
        "review_csv": str(args.review_csv),
        "review_json": str(args.review_json),
        "csv_sha256": validation["csv_sha256"],
        "json_sha256": validation["json_sha256"],
        "arm_cap_deg": args.arm_cap_deg,
        "gripper_cap_deg": args.gripper_cap_deg,
        "hold_keys": sorted(hold_keys),
        "first_write_scope": "right_arm_joints_only",
        "max_abs_final_delta_deg": max(abs(row["final_delta_deg"]) for row in plan),
        "max_abs_right_arm_candidate_delta_deg": max(right_arm_candidate_deltas),
        "right_arm_candidate_targets_within_review_limits": not blocking_first_write_keys,
        "blocking_first_write_keys": blocking_first_write_keys,
        "requires_fresh_runtime_preflight": True,
        "requires_separate_operator_motion_gate": True,
        "stage35_candidate_ready": False,
        "actuator_commands_sent": False,
        "plan": plan,
    }

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    write_markdown(args.md_out, payload)
    print(
        json.dumps(
            {
                "json_out": str(args.json_out),
                "md_out": str(args.md_out),
                "max_abs_final_delta_deg": payload["max_abs_final_delta_deg"],
                "max_abs_right_arm_candidate_delta_deg": payload["max_abs_right_arm_candidate_delta_deg"],
                "blocking_first_write_keys": payload["blocking_first_write_keys"],
                "send_allowed": False,
                "motion_allowed": False,
                "stage35_candidate_ready": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
