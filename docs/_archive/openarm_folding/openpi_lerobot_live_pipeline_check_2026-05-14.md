# OpenPI vs LeRobot Live Pipeline Check

Date: 2026-05-14

## Result

Proceed with the LeRobot live guarded path for the retrained folding checkpoint.

OpenPI and LeRobot both have the same high-level real-robot inference pattern:

1. Robot-side client continuously reads current cameras and proprioception.
2. Policy server returns an action chunk.
3. Robot-side client consumes actions while refreshing observations and requesting the next chunk.

LeRobot contains official rollout/RTC infrastructure, but its hardware execution path calls
`robot.connect()` and `robot.send_action()`. For this OpenArm deployment that is intentionally
not used, because the audited syhlabtop path is direct `DamiaoMotorsBus.connect(handshake=False)`
plus guarded MIT batch commands.

## OpenPI Reference Contract

From `../openpi/src/openpi/policies/openarm_runtime_contract.py`:

- State/action order: left arm, left gripper, right arm, right gripper.
- Camera keys: `head`, `wrist_left`, `wrist_right`.
- Image runtime shape: CHW `(3, 224, 224)`.
- Grippers: normalized `[0, 1]`.
- Action chunk shape: `(16, 16)`.
- Action semantics: absolute.

This is the correct contract for an OpenPI checkpoint trained/exported against that runtime.

## Current LeRobot Folding Contract

The retrained LeRobot folding checkpoint and syhlabtop live harness use:

- State/action order: right arm, right gripper, left arm, left gripper.
- Camera keys: `left_wrist`, `right_wrist`, `base`.
- Action chunk shape: `[1, 30, 16]`.
- Joint/action units: degrees.
- Grippers: OpenArm degree range `[-65, 0]`.
- Runtime action semantics: absolute after postprocessor.
- Relative actions remain a training/processor detail. A6000 returns absolute targets.

Do not switch this session to the OpenPI left-first contract unless the checkpoint is also
changed to an OpenPI-contract checkpoint.

## LeRobot Integration Check

LeRobot has these relevant upstream pieces:

- `src/lerobot/rollout/inference/rtc.py`: RTC background inference and action queue.
- `src/lerobot/policies/rtc`: leftover chunk re-anchoring for relative-action policies.
- `src/lerobot/scripts/lerobot_rollout.py`: official deployment CLI.
- `src/lerobot/async_inference`: remote inference client/server.

Not used for actual OpenArm motion in this session:

- `lerobot-rollout` actual path, because it reaches `robot.send_action()`.
- `async_inference/robot_client.py`, because it creates and connects a robot then calls
  `robot.send_action()`.
- `OpenArmFollower.connect()`, because follower connect can enable torque as part of its
  normal hardware setup path.

Used in this session:

- A6000 live policy server on port `8766`.
- Syhlabtop live guarded client.
- Direct Damiao bus reads and MIT batch writes.
- Full 16D bimanual + gripper commands, with operator monitor-only safety.

## A6000 Live Server

Status at check time:

- Existing snapshot server remains on `8765`.
- Live server is running on `8766`.
- Model: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- `model_id`: `pi05:pretrained_model`
- `checkpoint_id`: `004000`
- `robot_config_id`: `openarms_follower:16d:3cam:v1`
- `action_normalization_id`: `processor_sha256:94f781979263ad3f6d85df772d790d3d6909e6379ee47aa8e38491056082c67f`
- `action_space_version`: `openarm_folding_abs_16d_deg_v1`
- `send_allowed`: `false`
- `motion_allowed`: `false`

Startup note: the live server must be launched with the same HF offline/cache environment as
the existing snapshot server:

```bash
HF_HOME=/mnt/nas/huggingface
HF_HUB_CACHE=/mnt/nas/huggingface/hub
TRANSFORMERS_OFFLINE=1
HF_HUB_OFFLINE=1
```

Without those variables, the processor tokenizer tries to access the gated Paligemma Hub repo
during startup.

## Start Decision

The repo has the necessary pipeline concepts, but the official LeRobot hardware runner is not
the correct actuator path for this audited OpenArm deployment. The current custom live setup is
the appropriate bridge: it keeps the OpenPI/LeRobot online chunked inference pattern while
preserving the syhlabtop audited actuator path.

Next action: generate a live rollout session envelope from `8766 /health`, get operator approval
for that envelope, then run `syhlabtop_live_guarded_rollout.py --execute`.
