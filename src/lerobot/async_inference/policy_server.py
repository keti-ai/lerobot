# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example:
```shell
python -m lerobot.async_inference.policy_server \
     --host=127.0.0.1 \
     --port=8080 \
     --fps=30 \
     --inference_latency=0.033 \
     --obs_queue_timeout=1
```
"""

import logging
import math
import pickle  # nosec
import threading
import time
from concurrent import futures
from dataclasses import asdict
from pprint import pformat
from queue import Empty, Queue
from typing import Any

import draccus
import grpc
import torch

from lerobot.configs.types import RTCAttentionSchedule
from lerobot.policies import get_policy_class, make_pre_post_processors
from lerobot.policies.rtc import ActionQueue, LatencyTracker, RTCConfig, reanchor_relative_rtc_prefix
from lerobot.processor import NormalizerProcessorStep, PolicyProcessorPipeline, RelativeActionsProcessorStep
from lerobot.transport import (
    services_pb2,  # type: ignore
    services_pb2_grpc,  # type: ignore
)
from lerobot.transport.utils import receive_bytes_in_chunks
from lerobot.types import PolicyAction
from lerobot.utils.constants import OBS_STATE

from .configs import PolicyServerConfig
from .constants import SUPPORTED_POLICIES
from .helpers import (
    FPSTracker,
    Observation,
    RemotePolicyConfig,
    TimedAction,
    TimedObservation,
    get_logger,
    observations_similar,
    raw_observation_to_observation,
)

_ROBOT_FOLDING_RTC_EXECUTION_HORIZON = 10
_ROBOT_FOLDING_RTC_MAX_GUIDANCE_WEIGHT = 10.0
_ROBOT_FOLDING_RTC_PREFIX_ATTENTION_SCHEDULE = RTCAttentionSchedule.EXP


class PolicyServer(services_pb2_grpc.AsyncInferenceServicer):
    prefix = "policy_server"
    logger = get_logger(prefix)

    def __init__(self, config: PolicyServerConfig):
        self.config = config
        self.shutdown_event = threading.Event()

        # FPS measurement
        self.fps_tracker = FPSTracker(target_fps=config.fps)

        self.observation_queue = Queue(maxsize=1)

        self._predicted_timesteps_lock = threading.Lock()
        self._predicted_timesteps = set()
        self._observation_enqueue_times_lock = threading.Lock()
        self._observation_enqueue_times: dict[int, float] = {}

        self.last_processed_obs = None

        # Attributes will be set by SendPolicyInstructions
        self.device = None
        self.policy_type = None
        self.lerobot_features = None
        self.actions_per_chunk = None
        self.policy = None
        self.preprocessor: PolicyProcessorPipeline[dict[str, Any], dict[str, Any]] | None = None
        self.postprocessor: PolicyProcessorPipeline[PolicyAction, PolicyAction] | None = None

        self._action_queue: ActionQueue | None = None
        self._latency_tracker = LatencyTracker()
        self._relative_step: RelativeActionsProcessorStep | None = None
        self._normalizer_step: NormalizerProcessorStep | None = None
        self._action_index_before_inference: int | None = None

    @property
    def running(self):
        return not self.shutdown_event.is_set()

    @property
    def policy_image_features(self):
        return self.policy.config.image_features

    def _reset_server(self) -> None:
        """Flushes server state when new client connects."""
        # only running inference on the latest observation received by the server
        self.shutdown_event.set()
        self.observation_queue = Queue(maxsize=1)
        self._reset_rtc_state()

        with self._predicted_timesteps_lock:
            self._predicted_timesteps = set()
        with self._observation_enqueue_times_lock:
            self._observation_enqueue_times = {}

    def _reset_rtc_state(self) -> None:
        """Clear RTC leftovers and latency state without changing the loaded policy."""
        if self._action_queue is not None:
            self._action_queue.clear()
        self._latency_tracker.reset()
        self._action_index_before_inference = None

    def _rtc_config(self) -> RTCConfig | None:
        policy_config = getattr(self.policy, "config", None)
        return getattr(policy_config, "rtc_config", None)

    def _rtc_enabled(self) -> bool:
        rtc_config = self._rtc_config()
        return bool(rtc_config is not None and rtc_config.enabled)

    def _latency_to_steps(self, latency_s: float | None) -> int:
        if not latency_s:
            return 0
        return max(0, math.ceil(latency_s / self.config.environment_dt))

    @staticmethod
    def _format_ms(duration_s: float | None) -> str:
        if duration_s is None:
            return "nan"
        return f"{duration_s * 1000:.2f}"

    def _configure_rtc_policy(self) -> None:
        """Inject and initialize policy-side RTC when the loaded policy supports it."""
        policy_config = getattr(self.policy, "config", None)
        if policy_config is None or not hasattr(policy_config, "rtc_config"):
            self.logger.info(f"RTC unavailable for policy type {self.policy_type}; using non-RTC inference")
            return

        if policy_config.rtc_config is None:
            if self.policy_type != "pi05":
                self.logger.info(
                    f"RTC config absent for policy type {self.policy_type}; using non-RTC inference"
                )
                return

            policy_config.rtc_config = RTCConfig(
                enabled=True,
                execution_horizon=_ROBOT_FOLDING_RTC_EXECUTION_HORIZON,
                max_guidance_weight=_ROBOT_FOLDING_RTC_MAX_GUIDANCE_WEIGHT,
                prefix_attention_schedule=_ROBOT_FOLDING_RTC_PREFIX_ATTENTION_SCHEDULE,
            )
            self.logger.info(
                "Injected robot-folding RTCConfig: enabled=True | "
                f"execution_horizon={policy_config.rtc_config.execution_horizon} | "
                f"max_guidance_weight={policy_config.rtc_config.max_guidance_weight} | "
                f"prefix_attention_schedule={policy_config.rtc_config.prefix_attention_schedule}"
            )
        elif policy_config.rtc_config.enabled:
            self.logger.info(
                "Using policy-provided RTCConfig: "
                f"execution_horizon={policy_config.rtc_config.execution_horizon} | "
                f"max_guidance_weight={policy_config.rtc_config.max_guidance_weight} | "
                f"prefix_attention_schedule={policy_config.rtc_config.prefix_attention_schedule}"
            )
        else:
            self.logger.info("Policy RTCConfig is present but disabled; using non-RTC inference")

        if not self._rtc_enabled():
            return

        init_rtc_processor = getattr(self.policy, "init_rtc_processor", None)
        if not callable(init_rtc_processor):
            self.logger.warning("RTC is enabled but policy has no init_rtc_processor(); disabling RTC path")
            policy_config.rtc_config.enabled = False
            return

        init_rtc_processor()
        model_rtc_processor = getattr(getattr(self.policy, "model", None), "rtc_processor", None)
        if getattr(self.policy, "rtc_processor", None) is None or model_rtc_processor is None:
            self.logger.warning("RTC processor was not fully initialized on policy/model")
        else:
            self.logger.info("RTC processor initialized on policy and model")

    def _configure_rtc_processors(self) -> None:
        """Find processor steps needed to re-anchor relative RTC leftovers."""
        self._action_queue = None
        self._relative_step = None
        self._normalizer_step = None
        self._reset_rtc_state()

        if not self._rtc_enabled():
            return

        rtc_config = self._rtc_config()
        self._action_queue = ActionQueue(rtc_config)

        self._relative_step = next(
            (
                step
                for step in self.preprocessor.steps
                if isinstance(step, RelativeActionsProcessorStep) and step.enabled
            ),
            None,
        )
        self._normalizer_step = next(
            (step for step in self.preprocessor.steps if isinstance(step, NormalizerProcessorStep)),
            None,
        )

        if self._relative_step is not None:
            if self._relative_step.action_names is None:
                action_feature_names = getattr(self.policy.config, "action_feature_names", None)
                if action_feature_names:
                    self._relative_step.action_names = list(action_feature_names)
            self.logger.info("RTC relative-action prefix re-anchoring enabled")
        else:
            self.logger.info("RTC enabled without relative-action re-anchoring")

    def _synchronize_policy_device(self) -> None:
        if self.device is not None and str(self.device).startswith("cuda") and torch.cuda.is_available():
            torch.cuda.synchronize()

    def _make_warmup_observation(self) -> dict[str, Any]:
        """Build a synthetic observation from the loaded policy schema."""
        input_features = getattr(self.policy.config, "input_features", {}) or {}
        warmup_observation: dict[str, Any] = {"task": "policy server warmup"}

        for feature_name, feature in input_features.items():
            if feature_name in warmup_observation:
                continue
            warmup_observation[feature_name] = torch.zeros(tuple(feature.shape), dtype=torch.float32)

        if OBS_STATE not in warmup_observation:
            state_feature = getattr(self.policy.config, "robot_state_feature", None)
            if state_feature is not None:
                warmup_observation[OBS_STATE] = torch.zeros(tuple(state_feature.shape), dtype=torch.float32)

        return warmup_observation

    def _make_warmup_rtc_prefix(self) -> torch.Tensor | None:
        rtc_config = self._rtc_config()
        action_feature = getattr(self.policy.config, "action_feature", None)
        if rtc_config is None or action_feature is None:
            return None

        action_dim = action_feature.shape[0]
        prev_actions_absolute = torch.zeros(
            rtc_config.execution_horizon,
            action_dim,
            dtype=torch.float32,
            device=torch.device(self.device),
        )

        if self._relative_step is None:
            return prev_actions_absolute

        current_state = self._relative_step.get_cached_state()
        if current_state is None:
            return prev_actions_absolute

        return reanchor_relative_rtc_prefix(
            prev_actions_absolute=prev_actions_absolute,
            current_state=current_state,
            relative_step=self._relative_step,
            normalizer_step=self._normalizer_step,
            policy_device=torch.device(self.device),
        )

    def _warmup_policy_autograd(self) -> None:
        """Run discard-only forwards to pay CUDA/autograd lazy-init before the first client chunk."""
        if self.policy is None or self.preprocessor is None:
            return

        try:
            warmup_observation = self._make_warmup_observation()

            start_preprocess = time.perf_counter()
            preprocessed_observation = self.preprocessor(warmup_observation)
            self._synchronize_policy_device()
            preprocess_time = time.perf_counter() - start_preprocess

            start_no_prefix = time.perf_counter()
            _ = self.policy.predict_action_chunk(preprocessed_observation)
            self._synchronize_policy_device()
            no_prefix_time = time.perf_counter() - start_no_prefix

            guided_rtc_time = None
            if self._rtc_enabled():
                prev_chunk_left_over = self._make_warmup_rtc_prefix()
                if prev_chunk_left_over is not None:
                    rtc_config = self._rtc_config()
                    start_guided = time.perf_counter()
                    _ = self.policy.predict_action_chunk(
                        preprocessed_observation,
                        prev_chunk_left_over=prev_chunk_left_over,
                        inference_delay=0,
                        execution_horizon=rtc_config.execution_horizon,
                    )
                    self._synchronize_policy_device()
                    guided_rtc_time = time.perf_counter() - start_guided

            self._reset_rtc_state()

            if guided_rtc_time is None:
                self.logger.info(
                    "Policy warmup: preprocess %.2fms, no-prefix %.2fms, guided RTC skipped",
                    preprocess_time * 1000,
                    no_prefix_time * 1000,
                )
            else:
                self.logger.info(
                    "Policy warmup: preprocess %.2fms, no-prefix %.2fms, guided RTC %.2fms",
                    preprocess_time * 1000,
                    no_prefix_time * 1000,
                    guided_rtc_time * 1000,
                )
        except Exception:
            self._reset_rtc_state()
            self.logger.exception("Policy warmup failed; continuing without warmup")

    def Ready(self, request, context):  # noqa: N802
        client_id = context.peer()
        self.logger.info(f"Client {client_id} connected and ready")
        self._reset_server()
        self.shutdown_event.clear()

        return services_pb2.Empty()

    def SendPolicyInstructions(self, request, context):  # noqa: N802
        """Receive policy instructions from the robot client"""

        if not self.running:
            self.logger.warning("Server is not running. Ignoring policy instructions.")
            return services_pb2.Empty()

        client_id = context.peer()

        policy_specs = pickle.loads(request.data)  # nosec

        if not isinstance(policy_specs, RemotePolicyConfig):
            raise TypeError(f"Policy specs must be a RemotePolicyConfig. Got {type(policy_specs)}")

        if policy_specs.policy_type not in SUPPORTED_POLICIES:
            raise ValueError(
                f"Policy type {policy_specs.policy_type} not supported. "
                f"Supported policies: {SUPPORTED_POLICIES}"
            )

        self.logger.info(
            f"Receiving policy instructions from {client_id} | "
            f"Policy type: {policy_specs.policy_type} | "
            f"Pretrained name or path: {policy_specs.pretrained_name_or_path} | "
            f"Actions per chunk: {policy_specs.actions_per_chunk} | "
            f"Device: {policy_specs.device}"
        )

        self.device = policy_specs.device
        self.policy_type = policy_specs.policy_type  # act, pi0, etc.
        self.lerobot_features = policy_specs.lerobot_features
        self.actions_per_chunk = policy_specs.actions_per_chunk

        policy_class = get_policy_class(self.policy_type)

        start = time.perf_counter()
        self.policy = policy_class.from_pretrained(policy_specs.pretrained_name_or_path)
        self.policy.to(self.device)
        self._configure_rtc_policy()

        # Load preprocessor and postprocessor, overriding device to match requested device
        device_override = {"device": self.device}
        self.preprocessor, self.postprocessor = make_pre_post_processors(
            self.policy.config,
            pretrained_path=policy_specs.pretrained_name_or_path,
            preprocessor_overrides={
                "device_processor": device_override,
                "rename_observations_processor": {"rename_map": policy_specs.rename_map},
            },
            postprocessor_overrides={"device_processor": device_override},
        )
        self._configure_rtc_processors()
        self._warmup_policy_autograd()

        end = time.perf_counter()

        self.logger.info(f"Time taken to put policy on {self.device}: {end - start:.4f} seconds")

        return services_pb2.Empty()

    def SendObservations(self, request_iterator, context):  # noqa: N802
        """Receive observations from the robot client"""
        client_id = context.peer()
        self.logger.debug(f"Receiving observations from {client_id}")

        receive_time = time.time()  # comparing timestamps so need time.time()
        start_deserialize = time.perf_counter()
        received_bytes = receive_bytes_in_chunks(
            request_iterator, None, self.shutdown_event, self.logger
        )  # blocking call while looping over request_iterator
        timed_observation = pickle.loads(received_bytes)  # nosec
        deserialize_time = time.perf_counter() - start_deserialize

        self.logger.debug(f"Received observation #{timed_observation.get_timestep()}")

        obs_timestep = timed_observation.get_timestep()
        obs_timestamp = timed_observation.get_timestamp()

        # Calculate FPS metrics
        fps_metrics = self.fps_tracker.calculate_fps_metrics(obs_timestamp)

        self.logger.debug(
            f"Received observation #{obs_timestep} | "
            f"Avg FPS: {fps_metrics['avg_fps']:.2f} | "  # fps at which observations are received from client
            f"Target: {fps_metrics['target_fps']:.2f} | "
            f"One-way latency: {(receive_time - obs_timestamp) * 1000:.2f}ms"
        )

        self.logger.debug(
            f"Server timestamp: {receive_time:.6f} | "
            f"Client timestamp: {obs_timestamp:.6f} | "
            f"Deserialization time: {deserialize_time:.6f}s"
        )

        start_enqueue = time.perf_counter()
        enqueued = self._enqueue_observation(
            timed_observation  # wrapping a RawObservation
        )
        enqueue_time = time.perf_counter() - start_enqueue
        if not enqueued:
            self.logger.debug(f"Observation #{obs_timestep} has been filtered out")

        self.logger.info(
            "K13 SendObservations timing | "
            f"obs={obs_timestep} | "
            f"receive_deserialize_ms={deserialize_time * 1000:.2f} | "
            f"enqueue_ms={enqueue_time * 1000:.2f} | "
            f"enqueued={enqueued} | "
            f"queue_size={self.observation_queue.qsize()} | "
            f"one_way_ms={(receive_time - obs_timestamp) * 1000:.2f}"
        )

        return services_pb2.Empty()

    def GetActions(self, request, context):  # noqa: N802
        """Returns actions to the robot client. Actions are sent as a single
        chunk, containing multiple actions."""
        client_id = context.peer()
        self.logger.debug(f"Client {client_id} connected for action streaming")

        # Generate action based on the most recent observation and its timestep
        try:
            getactions_starts = time.perf_counter()
            obs = self.observation_queue.get(timeout=self.config.obs_queue_timeout)
            obs_dequeued_at = time.perf_counter()
            get_wait_time = obs_dequeued_at - getactions_starts
            with self._observation_enqueue_times_lock:
                obs_enqueue_time = self._observation_enqueue_times.pop(id(obs), None)
            queue_age_time = None
            if obs_enqueue_time is not None:
                queue_age_time = obs_dequeued_at - obs_enqueue_time

            self.logger.info(
                f"Running inference for observation #{obs.get_timestep()} (must_go: {obs.must_go})"
            )

            with self._predicted_timesteps_lock:
                self._predicted_timesteps.add(obs.get_timestep())

            start_time = time.perf_counter()
            action_chunk = self._predict_action_chunk(obs)
            inference_time = time.perf_counter() - start_time

            start_time = time.perf_counter()
            actions_bytes = pickle.dumps(action_chunk)  # nosec
            serialize_time = time.perf_counter() - start_time

            # Create and return the action chunk
            start_response_message = time.perf_counter()
            actions = services_pb2.Actions(data=actions_bytes)
            response_message_time = time.perf_counter() - start_response_message
            response_ready_at = time.perf_counter()
            sleep_time = max(
                0,
                self.config.inference_latency - max(0, response_ready_at - getactions_starts),
            )

            self.logger.info(
                f"Action chunk #{obs.get_timestep()} generated | "
                f"Total time: {(inference_time + serialize_time) * 1000:.2f}ms"
            )
            self.logger.info(
                "K13 GetActions timing | "
                f"obs={obs.get_timestep()} | "
                f"get_wait_ms={get_wait_time * 1000:.2f} | "
                f"queue_age_ms={self._format_ms(queue_age_time)} | "
                f"predict_ms={inference_time * 1000:.2f} | "
                f"serialize_ms={serialize_time * 1000:.2f} | "
                f"response_message_ms={response_message_time * 1000:.2f} | "
                f"sleep_ms={sleep_time * 1000:.2f} | "
                f"handler_ready_ms={(response_ready_at - getactions_starts) * 1000:.2f} | "
                "grpc_send_ms=unmeasured_after_return"
            )

            self.logger.debug(
                f"Action chunk #{obs.get_timestep()} generated | "
                f"Inference time: {inference_time:.2f}s |"
                f"Serialize time: {serialize_time:.2f}s |"
                f"Total time: {inference_time + serialize_time:.2f}s"
            )

            time.sleep(sleep_time)  # sleep controls inference latency

            return actions

        except Empty:  # no observation added to queue in obs_queue_timeout
            return services_pb2.Empty()

        except Exception as e:
            self.logger.error(f"Error in StreamActions: {e}")

            return services_pb2.Empty()

    def _obs_sanity_checks(self, obs: TimedObservation, previous_obs: TimedObservation) -> bool:
        """Check if the observation is valid to be processed by the policy"""
        with self._predicted_timesteps_lock:
            predicted_timesteps = self._predicted_timesteps

        if obs.get_timestep() in predicted_timesteps:
            self.logger.debug(f"Skipping observation #{obs.get_timestep()} - Timestep predicted already!")
            return False

        elif observations_similar(obs, previous_obs, lerobot_features=self.lerobot_features):
            self.logger.debug(
                f"Skipping observation #{obs.get_timestep()} - Observation too similar to last obs predicted!"
            )
            return False

        else:
            return True

    def _enqueue_observation(self, obs: TimedObservation) -> bool:
        """Enqueue an observation if it must go through processing, otherwise skip it.
        Observations not in queue are never run through the policy network"""

        if (
            obs.must_go
            or self.last_processed_obs is None
            or self._obs_sanity_checks(obs, self.last_processed_obs)
        ):
            last_obs = self.last_processed_obs.get_timestep() if self.last_processed_obs else "None"
            self.logger.debug(
                f"Enqueuing observation. Must go: {obs.must_go} | Last processed obs: {last_obs}"
            )

            # If queue is full, get the old observation to make room
            if self.observation_queue.full():
                # pops from queue
                removed_obs = self.observation_queue.get_nowait()
                with self._observation_enqueue_times_lock:
                    self._observation_enqueue_times.pop(id(removed_obs), None)
                self.logger.debug("Observation queue was full, removed oldest observation")

            # Now put the new observation (never blocks as queue is non-full here)
            with self._observation_enqueue_times_lock:
                self._observation_enqueue_times[id(obs)] = time.perf_counter()
            self.observation_queue.put(obs)
            return True

        return False

    def _time_action_chunk(self, t_0: float, action_chunk: list[torch.Tensor], i_0: int) -> list[TimedAction]:
        """Turn a chunk of actions into a list of TimedAction instances,
        with the first action corresponding to t_0 and the rest corresponding to
        t_0 + i*environment_dt for i in range(len(action_chunk))
        """
        return [
            TimedAction(timestamp=t_0 + i * self.config.environment_dt, timestep=i_0 + i, action=action)
            for i, action in enumerate(action_chunk)
        ]

    def _get_action_chunk(self, observation: dict[str, torch.Tensor]) -> torch.Tensor:
        """Get an action chunk from the policy. The chunk contains only"""
        self._action_index_before_inference = None

        if self._rtc_enabled() and self._action_queue is not None:
            self._action_index_before_inference = self._action_queue.get_action_index()
            prev_left_over = self._action_queue.get_left_over()
            inference_delay = self._latency_to_steps(self._latency_tracker.max())

            if prev_left_over is not None and self._relative_step is not None:
                current_state = self._relative_step.get_cached_state()
                prev_actions_absolute = self._action_queue.get_processed_left_over()
                if current_state is not None and prev_actions_absolute is not None:
                    prev_left_over = reanchor_relative_rtc_prefix(
                        prev_actions_absolute=prev_actions_absolute,
                        current_state=current_state,
                        relative_step=self._relative_step,
                        normalizer_step=self._normalizer_step,
                        policy_device=torch.device(self.device),
                    )
                    self.logger.debug(
                        "RTC re-anchored previous relative leftover prefix: "
                        f"shape={tuple(prev_left_over.shape)}"
                    )

            rtc_config = self._rtc_config()
            chunk = self.policy.predict_action_chunk(
                observation,
                prev_chunk_left_over=prev_left_over,
                inference_delay=inference_delay,
                execution_horizon=rtc_config.execution_horizon,
            )
            self.logger.debug(
                "RTC predict_action_chunk kwargs: "
                f"prev_left_over={None if prev_left_over is None else tuple(prev_left_over.shape)} | "
                f"inference_delay={inference_delay} | "
                f"execution_horizon={rtc_config.execution_horizon}"
            )
        else:
            chunk = self.policy.predict_action_chunk(observation)

        if chunk.ndim != 3:
            chunk = chunk.unsqueeze(0)  # adding batch dimension, now shape is (B, chunk_size, action_dim)

        return chunk[:, : self.actions_per_chunk, :]

    def _merge_rtc_action_chunk(
        self, original_actions: torch.Tensor, processed_actions: torch.Tensor, latency_s: float
    ) -> None:
        if not self._rtc_enabled() or self._action_queue is None:
            return

        real_delay = self._latency_to_steps(latency_s)
        self._latency_tracker.add(latency_s)
        self._action_queue.merge(
            original_actions,
            processed_actions,
            real_delay,
            self._action_index_before_inference,
        )
        self.logger.info(
            "RTC action queue merged | "
            f"latency={latency_s:.4f}s | "
            f"real_delay={real_delay} | "
            f"remaining_actions={self._action_queue.qsize()}"
        )

    def _predict_action_chunk(self, observation_t: TimedObservation) -> list[TimedAction]:
        """Predict an action chunk based on an observation.

        Pipeline:
        1. Convert raw observation to LeRobot format
        2. Apply preprocessor (tokenization, normalization, batching, device placement)
        3. Run policy inference to get action chunk
        4. Apply postprocessor (unnormalization, device movement)
        5. Convert to TimedAction list
        """
        """1. Prepare observation"""
        start_prepare = time.perf_counter()
        observation: Observation = raw_observation_to_observation(
            observation_t.get_observation(),
            self.lerobot_features,
            self.policy_image_features,
        )
        prepare_time = time.perf_counter() - start_prepare

        """2. Apply preprocessor"""
        start_preprocess = time.perf_counter()
        observation = self.preprocessor(observation)
        self.last_processed_obs: TimedObservation = observation_t
        preprocessing_time = time.perf_counter() - start_preprocess

        """3. Get action chunk"""
        start_inference = time.perf_counter()
        action_tensor = self._get_action_chunk(observation)
        inference_time = time.perf_counter() - start_inference
        start_original_clone = time.perf_counter()
        original_action_tensor = action_tensor.squeeze(0).detach().clone()
        original_clone_time = time.perf_counter() - start_original_clone
        self.logger.info(
            f"Preprocessing and inference took {inference_time:.4f}s, action shape: {action_tensor.shape}"
        )

        """4. Apply postprocessor"""
        # Apply postprocessor (handles unnormalization and device movement)
        # Postprocessor expects (B, action_dim) per action, but we have (B, chunk_size, action_dim)
        # So we process each action in the chunk individually
        start_postprocess = time.perf_counter()
        _, chunk_size, _ = action_tensor.shape

        # Process each action in the chunk
        processed_actions = []
        for i in range(chunk_size):
            # Extract action at timestep i: (B, action_dim)
            single_action = action_tensor[:, i, :]
            processed_action = self.postprocessor(single_action)
            processed_actions.append(processed_action)

        # Stack back to (B, chunk_size, action_dim), then remove batch dim
        action_tensor = torch.stack(processed_actions, dim=1).squeeze(0)
        self.logger.debug(f"Postprocessed action shape: {action_tensor.shape}")

        postprocess_stops = time.perf_counter()
        postprocessing_time = postprocess_stops - start_postprocess
        total_latency = postprocess_stops - start_prepare
        start_rtc_merge = time.perf_counter()
        self._merge_rtc_action_chunk(original_action_tensor, action_tensor.detach().clone(), total_latency)
        rtc_merge_time = time.perf_counter() - start_rtc_merge

        start_detach_cpu = time.perf_counter()
        action_tensor = action_tensor.detach().cpu()
        detach_cpu_time = time.perf_counter() - start_detach_cpu

        """5. Convert to TimedAction list"""
        start_time_actions = time.perf_counter()
        action_chunk = self._time_action_chunk(
            observation_t.get_timestamp(), list(action_tensor), observation_t.get_timestep()
        )
        time_actions_time = time.perf_counter() - start_time_actions
        predict_total_time = time.perf_counter() - start_prepare

        self.logger.info(
            f"Observation {observation_t.get_timestep()} | "
            f"Total time: {1000 * (postprocess_stops - start_prepare):.2f}ms"
        )
        self.logger.info(
            "K13 Predict timing | "
            f"obs={observation_t.get_timestep()} | "
            f"prepare_ms={prepare_time * 1000:.2f} | "
            f"preprocess_ms={preprocessing_time * 1000:.2f} | "
            f"inference_ms={inference_time * 1000:.2f} | "
            f"original_clone_ms={original_clone_time * 1000:.2f} | "
            f"postprocess_loop_ms={postprocessing_time * 1000:.2f} | "
            f"postprocess_per_action_ms={(postprocessing_time / max(chunk_size, 1)) * 1000:.2f} | "
            f"rtc_merge_ms={rtc_merge_time * 1000:.2f} | "
            f"detach_cpu_ms={detach_cpu_time * 1000:.2f} | "
            f"time_actions_ms={time_actions_time * 1000:.2f} | "
            f"pipeline_core_ms={(postprocess_stops - start_prepare) * 1000:.2f} | "
            f"predict_total_ms={predict_total_time * 1000:.2f}"
        )

        self.logger.debug(
            f"Observation {observation_t.get_timestep()} | "
            f"Prepare time: {1000 * prepare_time:.2f}ms | "
            f"Preprocessing time: {1000 * preprocessing_time:.2f}ms | "
            f"Inference time: {1000 * inference_time:.2f}ms | "
            f"Postprocessing time: {1000 * postprocessing_time:.2f}ms | "
            f"Total time: {1000 * (postprocess_stops - start_prepare):.2f}ms"
        )

        return action_chunk

    def stop(self):
        """Stop the server"""
        self._reset_server()
        self.logger.info("Server stopping...")


@draccus.wrap()
def serve(cfg: PolicyServerConfig):
    """Start the PolicyServer with the given configuration.

    Args:
        config: PolicyServerConfig instance. If None, uses default configuration.
    """
    logging.info(pformat(asdict(cfg)))

    # Create the server instance first
    policy_server = PolicyServer(cfg)

    # Setup and start gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    services_pb2_grpc.add_AsyncInferenceServicer_to_server(policy_server, server)
    server.add_insecure_port(f"{cfg.host}:{cfg.port}")

    policy_server.logger.info(f"PolicyServer started on {cfg.host}:{cfg.port}")
    server.start()

    server.wait_for_termination()

    policy_server.logger.info("Server terminated")


if __name__ == "__main__":
    serve()
