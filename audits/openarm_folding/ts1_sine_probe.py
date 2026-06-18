"""TS1 sine probe: drive ONE joint with a sine wave and measure frequency response.

Purpose: quantify per-joint bandwidth — at what frequency does tracking amplitude
drop and phase lag grow? This reveals the embodiment performance ceiling independent
of the policy.

Results saved to k4_logs/ts1_sine_<joint>_<timestamp>/:
  raw.csv         — per-tick (t, freq_hz, cmd_q, readback_q)
  summary.csv     — per-frequency (freq, gain_dB, phase_lag_deg, tracking_err)
  time_domain.png — cmd vs readback overlay per frequency
  bode.png        — gain(dB) + phase_lag vs frequency

Usage:
  uv run python audits/openarm_folding/ts1_sine_probe.py --dry-run
  uv run python audits/openarm_folding/ts1_sine_probe.py --joint joint_5 --sweep
  uv run python audits/openarm_folding/ts1_sine_probe.py --joint joint_1 --freq-hz 1.0
  uv run python audits/openarm_folding/ts1_sine_probe.py --sweep --all-joints   # 전 관절 순차 실행
"""

from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path

import numpy as np

from lerobot.robots import openarm_follower  # noqa: F401  (plugin registration)
from lerobot.utils.robot_utils import precise_sleep

LOG_DIR = Path("/home/syhlabtop/k4_logs")
JOINTS = ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6", "joint_7", "gripper"]
ARM_JOINTS = JOINTS[:7]  # gripper 제외
LIMIT_MARGIN_DEG = 5.0
SETTLE_PAUSE_S = 1.5   # 주파수 간 복귀 대기
SKIP_CYCLES = 1        # 분석 시 첫 N 사이클 제외 (과도 응답 제거)
MIN_AMPLITUDE_DEG = 8.0  # 이 미만으로 클램프되면 관절 skip (마찰/백래시에 묻힘)
# 관절별 추정 최대 속도 (deg/s) — 이 이상 필요한 주파수는 자동 skip
JOINT_VMAX_EST = {
    "joint_1": 240.0, "joint_2": 180.0, "joint_3": 240.0, "joint_4": 240.0,
    "joint_5": 400.0, "joint_6": 400.0, "joint_7": 400.0, "gripper": 120.0,
}

SWEEP_FREQS = [0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]


# ---------------------------------------------------------------------------
# DryRun plant: 1차 지연 시스템 (tau=30ms) — 로봇 없이 스크립트 검증용
# ---------------------------------------------------------------------------

class DryRunPlant:
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


# ---------------------------------------------------------------------------
# Robot connect / read helpers (ts1_wrist_probe.py 와 동일 패턴)
# ---------------------------------------------------------------------------

def connect_robot():
    from lerobot.robots.openarm_follower import OpenArmFollower, OpenArmFollowerConfig

    config = OpenArmFollowerConfig(
        id="openarm_right_sine_probe",
        port="can1",
        side="right",
        max_relative_target=None,
        cameras={},
    )
    robot = OpenArmFollower(config)
    robot.connect()
    return robot


def read_present(robot) -> dict[str, float]:
    obs = robot.get_observation()
    return {j: float(obs[f"{j}.pos"]) for j in JOINTS}


def read_back(robot) -> dict[str, float]:
    try:
        states = robot.bus._last_known_states  # noqa: SLF001
        return {j: float(states[j].get("position", float("nan"))) for j in JOINTS}
    except AttributeError:
        return read_present(robot)


def read_back_full(robot) -> dict[str, dict]:
    """position + torque + temp per joint."""
    try:
        states = robot.bus._last_known_states  # noqa: SLF001
        return {
            j: {
                "position": float(states[j].get("position", float("nan"))),
                "torque":   float(states[j].get("torque",   float("nan"))),
                "temp_mos": float(states[j].get("temp_mos", float("nan"))),
            }
            for j in JOINTS
        }
    except AttributeError:
        pos = read_present(robot)
        return {j: {"position": pos[j], "torque": float("nan"), "temp_mos": float("nan")} for j in JOINTS}


# ---------------------------------------------------------------------------
# Core: 단일 주파수 사인파 구동
# ---------------------------------------------------------------------------

TORQUE_ABORT_NM = 30.0   # 이 이상이면 즉시 중단 (모터 보호)
TEMP_WARN_C    = 70.0   # 이 이상이면 경고


def run_sine_freq(
    *,
    joint: str,
    freq_hz: float,
    amplitude_deg: float,
    center_q: float,
    hold_positions: dict[str, float],
    cycles: int,
    rate_hz: int,
    send_fn,
    readback_fn,
    t0: float,
    hold_kp: float | None = None,
    read_full_fn=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """한 주파수로 사인파 구동. returns (t, cmd_q, readback_q, torque_q)."""
    dt = 1.0 / rate_hz
    n_ticks = int(cycles / freq_hz * rate_hz)

    t_arr   = np.empty(n_ticks)
    cmd_arr = np.empty(n_ticks)
    rb_arr  = np.empty(n_ticks)
    tau_arr = np.full(n_ticks, float("nan"))

    hold_kp_dict = {j: hold_kp for j in JOINTS if j != joint} if hold_kp is not None else None
    actual_ticks = 0

    tick_deadline = time.perf_counter()
    for i in range(n_ticks):
        t_phase = i * dt
        cmd_q = center_q + amplitude_deg * math.sin(2.0 * math.pi * freq_hz * t_phase)

        action = {f"{j}.pos": hold_positions[j] for j in JOINTS}
        action[f"{joint}.pos"] = cmd_q
        send_fn(action, hold_kp=hold_kp_dict)

        now = time.perf_counter()
        t_arr[i]   = now - t0
        cmd_arr[i] = cmd_q
        actual_ticks += 1

        if read_full_fn is not None:
            full = read_full_fn()
            rb_arr[i]  = full[joint]["position"]
            tau_arr[i] = full[joint]["torque"]
            temp = full[joint]["temp_mos"]
            if temp > TEMP_WARN_C:
                print(f"\n  ⚠️  {joint} temp_mos={temp:.0f}°C", end="")
            if abs(tau_arr[i]) > TORQUE_ABORT_NM:
                print(f"\n  🛑 ABORT: {joint} torque={tau_arr[i]:.1f} Nm > {TORQUE_ABORT_NM} Nm — 모터 보호 중단")
                break
        else:
            rb = readback_fn()
            rb_arr[i] = rb[joint]

        tick_deadline += dt
        remaining = tick_deadline - time.perf_counter()
        if remaining > 0:
            precise_sleep(remaining)

    return t_arr[:actual_ticks], cmd_arr[:actual_ticks], rb_arr[:actual_ticks], tau_arr[:actual_ticks]


def settle_to_center(
    *,
    joint: str,
    center_q: float,
    hold_positions: dict[str, float],
    duration_s: float,
    rate_hz: int,
    send_fn,
    hold_kp: float | None = None,
):
    """주파수 간 중심 위치로 복귀 대기."""
    dt = 1.0 / rate_hz
    n = int(duration_s * rate_hz)
    hold_kp_dict = {j: hold_kp for j in JOINTS if j != joint} if hold_kp is not None else None
    tick_deadline = time.perf_counter()
    for _ in range(n):
        action = {f"{j}.pos": hold_positions[j] for j in JOINTS}
        action[f"{joint}.pos"] = center_q
        send_fn(action, hold_kp=hold_kp_dict)
        tick_deadline += dt
        remaining = tick_deadline - time.perf_counter()
        if remaining > 0:
            precise_sleep(remaining)


# ---------------------------------------------------------------------------
# Analysis: gain / phase lag 계산
# ---------------------------------------------------------------------------

def analyze_response(
    t: np.ndarray,
    cmd: np.ndarray,
    readback: np.ndarray,
    freq_hz: float,
) -> dict:
    """cmd / readback 배열에서 gain(dB), phase_lag_deg, tracking_err 반환."""
    dt_mean = float(np.mean(np.diff(t))) if len(t) > 1 else 1.0 / 100
    skip = int(SKIP_CYCLES / freq_hz / dt_mean)
    cmd_s = cmd[skip:]
    rb_s = readback[skip:]

    if len(cmd_s) < 8:
        return {
            "gain": float("nan"), "gain_db": float("nan"),
            "phase_lag_deg": float("nan"), "tracking_err_mean": float("nan"),
            "cmd_amp": float("nan"), "rb_amp": float("nan"),
        }

    # 진폭: peak-to-peak / 2
    cmd_amp = (cmd_s.max() - cmd_s.min()) / 2.0
    rb_amp = (rb_s.max() - rb_s.min()) / 2.0
    gain = rb_amp / cmd_amp if cmd_amp > 0.5 else float("nan")
    gain_db = 20.0 * math.log10(max(gain, 1e-6)) if not math.isnan(gain) else float("nan")

    # 위상 지연: 교차 상관
    # correlate(rb, cmd)[M] 의 peak 이 M > len-1 이면 rb 가 cmd 보다 뒤처짐 (양수 lag)
    cmd_n = cmd_s - cmd_s.mean()
    rb_n = rb_s - rb_s.mean()
    corr = np.correlate(rb_n, cmd_n, mode="full")
    lag_samples = int(np.argmax(corr)) - (len(cmd_n) - 1)  # 양수 = readback 지연
    phase_lag_s = lag_samples * dt_mean
    phase_lag_deg = phase_lag_s * freq_hz * 360.0
    # [-180, 180] 범위로 정규화
    phase_lag_deg %= 360.0
    if phase_lag_deg > 180.0:
        phase_lag_deg -= 360.0

    return {
        "gain": gain,
        "gain_db": gain_db,
        "phase_lag_deg": phase_lag_deg,
        "tracking_err_mean": float(np.abs(cmd_s - rb_s).mean()),
        "cmd_amp": float(cmd_amp),
        "rb_amp": float(rb_amp),
    }


# ---------------------------------------------------------------------------
# Per-joint sweep
# ---------------------------------------------------------------------------

def probe_joint(
    *,
    joint: str,
    freqs: list[float],
    amplitude_deg: float,
    cycles: int,
    rate_hz: int,
    send_fn,
    readback_fn,
    read_full_fn,
    start: dict[str, float],
    limits_for_clamp,
    out_dir: Path,
    t0: float,
    hold_kp: float | None = None,
):
    center_q = start[joint]
    amplitude = amplitude_deg

    if limits_for_clamp and joint in limits_for_clamp:
        lo, hi = limits_for_clamp[joint]
        max_amp = min(center_q - (lo + LIMIT_MARGIN_DEG), (hi - LIMIT_MARGIN_DEG) - center_q)
        max_amp = max(0.0, max_amp)
        if amplitude > max_amp:
            print(f"  [{joint}] amplitude clamped {amplitude:.1f} → {max_amp:.1f} deg")
            amplitude = max_amp

    if amplitude < MIN_AMPLITUDE_DEG:
        print(f"  [{joint}] amplitude {amplitude:.1f}° < {MIN_AMPLITUDE_DEG}° (joint limit 근처) — skip")
        return None

    # 속도 포화 주파수 필터: 2π·f·A > v_max 이면 모터가 추종 불가 → 의미 없는 데이터
    v_max = JOINT_VMAX_EST.get(joint, 240.0)
    runnable = [f for f in freqs if 2 * math.pi * f * amplitude <= v_max]
    skipped = [f for f in freqs if f not in runnable]
    if skipped:
        print(f"  [{joint}] skip {skipped} Hz (peak vel > {v_max:.0f}°/s — 속도 포화)")
    freqs = runnable
    if not freqs:
        print(f"  [{joint}] 모든 주파수가 속도 포화 범위 — skip")
        return None

    print(f"\n[{joint}] center={center_q:.1f}°  ±{amplitude:.1f}°  freqs={freqs}")

    hold_positions = dict(start)
    results = []
    all_rows = []

    for freq_hz in freqs:
        print(f"  {freq_hz:.2f} Hz ... ", end="", flush=True)
        t_arr, cmd_arr, rb_arr, tau_arr = run_sine_freq(
            joint=joint,
            freq_hz=freq_hz,
            amplitude_deg=amplitude,
            center_q=center_q,
            hold_positions=hold_positions,
            cycles=cycles,
            rate_hz=rate_hz,
            send_fn=send_fn,
            readback_fn=readback_fn,
            t0=t0,
            hold_kp=hold_kp,
            read_full_fn=read_full_fn,
        )
        m = analyze_response(t_arr, cmd_arr, rb_arr, freq_hz)
        tau_peak = float(np.nanmax(np.abs(tau_arr))) if not np.all(np.isnan(tau_arr)) else float("nan")
        results.append({"freq_hz": freq_hz, "torque_peak": tau_peak, **m})
        for i in range(len(t_arr)):
            all_rows.append((t_arr[i], freq_hz, cmd_arr[i], rb_arr[i], tau_arr[i]))

        tau_str = f"  τ_peak={tau_peak:.1f}Nm" if not math.isnan(tau_peak) else ""
        print(
            f"gain={m['gain_db']:+.1f} dB  "
            f"phase_lag={m['phase_lag_deg']:.1f}°  "
            f"track_err={m['tracking_err_mean']:.2f}°{tau_str}"
        )

        # 토크 한계 초과로 조기 종료됐으면 sweep 중단
        if tau_peak > TORQUE_ABORT_NM * 0.9:
            print(f"  [{joint}] 토크 한계 근접 — 이후 주파수 skip")
            break

        if freq_hz != freqs[-1]:
            settle_to_center(
                joint=joint, center_q=center_q, hold_positions=hold_positions,
                duration_s=SETTLE_PAUSE_S, rate_hz=rate_hz, send_fn=send_fn,
                hold_kp=hold_kp,
            )

    # 저장
    joint_dir = out_dir / joint
    joint_dir.mkdir(parents=True, exist_ok=True)

    csv_path = joint_dir / "raw.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "freq_hz", "cmd_q", "readback_q", "torque"])
        writer.writerows(all_rows)

    summary_path = joint_dir / "summary.csv"
    with open(summary_path, "w", newline="") as f:
        fieldnames = ["freq_hz", "gain", "gain_db", "phase_lag_deg", "tracking_err_mean",
                      "cmd_amp", "rb_amp", "torque_peak"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    _plot(joint, freqs, all_rows, results, joint_dir)
    return results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot(joint: str, freqs: list[float], all_rows: list, results: list[dict], out_dir: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # 주파수별 시간축 데이터 분리
        freq_data: dict[float, tuple[list, list, list]] = {}
        for row in all_rows:
            t_val, f_val, cmd_val, rb_val = row[0], row[1], row[2], row[3]
            if f_val not in freq_data:
                freq_data[f_val] = ([], [], [])
            freq_data[f_val][0].append(t_val)
            freq_data[f_val][1].append(cmd_val)
            freq_data[f_val][2].append(rb_val)

        # 시간 도메인 서브플롯
        n = len(freqs)
        fig, axes = plt.subplots(n, 1, figsize=(12, 3 * n), sharex=False)
        if n == 1:
            axes = [axes]
        for ax, f in zip(axes, freqs):
            if f not in freq_data:
                continue
            t_f, cmd_f, rb_f = [np.array(x) for x in freq_data[f]]
            t_f = t_f - t_f[0]
            ax.plot(t_f, cmd_f, "b-", lw=1.2, label="cmd")
            ax.plot(t_f, rb_f, "r-", lw=1.2, alpha=0.8, label="readback")
            r = next((x for x in results if x["freq_hz"] == f), {})
            ax.set_title(
                f"{f:.2f} Hz — {r.get('gain_db', float('nan')):+.1f} dB  "
                f"phase={r.get('phase_lag_deg', float('nan')):.1f}°"
            )
            ax.set_ylabel("deg")
            ax.legend(loc="upper right", fontsize=8)
        axes[-1].set_xlabel("s")
        fig.suptitle(f"{joint} sine response (cmd vs readback)")
        fig.tight_layout()
        time_png = out_dir / "time_domain.png"
        fig.savefig(time_png, dpi=110, bbox_inches="tight")
        plt.close(fig)
        print(f"    → {time_png}")

        # Bode 플롯
        valid = [r for r in results if not math.isnan(r.get("gain_db", float("nan")))]
        if len(valid) >= 2:
            fv = [r["freq_hz"] for r in valid]
            gv = [r["gain_db"] for r in valid]
            pv = [r["phase_lag_deg"] for r in valid]

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
            ax1.semilogx(fv, gv, "bo-", lw=1.5, ms=6)
            ax1.axhline(-3, color="gray", ls="--", label="-3 dB bandwidth")
            ax1.axhline(0, color="k", ls=":", lw=0.8)
            ax1.set_ylabel("Gain (dB)")
            ax1.legend(fontsize=9)
            ax1.grid(True, which="both", alpha=0.4)
            ax1.set_title(f"{joint} — Bode plot")

            ax2.semilogx(fv, pv, "ro-", lw=1.5, ms=6)
            ax2.set_ylabel("Phase lag (deg)")
            ax2.set_xlabel("Hz")
            ax2.grid(True, which="both", alpha=0.4)
            fig.tight_layout()
            bode_png = out_dir / "bode.png"
            fig.savefig(bode_png, dpi=110, bbox_inches="tight")
            plt.close(fig)
            print(f"    → {bode_png}")

    except Exception as exc:
        print(f"    (plot skipped: {exc})")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--joint", default="joint_5", choices=JOINTS,
                        help="테스트할 관절 (기본: joint_5 손목)")
    parser.add_argument("--all-joints", action="store_true",
                        help="gripper 제외 7개 관절 전체 순차 실행")
    parser.add_argument("--amplitude-deg", type=float, default=20.0,
                        help="사인파 진폭 (°). joint limit 초과 시 자동 축소")
    parser.add_argument("--freq-hz", type=float, default=None,
                        help="단일 주파수. 미지정 시 --sweep 자동 활성")
    parser.add_argument("--sweep", action="store_true",
                        help=f"주파수 스윕: {SWEEP_FREQS} Hz")
    parser.add_argument("--cycles", type=int, default=4,
                        help="주파수당 사이클 수 (많을수록 정확)")
    parser.add_argument("--rate-hz", type=int, default=100)
    parser.add_argument("--kp", type=float, default=None,
                        help="MIT kp override for the moving joint (per-packet, 비영구)")
    parser.add_argument("--kd", type=float, default=None,
                        help="MIT kd override for the moving joint (per-packet, 비영구)")
    parser.add_argument("--hold-kp", type=float, default=None,
                        help="MIT kp override for hold joints — 높이면 커플링 저항 강화 (예: 600)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="operator 확인 건너뜀")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    # 주파수 목록 결정
    if args.freq_hz is not None:
        freqs = [args.freq_hz]
    elif args.sweep or True:  # 기본 sweep
        freqs = SWEEP_FREQS

    # 테스트할 관절 목록
    joints = ARM_JOINTS if args.all_joints else [args.joint]

    # 로봇 또는 dry-run plant 연결
    if args.dry_run:
        start = {j: 0.0 for j in JOINTS}
        plant = DryRunPlant(start)
        def send_fn(action, hold_kp=None):  # noqa: E306
            return plant.send_action(action)
        readback_fn = plant.read_positions
        read_full_fn = None   # dry-run: torque 없음
        limits_for_clamp = None
        robot = None
    else:
        robot = connect_robot()
        start = read_present(robot)
        moving_kp = {args.joint: args.kp} if args.kp is not None else {}
        custom_kd = {args.joint: args.kd} if args.kd is not None else None
        if moving_kp or custom_kd:
            print(f"Gain override on {args.joint}: kp={args.kp}, kd={args.kd} (per-packet MIT, 비영구)")
        if args.hold_kp is not None:
            print(f"Hold joints kp override: {args.hold_kp} (per-packet MIT, 비영구)")

        def send_fn(action, hold_kp=None):  # noqa: E306
            kp = dict(moving_kp)
            if hold_kp:
                kp.update(hold_kp)
            return robot.send_action(action, custom_kp=kp or None, custom_kd=custom_kd)

        readback_fn = lambda: read_back(robot)  # noqa: E731
        read_full_fn = lambda: read_back_full(robot)  # noqa: E731
        limits_for_clamp = robot.config.joint_limits
        print(f"Connected. Present: { {j: round(v, 2) for j, v in start.items()} }")

    if not args.dry_run and not args.yes:
        print(f"\n대상 관절: {joints}")
        print(f"진폭: ±{args.amplitude_deg}°  주파수: {freqs} Hz  사이클: {args.cycles}")
        answer = input("\nOperator ready (E-stop in hand)? Type 'go': ").strip().lower()
        if answer != "go":
            print("Aborted.")
            if robot:
                robot.disconnect()
            return

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = args.out_dir or LOG_DIR / f"ts1_sine_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    all_results: dict[str, list] = {}
    for joint in joints:
        res = probe_joint(
            joint=joint,
            freqs=freqs,
            amplitude_deg=args.amplitude_deg,
            cycles=args.cycles,
            rate_hz=args.rate_hz,
            send_fn=send_fn,
            readback_fn=readback_fn,
            read_full_fn=read_full_fn,
            start=start,
            limits_for_clamp=limits_for_clamp,
            out_dir=out_dir,
            t0=t0,
            hold_kp=args.hold_kp,
        )
        if res is not None:
            all_results[joint] = res

    if robot:
        robot.disconnect()

    # 전 관절 비교 요약 출력
    if len(all_results) > 1:
        print("\n=== 전 관절 비교 (1 Hz 기준) ===")
        print(f"{'joint':>10}  {'gain_dB':>8}  {'phase_lag':>10}  {'track_err':>10}")
        for jname, res in all_results.items():
            r1 = next((r for r in res if abs(r["freq_hz"] - 1.0) < 0.01), None)
            if r1:
                print(
                    f"{jname:>10}  {r1['gain_db']:>+8.1f}  "
                    f"{r1['phase_lag_deg']:>9.1f}°  "
                    f"{r1['tracking_err_mean']:>9.2f}°"
                )

    print(f"\nOutput: {out_dir}")


if __name__ == "__main__":
    main()
