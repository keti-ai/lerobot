#!/usr/bin/env python
"""Summarize WB1 RTC window logs from policy_server output."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any


FIELD_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>[^|]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze WB1 RTC window delay log lines.")
    parser.add_argument("log_path", type=Path, help="policy_server log file to parse.")
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional path to write parsed summary JSON.",
    )
    return parser.parse_args()


def parse_value(raw: str) -> Any:
    value = raw.strip()
    if value == "None":
        return None
    if value == "True":
        return True
    if value == "False":
        return False
    if value.endswith("s"):
        numeric = value[:-1]
        try:
            return float(numeric)
        except ValueError:
            pass
    try:
        if any(char in value for char in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_fields(line: str) -> dict[str, Any]:
    return {match.group("key"): parse_value(match.group("value")) for match in FIELD_RE.finditer(line)}


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = max(0, math.ceil(q * len(sorted_values)) - 1)
    return sorted_values[index]


def summarize_numeric(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "p50": statistics.median(values),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


def main() -> None:
    args = parse_args()
    lines = args.log_path.read_text(errors="ignore").splitlines()
    config_rows = [parse_fields(line) for line in lines if "WB1 RTC window config" in line]
    delay_rows = [parse_fields(line) for line in lines if "WB1 RTC window delay" in line]

    delay_current = [
        float(row["delay_steps_current"]) for row in delay_rows if row.get("delay_steps_current") is not None
    ]
    delay_qmax = [
        float(row["delay_steps_qmax"]) for row in delay_rows if row.get("delay_steps_qmax") is not None
    ]
    upper = [
        float(row["window_upper_H_minus_d"])
        for row in delay_rows
        if row.get("window_upper_H_minus_d") is not None
    ]
    window_ok_values = [row.get("window_ok") for row in delay_rows if row.get("window_ok") is not None]
    window_ok_count = sum(1 for value in window_ok_values if value is True)
    window_false_count = sum(1 for value in window_ok_values if value is False)

    latest_config = config_rows[-1] if config_rows else {}
    latest_delay = delay_rows[-1] if delay_rows else {}
    summary: dict[str, Any] = {
        "log_path": str(args.log_path),
        "config_count": len(config_rows),
        "delay_count": len(delay_rows),
        "latest_config": latest_config,
        "latest_delay": latest_delay,
        "delay_steps_current": summarize_numeric(delay_current),
        "delay_steps_qmax": summarize_numeric(delay_qmax),
        "window_upper_H_minus_d": summarize_numeric(upper),
        "window_ok_count": window_ok_count,
        "window_false_count": window_false_count,
        "window_ok_rate": window_ok_count / len(window_ok_values) if window_ok_values else None,
    }

    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
