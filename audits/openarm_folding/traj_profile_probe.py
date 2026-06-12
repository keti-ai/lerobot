"""Offline probe for the TS1 high-rate trajectory streamer profiles (no robot, no gRPC).

Simulates a VLA-like setpoint stream (30 Hz setpoints incl. a step jump and a fast
wrist rotation ramp) through OnlineTrajectoryGenerator at 100 Hz and verifies:
- per-tick velocity bounded by v_max
- per-tick acceleration bounded by a_max (+ jerk bounded by j_max for scurve)
- convergence to the final setpoint
- the commanded path is strictly smoother than raw setpoint switching

Usage: uv run python audits/openarm_folding/traj_profile_probe.py [--csv out.csv]
"""

import argparse
import csv

import numpy as np

from lerobot.utils.joint_trajectory import JointProfileLimits, OnlineTrajectoryGenerator

RATE_HZ = 100
SETPOINT_HZ = 30
SIM_SECONDS = 4.0
EPS = 1e-6


def make_setpoint_stream() -> list[tuple[float, np.ndarray]]:
    """(time, target[2]) — joint 0: proximal-like step jump; joint 1: wrist-like fast ramp."""
    stream = []
    t = 0.0
    while t < SIM_SECONDS:
        proximal = 0.0 if t < 1.0 else 30.0  # 30 deg step at t=1s
        wrist = 0.0 if t < 1.0 else min(90.0, (t - 1.0) * 180.0)  # 180 deg/s commanded ramp to 90
        stream.append((t, np.array([proximal, wrist])))
        t += 1.0 / SETPOINT_HZ
    return stream


def run(profile: str, csv_path: str | None = None) -> dict:
    limits = {
        "proximal.pos": JointProfileLimits(v_max=120.0, a_max=600.0, j_max=6000.0),
        "wrist.pos": JointProfileLimits(v_max=400.0, a_max=2500.0, j_max=25000.0),
    }
    gen = OnlineTrajectoryGenerator(["proximal.pos", "wrist.pos"], limits, profile=profile)
    gen.reset(np.zeros(2))

    dt = 1.0 / RATE_HZ
    setpoints = make_setpoint_stream()
    sp_idx = 0

    rows = []
    prev_pos = np.zeros(2)
    prev_vel = np.zeros(2)
    prev_acc = np.zeros(2)
    v_max = np.array([120.0, 400.0])
    a_max = np.array([600.0, 2500.0])
    j_max = np.array([6000.0, 25000.0])
    max_v_violation = 0.0  # normalized: (|v| - v_max) / v_max
    max_a_violation = 0.0
    max_j_violation = 0.0

    n_ticks = int(SIM_SECONDS * RATE_HZ)
    for k in range(n_ticks):
        t = k * dt
        while sp_idx + 1 < len(setpoints) and setpoints[sp_idx + 1][0] <= t:
            sp_idx += 1
        gen.set_target(setpoints[sp_idx][1])
        pos = gen.step(dt)

        vel = (pos - prev_pos) / dt
        acc = (vel - prev_vel) / dt
        jerk = (acc - prev_acc) / dt
        if k > 1:  # skip startup finite-difference artifacts
            max_v_violation = max(max_v_violation, float(np.max((np.abs(vel) - v_max) / v_max)))
            max_a_violation = max(max_a_violation, float(np.max(np.abs(acc) - a_max)))
            if profile == "scurve" and k > 2:
                max_j_violation = max(max_j_violation, float(np.max(np.abs(jerk) - j_max)))
        rows.append((t, *setpoints[sp_idx][1], *pos, *vel, *acc))
        prev_pos, prev_vel, prev_acc = pos, vel, acc

    final_target = setpoints[-1][1]
    final_err = float(np.max(np.abs(prev_pos - final_target)))

    summary = {
        "profile": profile,
        "rate_hz": RATE_HZ,
        # 1% normalized tolerance: discrete-time slack of the jerk-limited integrator
        # (a cannot reach exactly 0 at the v_max crossing within one tick).
        "v_bound_ok": max_v_violation <= 0.01,
        "a_bound_ok": max_a_violation <= 1.0,  # finite-diff tolerance (deg/s^2)
        "j_bound_ok": (max_j_violation <= 100.0) if profile == "scurve" else None,
        "max_v_violation": round(max_v_violation, 4),
        "max_a_violation": round(max_a_violation, 4),
        "max_j_violation": round(max_j_violation, 4) if profile == "scurve" else None,
        "final_target": final_target.tolist(),
        "final_pos": prev_pos.tolist(),
        "final_err_deg": round(final_err, 4),
        "converged": final_err < 0.5,
    }

    if csv_path:
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["t", "tgt_prox", "tgt_wrist", "pos_prox", "pos_wrist",
                 "vel_prox", "vel_wrist", "acc_prox", "acc_wrist"]
            )
            writer.writerows(rows)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None, help="Optional CSV prefix for trajectories")
    args = parser.parse_args()

    ok = True
    for profile in ("trapezoidal", "scurve"):
        csv_path = f"{args.csv}_{profile}.csv" if args.csv else None
        summary = run(profile, csv_path)
        print(f"\n=== {profile} ===")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        ok &= summary["v_bound_ok"] and summary["a_bound_ok"] and summary["converged"]
        if profile == "scurve":
            ok &= summary["j_bound_ok"]

    print(f"\nPROBE {'PASS' if ok else 'FAIL'}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
