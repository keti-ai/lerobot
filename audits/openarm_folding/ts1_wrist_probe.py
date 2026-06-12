"""TS1 debug probe: drive ONE joint of the right arm through the velocity profile
(OnlineTrajectoryGenerator) and log target q / commanded q / readback q per tick.

Purpose: verify the trajectory streamer math against the real plant — tracking error,
lag, achieved tick rate — isolated from VLA/server/cameras. Single arm (can1), motors only.

Safety: operator + E-stop required. The probe moves exactly one joint by --delta-deg
(clamped inside the side-specific joint limits with a margin), holds, then returns.
All other joints are commanded to hold their start position.

Usage:
  uv run python audits/openarm_folding/ts1_wrist_probe.py --dry-run            # no robot
  uv run python audits/openarm_folding/ts1_wrist_probe.py --joint joint_7 --delta-deg 90
"""

from __future__ import annotations

import argparse
import csv
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from lerobot.robots import openarm_follower  # noqa: F401  (plugin registration)
from lerobot.utils.joint_trajectory import JointProfileLimits, OnlineTrajectoryGenerator
from lerobot.utils.robot_utils import precise_sleep

LOG_DIR = Path("/home/syhlabtop/k4_logs")
JOINTS = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7", "gripper"]
LIMIT_MARGIN_DEG = 3.0
SETTLE_ERR_DEG = 0.3
SETTLE_EXTRA_S = 0.5


@dataclass
class Row:
    t: float
    phase: str
    target: float
    cmd: float
    readback: float


class DryRunPlant:
    """First-order lag plant (tau=30ms) so the script can be tested without a robot."""

    def __init__(self, initial: dict[str, float]):
        self.state = dict(initial)
        self.tau = 0.03
        self._last = time.perf_counter()

    def send_action(self, action: dict[str, float]) -> dict[str, float]:
        now = time.perf_counter()
        dt = max(1e-4, now - self._last)
        self._last = now
        alpha = min(1.0, dt / self.tau)
        for key, value in action.items():
            name = key.removesuffix(".pos")
            self.state[name] += alpha * (value - self.state[name])
        return action

    def read_positions(self) -> dict[str, float]:
        return dict(self.state)


def connect_robot():
    from lerobot.robots.openarm_follower import OpenArmFollower, OpenArmFollowerConfig

    config = OpenArmFollowerConfig(
        id="openarm_right_wrist_probe",
        port="can1",
        side="right",
        max_relative_target=None,
        cameras={},
    )
    robot = OpenArmFollower(config)
    robot.connect()
    return robot


def read_present(robot) -> dict[str, float]:
    observation = robot.get_observation()
    return {j: float(observation[f"{j}.pos"]) for j in JOINTS}


def read_back(robot) -> dict[str, float]:
    """Positions from the MIT response cache (no extra bus traffic)."""
    try:
        states = robot.bus._last_known_states  # noqa: SLF001 (audit probe)
        return {j: float(states[j].get("position", float("nan"))) for j in JOINTS}
    except AttributeError:
        return read_present(robot)


def run_phase(
    *,
    phase: str,
    generator: OnlineTrajectoryGenerator,
    target_vec: np.ndarray,
    moving_joint_idx: int,
    send_fn,
    readback_fn,
    rate_hz: int,
    timeout_s: float,
    rows: list[Row],
    t0: float,
) -> dict[str, float]:
    dt = 1.0 / rate_hz
    generator.set_target(target_vec)
    settled_since = None
    tick_durations = []
    overruns = 0
    while True:
        tick_start = time.perf_counter()
        cmd = generator.step(dt)
        send_fn({f"{JOINTS[i]}.pos": float(cmd[i]) for i in range(len(JOINTS))})
        readback = readback_fn()
        now = time.perf_counter()
        rows.append(
            Row(
                t=now - t0,
                phase=phase,
                target=float(target_vec[moving_joint_idx]),
                cmd=float(cmd[moving_joint_idx]),
                readback=readback[JOINTS[moving_joint_idx]],
            )
        )
        err = abs(target_vec[moving_joint_idx] - readback[JOINTS[moving_joint_idx]])
        if err < SETTLE_ERR_DEG:
            settled_since = settled_since or now
            if now - settled_since > SETTLE_EXTRA_S:
                break
        else:
            settled_since = None
        elapsed = time.perf_counter() - tick_start
        tick_durations.append(elapsed)
        if elapsed > dt:
            overruns += 1
        if now - t0 > timeout_s:
            print(f"[{phase}] timeout after {timeout_s:.1f}s (residual err {err:.2f} deg)")
            break
        precise_sleep(max(0.0, dt - elapsed))
    return {
        "achieved_hz": 1.0 / max(np.mean(tick_durations), 1e-9) if tick_durations else 0.0,
        "mean_tick_ms": float(np.mean(tick_durations)) * 1000 if tick_durations else 0.0,
        "p95_tick_ms": float(np.percentile(tick_durations, 95)) * 1000 if tick_durations else 0.0,
        "overruns": overruns,
        "ticks": len(tick_durations),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--joint", default="joint_7", choices=JOINTS)
    parser.add_argument("--delta-deg", type=float, default=90.0)
    parser.add_argument("--rate-hz", type=int, default=100)
    parser.add_argument("--profile", default="trapezoidal", choices=["trapezoidal", "scurve"])
    parser.add_argument("--v-max", type=float, default=120.0)
    parser.add_argument("--a-max", type=float, default=1500.0)
    parser.add_argument("--j-max", type=float, default=15000.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Skip the operator confirmation prompt")
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args()

    moving_idx = JOINTS.index(args.joint)

    if args.dry_run:
        start = {j: 0.0 for j in JOINTS}
        plant = DryRunPlant(start)
        send_fn, readback_fn = plant.send_action, plant.read_positions
        limits_for_clamp = None
        robot = None
    else:
        robot = connect_robot()
        start = read_present(robot)
        send_fn = robot.send_action
        readback_fn = lambda: read_back(robot)  # noqa: E731
        limits_for_clamp = robot.config.joint_limits
        print(f"Connected. Present positions: { {j: round(v, 2) for j, v in start.items()} }")

    # Build the target: move only the selected joint, clamped inside joint limits.
    delta = args.delta_deg
    target_q = start[args.joint] + delta
    if limits_for_clamp and args.joint in limits_for_clamp:
        lo, hi = limits_for_clamp[args.joint]
        lo, hi = lo + LIMIT_MARGIN_DEG, hi - LIMIT_MARGIN_DEG
        clamped = min(max(target_q, lo), hi)
        if abs(clamped - start[args.joint]) < abs(delta) * 0.5:
            alt = min(max(start[args.joint] - delta, lo), hi)
            if abs(alt - start[args.joint]) > abs(clamped - start[args.joint]):
                clamped = alt
        if clamped != target_q:
            print(f"Target clamped by joint limits: {target_q:.1f} -> {clamped:.1f} deg")
        target_q = clamped
    achievable_delta = target_q - start[args.joint]
    print(
        f"Probe: {args.joint} {start[args.joint]:.2f} -> {target_q:.2f} deg "
        f"(delta {achievable_delta:+.2f}), profile={args.profile}, "
        f"v_max={args.v_max} deg/s, a_max={args.a_max} deg/s^2, rate={args.rate_hz} Hz"
    )

    if not args.dry_run and not args.yes:
        answer = input("Operator ready (E-stop in hand)? Type 'go' to move: ").strip().lower()
        if answer != "go":
            print("Aborted.")
            if robot is not None:
                robot.disconnect()
            return

    moving_limits = JointProfileLimits(v_max=args.v_max, a_max=args.a_max, j_max=args.j_max)
    hold_limits = JointProfileLimits(v_max=60.0, a_max=400.0, j_max=8000.0)
    limits = {j: (moving_limits if j == args.joint else hold_limits) for j in JOINTS}

    generator = OnlineTrajectoryGenerator([f"{j}.pos" for j in JOINTS], limits, profile=args.profile)
    start_vec = np.array([start[j] for j in JOINTS])
    generator.reset(start_vec)

    move_vec = start_vec.copy()
    move_vec[moving_idx] = target_q
    timeout = abs(achievable_delta) / args.v_max + 4.0

    rows: list[Row] = []
    t0 = time.perf_counter()
    stats_move = run_phase(
        phase="move", generator=generator, target_vec=move_vec, moving_joint_idx=moving_idx,
        send_fn=send_fn, readback_fn=readback_fn, rate_hz=args.rate_hz,
        timeout_s=timeout, rows=rows, t0=t0,
    )
    time.sleep(0.3)
    stats_back = run_phase(
        phase="return", generator=generator, target_vec=start_vec, moving_joint_idx=moving_idx,
        send_fn=send_fn, readback_fn=readback_fn, rate_hz=args.rate_hz,
        timeout_s=(time.perf_counter() - t0) + timeout, rows=rows, t0=t0,
    )

    if robot is not None:
        robot.disconnect()

    # --- analysis ---
    arr_t = np.array([r.t for r in rows])
    arr_cmd = np.array([r.cmd for r in rows])
    arr_rb = np.array([r.readback for r in rows])
    track_err = np.abs(arr_cmd - arr_rb)
    cmd_vel = np.abs(np.gradient(arr_cmd, arr_t, edge_order=1))
    rb_vel = np.abs(np.gradient(arr_rb, arr_t, edge_order=1))

    csv_path = args.csv or LOG_DIR / f"ts1_wrist_probe_{args.joint}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "phase", "target_q", "cmd_q", "readback_q"])
        writer.writerows([(r.t, r.phase, r.target, r.cmd, r.readback) for r in rows])

    actual_hz = (len(rows) - 1) / max(arr_t[-1] - arr_t[0], 1e-9)
    print("\n=== TS1 wrist probe summary ===")
    print(f"  joint: {args.joint} | delta: {achievable_delta:+.2f} deg | profile: {args.profile}")
    print(f"  actual loop rate: {actual_hz:.1f} Hz (requested {args.rate_hz})")
    print(f"  move : work-bound max {stats_move['achieved_hz']:.0f} Hz "
          f"(mean tick {stats_move['mean_tick_ms']:.2f} ms, p95 {stats_move['p95_tick_ms']:.2f} ms, "
          f"overruns {stats_move['overruns']}/{stats_move['ticks']})")
    print(f"  return: work-bound max {stats_back['achieved_hz']:.0f} Hz (overruns {stats_back['overruns']}/{stats_back['ticks']})")
    print(f"  tracking err |cmd-readback|: mean {track_err.mean():.3f} deg | max {track_err.max():.3f} deg")
    print(f"  cmd peak vel: {cmd_vel.max():.1f} deg/s (v_max {args.v_max}) | readback peak vel: {rb_vel.max():.1f} deg/s")
    print(f"  final readback err vs start: {abs(arr_rb[-1] - start[args.joint]):.3f} deg")
    print(f"  csv: {csv_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        ax1.plot(arr_t, [r.target for r in rows], "k--", label="target q")
        ax1.plot(arr_t, arr_cmd, "b-", label="cmd q (profile)")
        ax1.plot(arr_t, arr_rb, "r-", alpha=0.7, label="readback q")
        ax1.set_ylabel("deg"); ax1.legend(); ax1.set_title(f"{args.joint} {args.profile} probe")
        ax2.plot(arr_t, np.gradient(arr_cmd, arr_t), "b-", label="cmd vel")
        ax2.plot(arr_t, np.gradient(arr_rb, arr_t), "r-", alpha=0.7, label="readback vel")
        ax2.axhline(args.v_max, color="gray", ls=":"); ax2.axhline(-args.v_max, color="gray", ls=":")
        ax2.set_ylabel("deg/s"); ax2.set_xlabel("s"); ax2.legend()
        png_path = csv_path.with_suffix(".png")
        fig.savefig(png_path, dpi=110, bbox_inches="tight")
        print(f"  png: {png_path}")
    except Exception as exc:  # matplotlib optional
        print(f"  (no png: {exc})")


if __name__ == "__main__":
    main()
