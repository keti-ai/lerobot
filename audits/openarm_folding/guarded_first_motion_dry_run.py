#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


APPROVED_SNAPSHOT_ID = "snapshot_20260511_154554"
APPROVED_CSV_SHA256 = "ae203f49bca1d05ea01f9cd43affec69b45750d843c1809fde2bc7d64f8d1fb6"
APPROVED_JSON_SHA256 = "75a2136cb6eba5d3870d4d23a516d9b3050a21d1055871562b8e839142bfb6a1"

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

DEFAULT_HOLD_KEYS = {"left_joint_7.pos"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def parse_hold_keys(raw: str) -> set[str]:
    if raw.strip().lower() in {"", "none"}:
        return set()
    if raw.strip().lower() == "default":
        return set(DEFAULT_HOLD_KEYS)
    return {item.strip() for item in raw.split(",") if item.strip()}


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


def validate_artifacts(csv_path: Path, json_path: Path | None, rows: list[dict[str, str]]) -> dict:
    obs_ids = {row["obs_id"] for row in rows}
    if obs_ids != {APPROVED_SNAPSHOT_ID}:
        raise SystemExit(f"Rejected stale or unexpected obs_id set: {sorted(obs_ids)}")

    if any(parse_bool(row["send_allowed"]) for row in rows):
        raise SystemExit("Rejected review CSV because at least one row has send_allowed=true")

    csv_digest = sha256(csv_path)
    if csv_digest != APPROVED_CSV_SHA256:
        raise SystemExit(f"Rejected CSV checksum {csv_digest}; expected {APPROVED_CSV_SHA256}")

    payload = None
    json_digest = None
    if json_path is not None:
        json_digest = sha256(json_path)
        if json_digest != APPROVED_JSON_SHA256:
            raise SystemExit(f"Rejected JSON checksum {json_digest}; expected {APPROVED_JSON_SHA256}")
        payload = json.loads(json_path.read_text())
        if payload.get("send_allowed") is not False:
            raise SystemExit("Rejected review JSON because send_allowed is not false")
        if payload.get("all_finite") is not True:
            raise SystemExit("Rejected review JSON because all_finite is not true")
        if payload.get("action_shape") != [1, 30, 16]:
            raise SystemExit(f"Rejected review JSON action_shape={payload.get('action_shape')}")
        if not str(payload.get("snapshot_dir", "")).endswith(APPROVED_SNAPSHOT_ID):
            raise SystemExit(f"Rejected review JSON snapshot_dir={payload.get('snapshot_dir')!r}")

    return {"csv_sha256": csv_digest, "json_sha256": json_digest, "json": payload}


def capped_target(current: float, clamped: float, cap: float) -> tuple[float, float]:
    delta = clamped - current
    if delta > cap:
        delta = cap
    elif delta < -cap:
        delta = -cap
    return current + delta, delta


def build_plan(rows: list[dict[str, str]], arm_cap: float, gripper_cap: float, hold_keys: set[str]) -> list[dict]:
    plan = []
    for row in rows:
        key = row["key"]
        current = float(row["current_deg"])
        proposed = float(row["proposed_deg"])
        clamped = float(row["clamped_deg"])
        raw_delta = proposed - current
        clamped_delta = clamped - current
        cap = gripper_cap if "gripper" in key else arm_cap
        held = key in hold_keys
        if held:
            final = current
            final_delta = 0.0
            reason = "held_by_stage15_default"
        else:
            final, final_delta = capped_target(current, clamped, cap)
            reason = "capped_from_clamped_target" if abs(final_delta - clamped_delta) > 1e-9 else "clamped_target_within_cap"
        plan.append(
            {
                "key": key,
                "current_deg": current,
                "proposed_deg": proposed,
                "clamped_deg": clamped,
                "raw_delta_deg": raw_delta,
                "clamped_delta_deg": clamped_delta,
                "cap_deg": cap,
                "final_target_deg": final,
                "final_delta_deg": final_delta,
                "held": held,
                "reason": reason,
            }
        )
    return plan


def print_table(plan: list[dict]) -> None:
    columns = [
        ("key", 18),
        ("current", 9),
        ("proposed", 9),
        ("clamped", 9),
        ("cap", 7),
        ("target", 9),
        ("delta", 8),
        ("reason", 26),
    ]
    print("".join(label.ljust(width) for label, width in columns))
    print("".join("-" * (width - 1) + " " for _, width in columns))
    for row in plan:
        values = {
            "key": row["key"],
            "current": f"{row['current_deg']:.3f}",
            "proposed": f"{row['proposed_deg']:.3f}",
            "clamped": f"{row['clamped_deg']:.3f}",
            "cap": f"{row['cap_deg']:.3f}",
            "target": f"{row['final_target_deg']:.3f}",
            "delta": f"{row['final_delta_deg']:.3f}",
            "reason": row["reason"],
        }
        print("".join(values[label].ljust(width) for label, width in columns))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 15 guarded first-motion dry-run planner. This script never sends robot commands."
    )
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--review-json", type=Path)
    parser.add_argument("--action-id", type=int, default=0)
    parser.add_argument("--arm-cap-deg", type=float, default=2.0)
    parser.add_argument("--gripper-cap-deg", type=float, default=5.0)
    parser.add_argument(
        "--hold-keys",
        default="default",
        help="Comma-separated feature names to hold, 'default' for left_joint_7.pos, or 'none'.",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    if args.arm_cap_deg <= 0 or args.gripper_cap_deg <= 0:
        raise SystemExit("Caps must be positive")

    rows = load_rows(args.review_csv, args.action_id)
    validation = validate_artifacts(args.review_csv, args.review_json, rows)
    hold_keys = parse_hold_keys(args.hold_keys)
    unknown_holds = sorted(hold_keys - set(ACTION_NAMES))
    if unknown_holds:
        raise SystemExit(f"Unknown hold keys: {unknown_holds}")

    plan = build_plan(rows, args.arm_cap_deg, args.gripper_cap_deg, hold_keys)
    max_abs_final_delta = max(abs(row["final_delta_deg"]) for row in plan)
    payload = {
        "mode": "dry_run_only",
        "send_allowed": False,
        "motion_allowed": False,
        "approved_snapshot_id": APPROVED_SNAPSHOT_ID,
        "action_id": args.action_id,
        "review_csv": str(args.review_csv),
        "review_json": str(args.review_json) if args.review_json else None,
        "csv_sha256": validation["csv_sha256"],
        "json_sha256": validation["json_sha256"],
        "arm_cap_deg": args.arm_cap_deg,
        "gripper_cap_deg": args.gripper_cap_deg,
        "hold_keys": sorted(hold_keys),
        "max_abs_final_delta_deg": max_abs_final_delta,
        "requires_separate_operator_motion_gate": True,
        "plan": plan,
    }

    print(json.dumps({k: v for k, v in payload.items() if k != "plan"}, indent=2, sort_keys=True))
    print()
    print_table(plan)

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
