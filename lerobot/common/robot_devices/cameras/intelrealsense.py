"""
This file contains utilities for recording frames from Intel Realsense cameras.
"""

import argparse
import concurrent.futures
import logging
import math
import shutil
import threading
import time
import traceback
from collections import Counter
from pathlib import Path
from threading import Thread

import numpy as np
import pyrealsense2 as rs
from PIL import Image
import cv2

from lerobot.common.robot_devices.cameras.configs import IntelRealSenseCameraConfig
from lerobot.common.robot_devices.utils import (
    RobotDeviceAlreadyConnectedError,
    RobotDeviceNotConnectedError,
    busy_wait,
)
from lerobot.common.utils.utils import capture_timestamp_utc

SERIAL_NUMBER_INDEX = 1


def find_cameras(raise_when_empty=True, mock=False) -> list[dict]:
    """
    Find the names and the serial numbers of the Intel RealSense cameras
    connected to the computer.
    """
    if mock:
        import tests.mock_pyrealsense2 as rs
    else:
        import pyrealsense2 as rs

    cameras = []
    for device in rs.context().query_devices():
        serial_number = int(device.get_info(rs.camera_info(SERIAL_NUMBER_INDEX)))
        name = device.get_info(rs.camera_info.name)
        cameras.append(
            {
                "serial_number": serial_number,
                "name": name,
            }
        )

    if raise_when_empty and len(cameras) == 0:
        raise OSError(
            "Not a single camera was detected. Try re-plugging, or re-installing `librealsense` and its python wrapper `pyrealsense2`, or updating the firmware."
        )

    return cameras


def save_image(img_array, serial_number, frame_index, images_dir):
    try:
        img = Image.fromarray(img_array)
        path = images_dir / f"camera_{serial_number}_frame_{frame_index:06d}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path), quality=100)
        logging.info(f"Saved image: {path}")
    except Exception as e:
        logging.error(f"Failed to save image for camera {serial_number} frame {frame_index}: {e}")


def save_images_from_cameras(
    images_dir: Path,
    serial_numbers: list[int] | None = None,
    fps=None,
    width=None,
    height=None,
    record_time_s=2,
    mock=False,
):
    """
    Initializes all the cameras and saves images to the directory. Useful to visually identify the camera
    associated to a given serial number.
    """
    if serial_numbers is None or len(serial_numbers) == 0:
        camera_infos = find_cameras(mock=mock)
        serial_numbers = [cam["serial_number"] for cam in camera_infos]

    if mock:
        import tests.mock_cv2 as cv2
    else:
        import cv2

    print("Connecting cameras")
    cameras = []
    for cam_sn in serial_numbers:
        print(f"{cam_sn=}")
        config = IntelRealSenseCameraConfig(
            serial_number=cam_sn, fps=fps, width=width, height=height, mock=mock
        )
        camera = IntelRealSenseCamera(config)
        camera.connect()
        print(
            f"IntelRealSenseCamera({camera.serial_number}, fps={camera.fps}, width={camera.width}, height={camera.height}, color_mode={camera.color_mode})"
        )
        cameras.append(camera)

    images_dir = Path(images_dir)
    if images_dir.exists():
        shutil.rmtree(
            images_dir,
        )
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving images to {images_dir}")
    frame_index = 0
    start_time = time.perf_counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            while True:
                now = time.perf_counter()

                for camera in cameras:
                    # If we use async_read when fps is None, the loop will go full speed, and we will end up
                    # saving the same images from the cameras multiple times until the RAM/disk is full.
                    image = camera.read() if fps is None else camera.async_read()
                    if image is None:
                        print("No Frame")

                    bgr_converted_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                    executor.submit(
                        save_image,
                        bgr_converted_image,
                        camera.serial_number,
                        frame_index,
                        images_dir,
                    )

                if fps is not None:
                    dt_s = time.perf_counter() - now
                    busy_wait(1 / fps - dt_s)

                if time.perf_counter() - start_time > record_time_s:
                    break

                print(f"Frame: {frame_index:04d}\tLatency (ms): {(time.perf_counter() - now) * 1000:.2f}")

                frame_index += 1
    finally:
        print(f"Images have been saved to {images_dir}")
        for camera in cameras:
            camera.disconnect()


class IntelRealSenseCamera:
    """
    The IntelRealSenseCamera class is similar to OpenCVCamera class but adds additional features for Intel Real Sense cameras:
    - is instantiated with the serial number of the camera - won't randomly change as it can be the case of OpenCVCamera for Linux,
    - can also be instantiated with the camera's name — if it's unique — using IntelRealSenseCamera.init_from_name(),
    - depth map can be returned.

    To find the camera indices of your cameras, you can run our utility script that will save a few frames for each camera:
    ```bash
    python lerobot/common/robot_devices/cameras/intelrealsense.py --images-dir outputs/images_from_intelrealsense_cameras
    ```

    When an IntelRealSenseCamera is instantiated, if no specific config is provided, the default fps, width, height and color_mode
    of the given camera will be used.

    Example of instantiating with a serial number:
    ```python
    from lerobot.common.robot_devices.cameras.configs import IntelRealSenseCameraConfig

    config = IntelRealSenseCameraConfig(serial_number=128422271347)
    camera = IntelRealSenseCamera(config)
    camera.connect()
    color_image = camera.read()
    # when done using the camera, consider disconnecting
    camera.disconnect()
    ```

    Example of instantiating with a name if it's unique:
    ```
    config = IntelRealSenseCameraConfig(name="Intel RealSense D405")
    ```

    Example of changing default fps, width, height and color_mode:
    ```python
    config = IntelRealSenseCameraConfig(serial_number=128422271347, fps=30, width=1280, height=720)
    config = IntelRealSenseCameraConfig(serial_number=128422271347, fps=90, width=640, height=480)
    config = IntelRealSenseCameraConfig(serial_number=128422271347, fps=90, width=640, height=480, color_mode="bgr")
    # Note: might error out upon `camera.connect()` if these settings are not compatible with the camera
    ```

    Example of returning depth:
    ```python
    config = IntelRealSenseCameraConfig(serial_number=128422271347, use_depth=True)
    camera = IntelRealSenseCamera(config)
    camera.connect()
    color_image, depth_map = camera.read()
    ```
    """

    def __init__(
        self,
        config: IntelRealSenseCameraConfig,
    ):
        self.config = config
        if config.name is not None:
            self.serial_number = self.find_serial_number_from_name(config.name)
        else:
            self.serial_number = config.serial_number
        self.fps = config.fps
        self.width = config.width
        self.height = config.height
        self.channels = config.channels
        self.color_mode = config.color_mode
        self.use_depth = config.use_depth
        self.force_hardware_reset = config.force_hardware_reset
        self.mock = config.mock

        self.camera = None
        self.is_connected = False
        self.thread = None
        self.stop_event = None
        self.color_image = None
        self.depth_map = None
        self.logs = {}

        if self.mock:
            import tests.mock_cv2 as cv2
        else:
            import cv2

        # TODO(alibets): Do we keep original width/height or do we define them after rotation?
        self.rotation = None
        if config.rotation == -90:
            self.rotation = cv2.ROTATE_90_COUNTERCLOCKWISE
        elif config.rotation == 90:
            self.rotation = cv2.ROTATE_90_CLOCKWISE
        elif config.rotation == 180:
            self.rotation = cv2.ROTATE_180

    def find_serial_number_from_name(self, name):
        camera_infos = find_cameras()
        camera_names = [cam["name"] for cam in camera_infos]
        this_name_count = Counter(camera_names)[name]
        if this_name_count > 1:
            # TODO(aliberts): Test this with multiple identical cameras (Aloha)
            raise ValueError(
                f"Multiple {name} cameras have been detected. Please use their serial number to instantiate them."
            )

        name_to_serial_dict = {cam["name"]: cam["serial_number"] for cam in camera_infos}
        cam_sn = name_to_serial_dict[name]

        return cam_sn

    def connect(self):
        """Connect to the camera and start the read loop."""
        if self.is_connected:
            return
            
        logging.info(f"Connecting to camera {self.serial_number}...")
        
        try:
            # Try to reset the camera if it's busy
            if self.force_hardware_reset:
                logging.info("Attempting to reset camera...")
                try:
                    ctx = rs.context()
                    devices = ctx.query_devices()
                    for dev in devices:
                        if str(dev.get_info(rs.camera_info.serial_number)) == str(self.serial_number):
                            dev.hardware_reset()
                            logging.info("Camera reset successful")
                            time.sleep(2)  # Wait for camera to reinitialize
                            break
                except Exception as e:
                    logging.warning(f"Failed to reset camera: {e}")
            
            # Initialize stop event and thread
            self.stop_event = threading.Event()
            self.thread = Thread(target=self.read_loop)
            self.thread.daemon = True
            
            # Start thread
            self.thread.start()
            logging.info("Camera thread started")
            
            # Wait for first frame
            max_tries = 30  # 3 seconds timeout
            for i in range(max_tries):
                if self.color_image is not None:
                    logging.info("Camera connected successfully")
                    self.is_connected = True
                    return
                time.sleep(0.1)
                
            raise TimeoutError("Timeout waiting for first frame")
            
        except Exception as e:
            logging.error(f"Error connecting to camera: {e}")
            self.disconnect()
            raise
            
    def read_loop(self):
        """Read frames from the camera in a loop."""
        logging.info("=== Starting read_loop ===")
        logging.info(f"Thread ID: {threading.get_ident()}")
        
        try:
            # Initialize pipeline
            logging.info("Initializing pipeline...")
            pipeline = rs.pipeline()
            config = rs.config()
            
            # Enable device
            logging.info(f"Enabling device {self.serial_number}...")
            config.enable_device(str(self.serial_number))
            
            # Enable streams
            logging.info("Enabling color stream...")
            config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            if self.use_depth:
                logging.info("Enabling depth stream...")
                config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)
            
            # Start pipeline
            logging.info("Starting pipeline...")
            pipeline.start(config)
            logging.info("Pipeline started successfully")
            
            # Get device
            device = pipeline.get_active_profile().get_device()
            logging.info(f"Device info: {device.get_info(rs.camera_info.name)}")
            
            # Main loop
            while not self.stop_event.is_set():
                try:
                    # Wait for frames
                    frames = pipeline.wait_for_frames()
                    
                    # Get color frame
                    color_frame = frames.get_color_frame()
                    if not color_frame:
                        logging.warning("No color frame available")
                        continue
                        
                    # Convert to numpy array
                    color_image = np.asanyarray(color_frame.get_data())
                    
                    # Convert BGR to RGB
                    color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
                    
                    # Get depth frame if needed
                    if self.use_depth:
                        depth_frame = frames.get_depth_frame()
                        if not depth_frame:
                            logging.warning("No depth frame available")
                            continue
                        depth_image = np.asanyarray(depth_frame.get_data())
                        self.depth_image = depth_image
                    
                    # Update color image
                    self.color_image = color_image
                    
                except Exception as e:
                    logging.error(f"Error in read_loop: {e}")
                    logging.error(traceback.format_exc())
                    time.sleep(0.1)  # Small delay before retry
                    
        except Exception as e:
            logging.error(f"Fatal error in read_loop: {e}")
            logging.error(traceback.format_exc())
            
        finally:
            logging.info("Cleaning up pipeline...")
            try:
                pipeline.stop()
            except:
                pass
            logging.info("Pipeline stopped")
            
    def read(self, temporary_color: str | None = None) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
        """Read a frame from the camera returned in the format height x width x channels (e.g. 480 x 640 x 3)
        of type `np.uint8`, contrarily to the pytorch format which is float channel first.

        When `use_depth=True`, returns a tuple `(color_image, depth_map)` with a depth map in the format
        height x width (e.g. 480 x 640) of type np.uint16.

        Note: Reading a frame is done every `camera.fps` times per second, and it is blocking.
        If you are reading data from other sensors, we advise to use `camera.async_read()` which is non blocking version of `camera.read()`.
        """
        if not self.is_connected:
            raise RobotDeviceNotConnectedError(
                f"IntelRealSenseCamera({self.serial_number}) is not connected. Try running `camera.connect()` first."
            )

        if self.mock:
            import tests.mock_cv2 as cv2
        else:
            import cv2

        start_time = time.perf_counter()

        frame = self.camera.wait_for_frames(timeout_ms=5000)

        color_frame = frame.get_color_frame()

        if not color_frame:
            raise OSError(f"Can't capture color image from IntelRealSenseCamera({self.serial_number}).")

        color_image = np.asanyarray(color_frame.get_data())

        requested_color_mode = self.color_mode if temporary_color is None else temporary_color
        if requested_color_mode not in ["rgb", "bgr"]:
            raise ValueError(
                f"Expected color values are 'rgb' or 'bgr', but {requested_color_mode} is provided."
            )

        # IntelRealSense uses RGB format as default (red, green, blue).
        if requested_color_mode == "bgr":
            color_image = cv2.cvtColor(color_image, cv2.COLOR_RGB2BGR)

        h, w, _ = color_image.shape
        if h != self.height or w != self.width:
            raise OSError(
                f"Can't capture color image with expected height and width ({self.height} x {self.width}). ({h} x {w}) returned instead."
            )

        if self.rotation is not None:
            color_image = cv2.rotate(color_image, self.rotation)

        # log the number of seconds it took to read the image
        self.logs["delta_timestamp_s"] = time.perf_counter() - start_time

        # log the utc time at which the image was received
        self.logs["timestamp_utc"] = capture_timestamp_utc()

        if self.use_depth:
            depth_frame = frame.get_depth_frame()
            if not depth_frame:
                raise OSError(f"Can't capture depth image from IntelRealSenseCamera({self.serial_number}).")

            depth_map = np.asanyarray(depth_frame.get_data())

            h, w = depth_map.shape
            if h != self.height or w != self.width:
                raise OSError(
                    f"Can't capture depth map with expected height and width ({self.height} x {self.width}). ({h} x {w}) returned instead."
                )

            if self.rotation is not None:
                depth_map = cv2.rotate(depth_map, self.rotation)

            return color_image, depth_map
        else:
            return color_image

    def async_read(self):
        """Read the latest frame from the camera."""
        logging.info("=== Starting async_read ===")
        logging.info(f"Thread ID: {threading.get_ident()}")
        start_time = time.time()
        
        try:
            if not self.is_connected:
                logging.error("Camera is not connected")
                return None
                
            if self.thread is None or not self.thread.is_alive():
                logging.error("Camera thread is not running")
                return None
                
            # Wait for color image with timeout
            max_tries = 10  # 1 second timeout
            for i in range(max_tries):
                if self.color_image is not None:
                    break
                time.sleep(0.1)
                
            if self.color_image is None:
                logging.error("Timeout waiting for color image")
                return None
                
            # Return color image
            color_image = self.color_image.copy()
            logging.info(f"Color image shape: {color_image.shape}")
            
            end_time = time.time()
            logging.info(f"async_read took {end_time - start_time:.3f} seconds")
            
            return color_image
            
        except Exception as e:
            logging.error(f"Error in async_read: {e}")
            logging.error(traceback.format_exc())
            return None

    def disconnect(self):
        """Disconnect from the camera and stop the read loop."""
        if not self.is_connected:
            return
            
        logging.info(f"Disconnecting from camera {self.serial_number}...")
        
        try:
            # Set stop event
            self.stop_event.set()
            
            # Wait for thread to finish
            if self.thread is not None:
                self.thread.join(timeout=1.0)
                if self.thread.is_alive():
                    logging.warning("Camera thread did not stop gracefully")
                    
            # Reset state
            self.thread = None
            self.stop_event = None
            self.color_image = None
            self.depth_map = None
            self.is_connected = False
            
            logging.info("Camera disconnected successfully")
            
        except Exception as e:
            logging.error(f"Error disconnecting from camera: {e}")
            raise

    def __del__(self):
        if getattr(self, "is_connected", False):
            self.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Save a few frames using `IntelRealSenseCamera` for all cameras connected to the computer, or a selected subset."
    )
    parser.add_argument(
        "--serial-numbers",
        type=int,
        nargs="*",
        default=None,
        help="List of serial numbers used to instantiate the `IntelRealSenseCamera`. If not provided, find and use all available camera indices.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Set the number of frames recorded per seconds for all cameras. If not provided, use the default fps of each camera.",
    )
    parser.add_argument(
        "--width",
        type=str,
        default=640,
        help="Set the width for all cameras. If not provided, use the default width of each camera.",
    )
    parser.add_argument(
        "--height",
        type=str,
        default=480,
        help="Set the height for all cameras. If not provided, use the default height of each camera.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default="outputs/images_from_intelrealsense_cameras",
        help="Set directory to save a few frames for each camera.",
    )
    parser.add_argument(
        "--record-time-s",
        type=float,
        default=2.0,
        help="Set the number of seconds used to record the frames. By default, 2 seconds.",
    )
    args = parser.parse_args()
    save_images_from_cameras(**vars(args))
