#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import json
import signal
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import cv2
import numpy as np
import pyrealsense2 as rs


IMAGE_KEYS = ["left_wrist", "right_wrist", "base"]


class RealSenseColorStream:
    def __init__(
        self,
        *,
        name: str,
        serial: str,
        width: int,
        height: int,
        fps: int,
        start_retries: int,
        read_retries: int,
    ):
        self.name = name
        self.serial = serial
        self.width = width
        self.height = height
        self.fps = fps
        self.start_retries = start_retries
        self.read_retries = read_retries
        self.pipeline = rs.pipeline()
        self.started = False
        self.actual_profile: tuple[int, int, int] | None = None

    def start(self) -> None:
        last_error: Exception | None = None
        profiles = [
            (self.width, self.height, self.fps),
            (640, 480, self.fps),
            (424, 240, self.fps),
            (640, 480, 30),
            (424, 240, 30),
            (1280, 720, 15),
            (640, 480, 15),
        ]
        profiles = list(dict.fromkeys(profiles))
        for attempt in range(1, self.start_retries + 1):
            for width, height, fps in profiles:
                cfg = rs.config()
                cfg.enable_device(self.serial)
                cfg.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
                try:
                    self.pipeline.start(cfg)
                    self.started = True
                    self.actual_profile = (width, height, fps)
                    for _ in range(10):
                        self.pipeline.wait_for_frames(2000)
                    return
                except Exception as exc:
                    last_error = exc
                    self.stop()
                    time.sleep(min(2.0, 0.1 * attempt))
        raise RuntimeError(f"{self.name} RealSense start failed after {self.start_retries} attempts: {last_error!r}")

    def read(self, timeout_ms: int) -> tuple[np.ndarray, float]:
        last_error: Exception | None = None
        for _ in range(self.read_retries):
            try:
                frames = self.pipeline.wait_for_frames(timeout_ms)
                color = frames.get_color_frame()
                if color:
                    return np.asanyarray(color.get_data()), time.time()
                last_error = RuntimeError(f"{self.name} produced no color frame")
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"{self.name} read failed after {self.read_retries} attempts: {last_error!r}")

    def stop(self) -> None:
        if self.started:
            self.pipeline.stop()
            self.started = False


class PolicyInputCameraWorker:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.streams = {
            "left_wrist": RealSenseColorStream(
                name="left_wrist",
                serial=args.left_wrist_serial,
                width=args.wrist_width,
                height=args.wrist_height,
                fps=args.camera_fps,
                start_retries=args.camera_start_retries,
                read_retries=args.camera_read_retries,
            ),
            "right_wrist": RealSenseColorStream(
                name="right_wrist",
                serial=args.right_wrist_serial,
                width=args.wrist_width,
                height=args.wrist_height,
                fps=args.camera_fps,
                start_retries=args.camera_start_retries,
                read_retries=args.camera_read_retries,
            ),
            "base": RealSenseColorStream(
                name="base",
                serial=args.base_serial,
                width=args.base_width,
                height=args.base_height,
                fps=args.camera_fps,
                start_retries=args.camera_start_retries,
                read_retries=args.camera_read_retries,
            ),
        }
        self.lock = threading.Lock()
        self.latest: dict[str, tuple[np.ndarray, float]] = {}
        self.errors: list[str] = []
        self.frame_count = 0
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        for stream in self.streams.values():
            stream.start()
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="policy-input-camera-worker", daemon=True)
        self.thread.start()

    def _loop(self) -> None:
        period = 1.0 / max(1, self.args.camera_fps)
        while self.running:
            started = time.time()
            try:
                frames = {key: stream.read(self.args.camera_timeout_ms) for key, stream in self.streams.items()}
                with self.lock:
                    self.latest = frames
                    self.frame_count += 1
            except Exception as exc:
                with self.lock:
                    self.errors.append(f"{time.time():.3f}: {exc}")
                    self.errors = self.errors[-20:]
            elapsed = time.time() - started
            if elapsed < period:
                time.sleep(period - elapsed)

    def stop(self) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=3.0)
        for stream in self.streams.values():
            stream.stop()

    def profiles(self) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "serial": stream.serial,
                "profile": list(stream.actual_profile) if stream.actual_profile is not None else None,
            }
            for key, stream in self.streams.items()
        }

    def snapshot(self) -> dict[str, tuple[np.ndarray, float]]:
        with self.lock:
            return {key: (image.copy(), timestamp) for key, (image, timestamp) in self.latest.items()}

    def status(self) -> dict[str, Any]:
        now = time.time()
        with self.lock:
            ages = {key: now - timestamp for key, (_, timestamp) in self.latest.items()}
            return {
                "schema": "openarm_folding_policy_input_viewer_status_v1",
                "image_keys": IMAGE_KEYS,
                "profiles": self.profiles(),
                "frame_count": self.frame_count,
                "camera_age_s": ages,
                "errors": list(self.errors),
                "read_only": True,
                "robot_io": False,
                "actuator_commands_sent": False,
            }


def encode_jpeg(image: np.ndarray, quality: int) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return encoded.tobytes()


def add_label(image: np.ndarray, label: str) -> np.ndarray:
    out = image.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 42), (0, 0, 0), thickness=-1)
    cv2.putText(out, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def make_mosaic(frames: dict[str, tuple[np.ndarray, float]], worker: PolicyInputCameraWorker) -> np.ndarray:
    panels = []
    now = time.time()
    profiles = worker.profiles()
    for key in IMAGE_KEYS:
        if key not in frames:
            panel = np.zeros((480, 640, 3), dtype=np.uint8)
            label = f"{key} | waiting"
        else:
            image, timestamp = frames[key]
            panel = cv2.resize(image, (640, 480), interpolation=cv2.INTER_AREA)
            profile = profiles[key]["profile"]
            serial = profiles[key]["serial"]
            profile_text = "unknown" if profile is None else f"{profile[0]}x{profile[1]}@{profile[2]}"
            label = f"{key} | serial {serial} | {profile_text} | age {now - timestamp:.2f}s"
        panels.append(add_label(panel, label))
    return np.concatenate(panels, axis=1)


def write_capture(output_dir: Path, worker: PolicyInputCameraWorker, quality: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = worker.snapshot()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    capture_dir = output_dir / f"policy_input_view_{timestamp}"
    capture_dir.mkdir(parents=True, exist_ok=False)
    files = {}
    for key, (image, _) in frames.items():
        path = capture_dir / f"{key}.jpg"
        path.write_bytes(encode_jpeg(image, quality))
        files[key] = str(path)
    mosaic_path = capture_dir / "mosaic.jpg"
    mosaic_path.write_bytes(encode_jpeg(make_mosaic(frames, worker), quality))
    manifest = {
        "schema": "openarm_folding_policy_input_view_capture_v1",
        "timestamp": timestamp,
        "image_keys": IMAGE_KEYS,
        "profiles": worker.profiles(),
        "files": files,
        "mosaic": str(mosaic_path),
        "read_only": True,
        "robot_io": False,
        "actuator_commands_sent": False,
    }
    (capture_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


class ViewerHandler(BaseHTTPRequestHandler):
    worker: PolicyInputCameraWorker
    args: argparse.Namespace

    def log_message(self, format: str, *args: Any) -> None:
        if not self.args.quiet_http:
            super().log_message(format, *args)

    def _send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                self._send_bytes(self._index().encode("utf-8"), "text/html; charset=utf-8")
                return
            if path == "/status.json":
                body = json.dumps(self.worker.status(), indent=2, sort_keys=True).encode("utf-8")
                self._send_bytes(body, "application/json")
                return
            if path == "/mosaic.jpg":
                image = make_mosaic(self.worker.snapshot(), self.worker)
                self._send_bytes(encode_jpeg(image, self.args.jpeg_quality), "image/jpeg")
                return
            if path == "/capture":
                manifest = write_capture(self.args.output_dir, self.worker, self.args.jpeg_quality)
                self._send_bytes(json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"), "application/json")
                return
            prefix = "/latest/"
            if path.startswith(prefix) and path.endswith(".jpg"):
                key = path[len(prefix) : -len(".jpg")]
                if key not in IMAGE_KEYS:
                    self._send_bytes(b"unknown image key\n", "text/plain", HTTPStatus.NOT_FOUND)
                    return
                frames = self.worker.snapshot()
                if key not in frames:
                    self._send_bytes(b"camera frame not ready\n", "text/plain", HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                image, _ = frames[key]
                self._send_bytes(encode_jpeg(image, self.args.jpeg_quality), "image/jpeg")
                return
            self._send_bytes(b"not found\n", "text/plain", HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_bytes(f"{exc}\n".encode("utf-8"), "text/plain", HTTPStatus.INTERNAL_SERVER_ERROR)

    def _index(self) -> str:
        status = self.worker.status()
        cards = []
        for key in IMAGE_KEYS:
            profile = status["profiles"][key]
            cards.append(
                f"""
                <section class="card">
                  <h2>{html.escape(key)}</h2>
                  <img id="{html.escape(key)}" src="/latest/{html.escape(key)}.jpg" />
                  <p>serial <code>{html.escape(str(profile["serial"]))}</code> · profile <code>{html.escape(str(profile["profile"]))}</code></p>
                </section>
                """
            )
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OpenArm Folding Policy Inputs</title>
  <style>
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #111; color: #eee; }}
    header {{ padding: 12px 16px; background: #1d1d1d; border-bottom: 1px solid #333; }}
    h1 {{ margin: 0; font-size: 18px; font-weight: 650; }}
    main {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; padding: 10px; }}
    .card {{ background: #181818; border: 1px solid #333; border-radius: 6px; overflow: hidden; }}
    h2 {{ margin: 0; padding: 8px 10px; font-size: 15px; }}
    img {{ display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: contain; background: #000; }}
    p {{ margin: 0; padding: 8px 10px 10px; color: #bbb; font-size: 13px; }}
    code {{ color: #e7e7e7; }}
    footer {{ padding: 0 10px 10px; color: #aaa; font-size: 13px; }}
    @media (max-width: 1100px) {{ main {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>OpenArm Folding Policy Inputs · read-only camera view · keys: left_wrist, right_wrist, base</h1>
  </header>
  <main>
    {''.join(cards)}
  </main>
  <footer>
    <p><a href="/mosaic.jpg">mosaic.jpg</a> · <a href="/status.json">status.json</a> · <a href="/capture">capture stills</a></p>
  </footer>
  <script>
    const keys = {json.dumps(IMAGE_KEYS)};
    function refresh() {{
      const t = Date.now();
      for (const key of keys) {{
        document.getElementById(key).src = `/latest/${{key}}.jpg?t=${{t}}`;
      }}
    }}
    setInterval(refresh, {int(1000 / max(1, self.args.display_fps))});
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only web viewer for the three live policy camera inputs.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--left-wrist-serial", default="315122270766")
    parser.add_argument("--right-wrist-serial", default="230322273311")
    parser.add_argument("--base-serial", default="213622075840")
    parser.add_argument("--camera-fps", type=int, default=30)
    parser.add_argument("--display-fps", type=int, default=5)
    parser.add_argument("--wrist-width", type=int, default=640)
    parser.add_argument("--wrist-height", type=int, default=480)
    parser.add_argument("--base-width", type=int, default=640)
    parser.add_argument("--base-height", type=int, default=480)
    parser.add_argument("--camera-timeout-ms", type=int, default=2000)
    parser.add_argument("--camera-start-retries", type=int, default=3)
    parser.add_argument("--camera-read-retries", type=int, default=2)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/openarm_folding_policy_input_viewer"))
    parser.add_argument("--quiet-http", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    worker = PolicyInputCameraWorker(args)
    stop_event = threading.Event()

    def request_stop(signum: int, frame: Any) -> None:  # noqa: ARG001
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    worker.start()
    ViewerHandler.worker = worker
    ViewerHandler.args = args
    server = ThreadingHTTPServer((args.host, args.port), ViewerHandler)
    server.timeout = 0.5
    print(
        json.dumps({"status": "started", "url": f"http://{args.host}:{args.port}/", "profiles": worker.profiles()}),
        flush=True,
    )
    try:
        while not stop_event.is_set():
            server.handle_request()
    finally:
        server.server_close()
        worker.stop()


if __name__ == "__main__":
    main()
