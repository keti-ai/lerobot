from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
import traceback
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat
from threading import Event, Lock, Thread
from typing import Any

from lerobot.async_inference.configs import RobotClientConfig
from lerobot.async_inference.robot_client import RobotClient
from lerobot.cameras.realsense import RealSenseCameraConfig
from lerobot.robots import bi_openarm_follower, openarm_follower  # noqa: F401
from lerobot.robots.bi_openarm_follower.config_bi_openarm_follower import BiOpenArmFollowerConfig
from lerobot.robots.openarm_follower.config_openarm_follower import OpenArmFollowerConfigBase
from lerobot.utils.utils import init_logging


SERVER_ADDRESS = "10.252.205.103:8081"
POLICY_TYPE = "pi05"
POLICY_REPO = "KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime"
LOG_DIR = Path("/home/syhlabtop/k4_logs")
DIAGNOSTIC_RESULTS_CSV = LOG_DIR / "diagnostic_results.csv"
CLAMP_LOG_SNIPPET = "Relative goal position magnitude had to be clamped"

ARM_MOTORS = (
    "joint_1",
    "joint_2",
    "joint_3",
    "joint_4",
    "joint_5",
    "joint_6",
    "joint_7",
)
ALL_MOTORS = (*ARM_MOTORS, "gripper")


@dataclass(frozen=True)
class ProfileSpec:
    arm_max_relative_target: float = 5.0
    gripper_max_relative_target: float = 5.0
    chunk_size_threshold: float = 0.5
    aggregate_fn_name: str = "weighted_average"
    clamp_log_suppression: str = "console"
    write_diagnostic_csv: bool = False


PROFILES: dict[str, ProfileSpec] = {
    "k4": ProfileSpec(),
    "diag_baseline_silent": ProfileSpec(
        clamp_log_suppression="all",
        write_diagnostic_csv=True,
    ),
    "diag_gripper_cap": ProfileSpec(
        gripper_max_relative_target=65.0,
        clamp_log_suppression="all",
        write_diagnostic_csv=True,
    ),
    "diag_queue_smooth": ProfileSpec(
        gripper_max_relative_target=65.0,
        chunk_size_threshold=0.9,
        aggregate_fn_name="conservative",
        clamp_log_suppression="all",
        write_diagnostic_csv=True,
    ),
}


@dataclass
class RunMetrics:
    clamp_events: int = 0
    clamp_joint_counts: Counter[str] = field(default_factory=Counter)
    last_avg_fps: float | None = None
    max_net_latency_ms: float | None = None
    queue_empty_cnt: int = 0
    _queue_was_empty: bool = False
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_log_message(self, message: str) -> None:
        with self._lock:
            if CLAMP_LOG_SNIPPET in message:
                self.clamp_events += 1
                for joint_name in re.findall(r"'([^']+)':\s*\{", message):
                    self.clamp_joint_counts[joint_name] += 1

            if fps_match := re.search(r"Avg FPS: ([0-9.]+)", message):
                self.last_avg_fps = float(fps_match.group(1))

            if latency_match := re.search(
                r"Network latency \(server->client\): ([0-9.]+)ms", message
            ):
                latency_ms = float(latency_match.group(1))
                if self.max_net_latency_ms is None or latency_ms > self.max_net_latency_ms:
                    self.max_net_latency_ms = latency_ms

    def record_queue_state(self, *, action_started: bool, queue_empty: bool) -> None:
        with self._lock:
            if not action_started:
                self._queue_was_empty = False
                return

            if queue_empty and not self._queue_was_empty:
                self.queue_empty_cnt += 1
            self._queue_was_empty = queue_empty

    def to_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "clamp_events": self.clamp_events,
                "clamp_joint_counts": dict(sorted(self.clamp_joint_counts.items())),
                "last_avg_fps": self.last_avg_fps,
                "max_net_latency_ms": self.max_net_latency_ms,
                "queue_empty_cnt": self.queue_empty_cnt,
            }


class MetricsLogHandler(logging.Handler):
    def __init__(self, metrics: RunMetrics) -> None:
        super().__init__(level=logging.DEBUG)
        self.metrics = metrics

    def emit(self, record: logging.LogRecord) -> None:
        self.metrics.record_log_message(record.getMessage())


class ClampSuppressFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return CLAMP_LOG_SNIPPET not in record.getMessage()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="K4 live eval runner for OpenArm handover async inference.")
    parser.add_argument("--trial", required=True, help="Trial id, e.g. 01.")
    parser.add_argument("--obj", required=True, help="Object label, e.g. banana.")
    parser.add_argument("--task", required=True, help="Task prompt sent to the policy server.")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="k4",
        help="Runtime profile. Diagnostics are not counted in official K4 results.",
    )
    parser.add_argument("--duration-s", type=float, default=60.0, help="Control-loop duration after start.")
    parser.add_argument("--log-dir", type=Path, default=LOG_DIR, help="Directory for K4 sidecar logs.")
    parser.add_argument(
        "--diagnostic-csv",
        type=Path,
        default=DIAGNOSTIC_RESULTS_CSV,
        help="CSV path for diagnostic profile summaries.",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Build and print the RobotClientConfig without connecting hardware or server.",
    )
    return parser.parse_args()


def build_max_relative_target(profile: ProfileSpec) -> float | dict[str, float]:
    if profile.arm_max_relative_target == profile.gripper_max_relative_target:
        return profile.arm_max_relative_target
    return {
        **{motor_name: profile.arm_max_relative_target for motor_name in ARM_MOTORS},
        "gripper": profile.gripper_max_relative_target,
    }


def build_config(task: str, profile: ProfileSpec) -> RobotClientConfig:
    max_relative_target = build_max_relative_target(profile)
    return RobotClientConfig(
        policy_type=POLICY_TYPE,
        pretrained_name_or_path=POLICY_REPO,
        robot=BiOpenArmFollowerConfig(
            id="openarm_bimanual_follower",
            left_arm_config=OpenArmFollowerConfigBase(
                port="can0",
                side="left",
                max_relative_target=max_relative_target,
            ),
            right_arm_config=OpenArmFollowerConfigBase(
                port="can1",
                side="right",
                max_relative_target=max_relative_target,
            ),
            cameras={
                "left_wrist": RealSenseCameraConfig(
                    serial_number_or_name="315122270766",
                    width=640,
                    height=480,
                    fps=30,
                    warmup_s=3,
                ),
                "right_wrist": RealSenseCameraConfig(
                    serial_number_or_name="230322273311",
                    width=640,
                    height=480,
                    fps=30,
                    warmup_s=3,
                ),
                "base": RealSenseCameraConfig(
                    serial_number_or_name="213622075840",
                    width=640,
                    height=480,
                    fps=30,
                    warmup_s=3,
                ),
            },
        ),
        actions_per_chunk=30,
        task=task,
        server_address=SERVER_ADDRESS,
        policy_device="cuda",
        client_device="cpu",
        chunk_size_threshold=profile.chunk_size_threshold,
        fps=30,
        aggregate_fn_name=profile.aggregate_fn_name,
    )


def save_queue_outputs(action_queue_size: list[int], log_dir: Path, trial: str) -> dict[str, str | None]:
    log_dir.mkdir(parents=True, exist_ok=True)
    json_path = log_dir / f"queue_trial_{trial}.json"
    png_path = log_dir / f"queue_trial_{trial}.png"

    json_path.write_text(json.dumps(action_queue_size, indent=2), encoding="utf-8")

    if not action_queue_size:
        logging.warning("No action queue samples were collected; skipping queue PNG.")
        return {"queue_json": str(json_path), "queue_png": None}

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        _, ax = plt.subplots()
        ax.set_title(f"K4 action queue size trial {trial}")
        ax.set_xlabel("Performed action index")
        ax.set_ylabel("Action queue size")
        ax.set_ylim(0, max(action_queue_size) * 1.1 if max(action_queue_size) else 1)
        ax.grid(True, alpha=0.3)
        ax.plot(range(len(action_queue_size)), action_queue_size)
        plt.tight_layout()
        plt.savefig(png_path)
        plt.close()
        return {"queue_json": str(json_path), "queue_png": str(png_path)}
    except Exception:
        logging.exception("Failed to save queue PNG.")
        return {"queue_json": str(json_path), "queue_png": None}


def run_control_loop(
    client: RobotClient,
    *,
    task: str,
    verbose: bool,
    started: Event,
    errors: list[str],
    metrics: RunMetrics,
) -> None:
    try:
        client.start_barrier.wait()
        client.logger.info("Control loop thread starting")
        started.set()

        while client.running:
            control_loop_start = time.perf_counter()
            if client.actions_available():
                client.control_loop_action(verbose)
            with client.latest_action_lock:
                action_started = client.latest_action >= 0
            with client.action_queue_lock:
                queue_empty = client.action_queue.empty()
            metrics.record_queue_state(action_started=action_started, queue_empty=queue_empty)
            if client._ready_to_send_observation():
                client.control_loop_observation(task, verbose)
            client.logger.debug(
                f"Control loop (ms): {(time.perf_counter() - control_loop_start) * 1000:.2f}"
            )
            time.sleep(max(0, client.config.environment_dt - (time.perf_counter() - control_loop_start)))
    except Exception as exc:
        errors.append(repr(exc))
        client.logger.exception("K4 control loop failed.")
        started.set()
        client.shutdown_event.set()


def write_summary(log_dir: Path, trial: str, summary: dict[str, Any]) -> Path:
    summary_path = log_dir / f"summary_trial_{trial}.json"
    summary["summary_json"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary_path


def quiet_noisy_debug_loggers() -> None:
    for logger_name in (
        "can",
        "can.interfaces.socketcan.socketcan",
        "can.util",
        "draccus",
        "matplotlib",
        "lerobot.configs",
        "lerobot.motors.damiao.damiao",
        "lerobot.motors.openarm.damiao",
        "lerobot.transport",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def install_metrics_logging(metrics: RunMetrics, clamp_log_suppression: str) -> None:
    logging.getLogger().addHandler(MetricsLogHandler(metrics))
    suppress_filter = ClampSuppressFilter()
    for handler in logging.getLogger().handlers:
        if isinstance(handler, MetricsLogHandler):
            continue
        if clamp_log_suppression == "all":
            handler.addFilter(suppress_filter)
        elif (
            clamp_log_suppression == "console"
            and isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
        ):
            handler.addFilter(suppress_filter)


def append_diagnostic_result(csv_path: Path, summary: dict[str, Any]) -> None:
    fieldnames = [
        "trial",
        "obj",
        "profile",
        "status",
        "duration_s",
        "last_avg_fps",
        "max_net_latency_ms",
        "queue_empty_cnt",
        "clamp_events",
        "clamp_joint_counts",
        "summary_json",
        "queue_json",
        "queue_png",
    ]
    row = {field: summary.get(field) for field in fieldnames}
    row["clamp_joint_counts"] = json.dumps(summary.get("clamp_joint_counts", {}), sort_keys=True)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run_trial(args: argparse.Namespace) -> int:
    profile = PROFILES[args.profile]
    cfg = build_config(args.task, profile)

    if args.config_only:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.info("K4 runner profile %s:\n%s", args.profile, pformat(asdict(profile)))
        logging.info("K4 trial config:\n%s", pformat(asdict(cfg)))
        logging.info("config-only mode: no hardware or server connection attempted.")
        return 0

    args.log_dir.mkdir(parents=True, exist_ok=True)
    init_logging(
        log_file=args.log_dir / f"k4_runner_trial_{args.trial}_{args.obj}.debug.log",
        console_level="INFO",
        file_level="DEBUG",
    )
    quiet_noisy_debug_loggers()
    metrics = RunMetrics()
    install_metrics_logging(metrics, profile.clamp_log_suppression)
    logging.info("K4 runner profile %s:\n%s", args.profile, pformat(asdict(profile)))
    logging.info("K4 trial config:\n%s", pformat(asdict(cfg)))

    client: RobotClient | None = None
    receiver_thread: Thread | None = None
    control_thread: Thread | None = None
    control_started = Event()
    thread_errors: list[str] = []

    summary: dict[str, Any] = {
        "trial": args.trial,
        "obj": args.obj,
        "profile": args.profile,
        "task": args.task,
        "server_address": SERVER_ADDRESS,
        "policy_repo": POLICY_REPO,
        "duration_s": args.duration_s,
        "diagnostic_csv": str(args.diagnostic_csv) if profile.write_diagnostic_csv else None,
        "started_at_unix": time.time(),
        "status": "started",
    }

    try:
        hardware_start = time.perf_counter()
        client = RobotClient(cfg)
        summary["hardware_connect_latency_s"] = time.perf_counter() - hardware_start

        setup_start = time.perf_counter()
        if not client.start():
            summary["status"] = "client_start_failed"
            logging.error("RobotClient.start() returned False.")
            return 2
        summary["server_setup_latency_s"] = time.perf_counter() - setup_start

        receiver_thread = Thread(
            target=client.receive_actions,
            kwargs={"verbose": True},
            daemon=True,
            name=f"k4_receiver_{args.trial}",
        )
        control_thread = Thread(
            target=run_control_loop,
            kwargs={
                "client": client,
                "task": args.task,
                "verbose": True,
                "started": control_started,
                "errors": thread_errors,
                "metrics": metrics,
            },
            daemon=True,
            name=f"k4_control_{args.trial}",
        )

        receiver_thread.start()
        control_thread.start()

        if not control_started.wait(timeout=30):
            summary["status"] = "control_loop_start_timeout"
            raise TimeoutError("Control loop did not start within 30 seconds.")

        control_started_at = time.time()
        summary["control_started_at_unix"] = control_started_at
        logging.info("K4 control window started for %.3f seconds.", args.duration_s)

        deadline = time.monotonic() + args.duration_s
        while time.monotonic() < deadline:
            if thread_errors:
                summary["status"] = "thread_error"
                break
            if not client.running:
                summary["status"] = "client_stopped_early"
                break
            time.sleep(0.25)
        else:
            summary["status"] = "completed_control_window"

    except KeyboardInterrupt:
        summary["status"] = "keyboard_interrupt"
        summary["exception_type"] = "KeyboardInterrupt"
        summary["exception_message"] = "KeyboardInterrupt"
        summary["traceback"] = traceback.format_exc()
        logging.warning("KeyboardInterrupt received; stopping K4 client.")
        return_code = 130
    except Exception as exc:
        summary["status"] = "exception"
        summary["exception_type"] = type(exc).__name__
        summary["exception_message"] = str(exc)
        summary["traceback"] = traceback.format_exc()
        logging.error("K4 trial failed with %s: %s\n%s", type(exc).__name__, exc, summary["traceback"])
        return_code = 1
    else:
        return_code = 1 if thread_errors else 0
    finally:
        summary["ended_at_unix"] = time.time()
        summary["thread_errors"] = thread_errors

        if client is not None:
            try:
                logging.info("Stopping K4 client.")
                client.stop()
            except Exception:
                logging.exception("client.stop() failed.")

        if receiver_thread is not None:
            receiver_thread.join(timeout=5)
            summary["receiver_thread_alive_after_join"] = receiver_thread.is_alive()
            logging.info("receiver_thread_alive_after_join=%s", receiver_thread.is_alive())
        if control_thread is not None:
            control_thread.join(timeout=5)
            summary["control_thread_alive_after_join"] = control_thread.is_alive()
            logging.info("control_thread_alive_after_join=%s", control_thread.is_alive())

        if client is not None:
            summary["action_queue_samples"] = len(client.action_queue_size)
            summary.update(save_queue_outputs(client.action_queue_size, args.log_dir, args.trial))

        summary.update(metrics.to_summary())
        summary_path = write_summary(args.log_dir, args.trial, summary)
        if profile.write_diagnostic_csv:
            append_diagnostic_result(args.diagnostic_csv, summary)
            logging.info("K4 diagnostic CSV appended to %s", args.diagnostic_csv)
        logging.info("K4 summary written to %s", summary_path)
        logging.info("K4 trial final summary:\n%s", pformat(summary))

    return return_code


def main() -> int:
    args = parse_args()
    return run_trial(args)


if __name__ == "__main__":
    raise SystemExit(main())
