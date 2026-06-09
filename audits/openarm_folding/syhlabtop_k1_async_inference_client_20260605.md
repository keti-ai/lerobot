# syhlabtop K1 async inference client

Executed: 2026-06-09 11:00-11:28 KST

## 입력

- Client host: `syhlabtop`
- Repo: `/home/syhlabtop/workspace/lerobot`
- Branch: `audit/openarm-folding-baseline`
- Starting commit: `dd906059 ops(a6000): K1 server — HF push α'' 030000 + policy_server gRPC bind 8081`
- Server: `10.252.205.103`
- Approved endpoint: `10.252.205.103:8081`
- Policy repo: `KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime`
- Task string used for dry-run: `Pick the banana, hand it over to the other arm, and place it at the target.`
- Operator: ready
- Power abort: ready

## 서버 reachability

`8080` was not used for K1 client because the a6000 K1 report records that `8080` is occupied by another user's `code-server`.
The approved policy server endpoint was `8081`.

```text
ping -c 2 10.252.205.103
=> OK, 0% packet loss

nc -zv 10.252.205.103 8081
=> Connection to 10.252.205.103 8081 port [tcp/tproxy] succeeded

gRPC readiness:
8080 => FutureTimeoutError
8081 => grpc 8081 ready
```

Server-side log pasted from a6000:

```text
INFO 2026-06-08 20:32:46 y_server.py:430 PolicyServer started on 0.0.0.0:8081
INFO 2026-06-09 11:16:59 y_server.py:110 Client ipv4:10.252.216.81:52072 connected and ready
INFO 2026-06-09 11:16:59 y_server.py:136 Receiving policy instructions from ipv4:10.252.216.81:52072 | Policy type: pi05 | Pretrained name or path: KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime | Actions per chunk: 30 | Device: cuda
INFO 2026-06-09 11:19:12 ing_pi05.py:599 Enabled gradient checkpointing for PI05Pytorch model
```

Interpretation: first policy setup on server took more than 90 seconds, so a raw `timeout 10` wrapper is not appropriate. The control window must be limited after `RobotClient.start()` returns.

## 로컬 setup

`uv sync --locked --extra all` failed on the `egl-probe==1.0.2` build path from the `hf-libero/robomimic` dependency. K1 client dependencies were installed with a narrower hardware/client set:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --locked \
  --extra async \
  --extra core-scripts \
  --extra openarms \
  --extra feetech \
  --extra intelrealsense
```

Import smoke:

```text
grpc ok
pyrealsense2 ok
```

## robot_client command validation

Direct file execution is not valid for this module:

```bash
uv run python src/lerobot/async_inference/robot_client.py --help
```

It fails with `ImportError: attempted relative import with no known parent package`.

Module execution works, but does not expose `bi_openarm_follower` unless the OpenArm robot module is imported first. The working command path used for validation was:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -c \
"from lerobot.robots import bi_openarm_follower, openarm_follower, so_follower, bi_so_follower, koch_follower, omx_follower; from lerobot.cameras.realsense import RealSenseCameraConfig; from lerobot.async_inference.robot_client import async_client; async_client()" \
--help
```

Confirmed K1-relevant args:

- `--robot.type`
- `--robot.cameras`
- `--task`
- `--server_address`
- `--policy_type`
- `--pretrained_name_or_path`
- `--policy_device`
- `--client_device`
- `--actions_per_chunk`
- `--fps`
- `--chunk_size_threshold`
- `--aggregate_fn_name`

## Hardware preflight

CAN was configured manually by the operator:

```bash
uv run lerobot-setup-can --mode=setup --interfaces=can0,can1
```

Post-setup state:

```text
can0 UP <NOARP,UP,LOWER_UP,ECHO>
can1 UP <NOARP,UP,LOWER_UP,ECHO>
```

RealSense enumerate:

```text
Intel RealSense D405  serial 230322273311  USB 3.2
Intel RealSense D435I serial 213622075840  USB 3.2
Intel RealSense D405  serial 315122270766  USB 3.2
```

## Dry-run attempts

### Attempt 1: raw process timeout

Log: `/tmp/k1_client_dryrun_20260609.log`

The process was interrupted during camera warmup before server RPC or motion.

Result:

```text
exit code: 137
RealSenseCamera(315122270766) connected
KeyboardInterrupt in camera_realsense.py during warmup
```

Conclusion: do not use shell `timeout 10` around the whole process because hardware connection and first server load can exceed 10 seconds. It can interrupt cleanup.

### Attempt 2: safe wrapper, int max_relative_target

Log: `/tmp/k1_client_dryrun_20260609_retry.log`

This wrapper connected the robot and cameras, sent policy instructions, and waited for server setup. Server response arrived after about 134 seconds.

Result:

```text
Control loop thread starting
Action receiving thread starting
TypeError: 5
```

Cause: the wrapper directly instantiated `OpenArmFollowerConfigBase(max_relative_target=5)` as an `int`. `ensure_safe_goal_position()` accepts `float | dict[str, float]`, so direct dataclass construction must use `5.0`. This was a wrapper issue, not a server or robot connection failure.

### Attempt 3: safe wrapper, float max_relative_target

Log: `/tmp/k1_client_dryrun_20260609_retry_float.log`

Actual command pattern:

```bash
timeout --signal=INT --kill-after=30s 240s \
  env UV_CACHE_DIR=/tmp/uv-cache HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 \
  uv run python - <<'PY'
# Python wrapper:
# - builds RobotClientConfig directly
# - uses BiOpenArmFollowerConfig
# - uses OpenArmFollowerConfigBase(..., max_relative_target=5.0)
# - server_address="10.252.205.103:8081"
# - policy_type="pi05"
# - pretrained_name_or_path="KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime"
# - policy_device="cuda"
# - client_device="cpu"
# - actions_per_chunk=30
# - fps=30
# - chunk_size_threshold=0.5
# - aggregate_fn_name="weighted_average"
# - starts receive_actions and control_loop only after client.start() returns
# - sleeps exactly 10 seconds for the control window
# - always calls client.stop() and joins threads
PY
```

Key log lines:

```text
INFO 2026-06-09 11:25:57 t_client.py:156 Sending policy instructions to policy server
INFO 2026-06-09 11:27:53 t_client.py:462 Control loop thread starting
INFO 2026-06-09 11:27:53 <stdin>:51 K1 control loop running for 10 seconds
INFO 2026-06-09 11:27:53 t_client.py:273 Action receiving thread starting
WARNING 2026-06-09 11:27:56 ts/utils.py:121 Relative goal position magnitude had to be clamped to be safe.
INFO 2026-06-09 11:28:03 <stdin>:53 K1 10-second dry-run window complete
INFO 2026-06-09 11:28:05 ealsense.py:644 RealSenseCamera(315122270766) disconnected.
INFO 2026-06-09 11:28:06 ealsense.py:644 RealSenseCamera(230322273311) disconnected.
INFO 2026-06-09 11:28:08 ealsense.py:644 RealSenseCamera(213622075840) disconnected.
INFO 2026-06-09 11:28:08 follower.py:346 openarm_bimanual_follower_left OpenArmFollower disconnected.
INFO 2026-06-09 11:28:08 follower.py:346 openarm_bimanual_follower_right OpenArmFollower disconnected.
INFO 2026-06-09 11:28:08 <stdin>:60 receiver_thread_alive_after_join=False
INFO 2026-06-09 11:28:08 <stdin>:63 control_thread_alive_after_join=False
INFO 2026-06-09 11:28:08 <stdin>:64 K1 float retry wrapper elapsed_seconds=141.958
```

Result:

- gRPC connect: PASS on `10.252.205.103:8081`
- Server-side policy setup: PASS, but first response took about 116 seconds in the final attempt and more than 130 seconds in the previous attempt
- syhlabtop robot connection: PASS
- syhlabtop camera connection: PASS
- Action receiving thread: PASS
- Control loop: PASS for 10 seconds
- Cleanup: PASS
- Safety clamp: observed repeatedly; `max_relative_target=5.0` was active
- Operator visual observation: not recorded in this terminal session

## K4 command template

Use the same safe wrapper pattern. Do not wrap the whole process with `timeout 60`; instead, start the client, wait for server setup, then run the control window for 60 seconds.

Trial allocation:

```text
banana: 7 trials
olive green cup: 7 trials
blue toothpaste: 6 trials
```

Template variables:

```bash
SERVER_ADDRESS=10.252.205.103:8081
POLICY_REPO=KETI-IRRC/pi05_openarm_handover_v0_clean_alpha2prime
ACTIONS_PER_CHUNK=30
FPS=30
CONTROL_SECONDS=60
```

Task strings:

```text
Pick the banana, hand it over to the other arm, and place it at the target.
Pick the olive green cup, hand it over to the other arm, and place it at the target.
Pick the blue toothpaste, hand it over to the other arm, and place it at the target.
```

Required wrapper details for K4:

- `server_address="10.252.205.103:8081"`
- `policy_device="cuda"`
- `client_device="cpu"`
- `actions_per_chunk=30`
- `fps=30`
- `chunk_size_threshold=0.5`
- `aggregate_fn_name="weighted_average"`
- `max_relative_target=5.0`, not integer `5`, if constructing configs directly in Python
- `warmup_s=3` for each RealSense camera
- outer failsafe >= 240 seconds for the first trial because server setup can be slow
- inner trial control window exactly 60 seconds

## Operator protocol for K4

1. Confirm operator and power abort before each trial.
2. Confirm workspace is clear and target object matches the task string.
3. Start wrapper and wait for `Control loop thread starting`.
4. Score only the 60-second control window.
5. Stop immediately on unsafe motion, USB camera loss, CAN error, or excessive clamp-driven motion.
6. Record each trial as `success`, `partial`, `fail`, or `abort`.
7. Store trial notes with object, trial index, result, failure reason, and any intervention.

## K4 readiness

K1 client-side gRPC and 10-second action execution are verified on `8081`.
K4 can proceed after the operator records a visual note for the K1 motion and confirms the same safety setup.
