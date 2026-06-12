"""Plot/compare TS1 trajectory streamer logs (traj_trial_*.csv from k4_eval_runner).

Each log row has, per joint: setpoint q, commanded q (profile), commanded qvel,
readback q, readback qvel. Produces per-run PNGs and, when two CSVs are given,
an A/B overlay PNG (e.g. default gains vs wrist-kp x2).

Usage:
  uv run python audits/openarm_folding/traj_log_plot.py LOG_A.csv [LOG_B.csv] \
      --joints right_joint_5,right_joint_6,right_joint_7 [--labels default,kp2x]
"""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(csv_path: Path) -> tuple[np.ndarray, dict[str, dict[str, np.ndarray]]]:
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader)
        data = np.array([[float(x) for x in row] for row in reader])
    t = data[:, 0]
    series: dict[str, dict[str, np.ndarray]] = {}
    for col, name in enumerate(header[1:], start=1):
        feature, kind = name.rsplit(":", 1)
        series.setdefault(feature.removesuffix(".pos"), {})[kind] = data[:, col]
    return t, series


def plot_run(t, series, joints, title, out_png: Path):
    fig, axes = plt.subplots(len(joints), 2, figsize=(13, 3.2 * len(joints)), squeeze=False)
    for i, joint in enumerate(joints):
        s = series[joint]
        ax_q, ax_v = axes[i]
        ax_q.plot(t, s["set"], "k--", lw=1, label="VLA setpoint")
        ax_q.plot(t, s["cmd"], "b-", lw=1, label="cmd q (profile)")
        ax_q.plot(t, s["rb_q"], "r-", lw=1, alpha=0.8, label="current q (readback)")
        ax_q.set_ylabel(f"{joint}\n[deg]")
        ax_v.plot(t, s["cmd_v"], "b-", lw=1, label="cmd qvel (profile)")
        ax_v.plot(t, s["rb_v"], "r-", lw=1, alpha=0.8, label="current qvel (readback)")
        ax_v.set_ylabel("[deg/s]")
        if i == 0:
            ax_q.legend(fontsize=8)
            ax_v.legend(fontsize=8)
    axes[-1][0].set_xlabel("t [s]")
    axes[-1][1].set_xlabel("t [s]")
    fig.suptitle(title)
    fig.savefig(out_png, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_png}")


def summarize(t, series, joints, label):
    print(f"--- {label} ---")
    for joint in joints:
        s = series[joint]
        err_q = np.abs(s["cmd"] - s["rb_q"])
        err_v = np.abs(s["cmd_v"] - s["rb_v"])
        valid = ~np.isnan(err_q)
        print(
            f"  {joint}: |cmd-rb| q mean {np.nanmean(err_q):.3f} max {np.nanmax(err_q):.3f} deg"
            f" | qvel mean {np.nanmean(err_v):.2f} max {np.nanmax(err_v):.2f} deg/s"
            f" | valid {valid.mean() * 100:.0f}%"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csvs", nargs="+", type=Path)
    parser.add_argument("--joints", default="right_joint_5,right_joint_6,right_joint_7")
    parser.add_argument("--labels", default=None, help="comma labels for the runs (A/B compare)")
    args = parser.parse_args()

    joints = args.joints.split(",")
    labels = args.labels.split(",") if args.labels else [p.stem for p in args.csvs]

    runs = []
    for path, label in zip(args.csvs, labels):
        t, series = load(path)
        missing = [j for j in joints if j not in series]
        if missing:
            raise SystemExit(f"{path}: joints not in log: {missing} (available: {list(series)[:8]}...)")
        summarize(t, series, joints, label)
        plot_run(t, series, joints, label, path.with_suffix(".png"))
        runs.append((t, series, label))

    if len(runs) == 2:
        (t1, s1, l1), (t2, s2, l2) = runs
        fig, axes = plt.subplots(len(joints), 2, figsize=(13, 3.2 * len(joints)), squeeze=False)
        for i, joint in enumerate(joints):
            ax_q, ax_v = axes[i]
            ax_q.plot(t1, s1[joint]["cmd"], "k--", lw=0.8, label="cmd q")
            ax_q.plot(t1, s1[joint]["rb_q"], "b-", lw=1, label=f"current q [{l1}]")
            ax_q.plot(t2, s2[joint]["rb_q"], "r-", lw=1, alpha=0.8, label=f"current q [{l2}]")
            ax_q.set_ylabel(f"{joint}\n[deg]")
            ax_v.plot(t1, s1[joint]["rb_v"], "b-", lw=1, label=f"current qvel [{l1}]")
            ax_v.plot(t2, s2[joint]["rb_v"], "r-", lw=1, alpha=0.8, label=f"current qvel [{l2}]")
            ax_v.set_ylabel("[deg/s]")
            if i == 0:
                ax_q.legend(fontsize=8)
                ax_v.legend(fontsize=8)
        axes[-1][0].set_xlabel("t [s]")
        axes[-1][1].set_xlabel("t [s]")
        fig.suptitle(f"A/B: {l1} vs {l2}")
        out = args.csvs[0].parent / f"traj_compare_{l1}_vs_{l2}.png"
        fig.savefig(out, dpi=110, bbox_inches="tight")
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
