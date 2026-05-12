# Stage 33 A6000 Remote Serving Bridge Plan

Date: 2026-05-12

## Purpose

The baseline deployment architecture is not "run the PI0.5 model on
syhlabtop." The baseline architecture is:

```text
syhlabtop: robot/camera IO and final safety gate
A6000: PI0.5 model weights and inference
```

However, the current LeRobot rollout code does not provide an audited
split-host inference transport. RTC inference is an in-process background
thread, not a remote A6000 model server. Therefore live A6000 serving must be a
separate stage after snapshot-based no-send review.

## Current Allowed Path

Stage 32 is snapshot-based:

1. syhlabtop captures a read-only observation snapshot:
   - `state_16.csv`
   - `left_wrist.png`
   - `right_wrist.png`
   - `base.png`
   - `metadata.json`
2. syhlabtop transfers that snapshot bundle to A6000.
3. A6000 runs no-send inference/review with the final checkpoint.
4. No action is sent to the robot.

This path uses the A6000 model without requiring syhlabtop to load
`model.safetensors`.

## Future Live Serving Path

Stage 33 should create and audit a no-motion remote inference bridge.

Required split:

- A6000 server:
  - loads final PI0.5 checkpoint
  - owns model/device/preprocessor/postprocessor
  - receives observation packets
  - returns action proposal packets
  - never talks to robot hardware
- syhlabtop client:
  - owns camera/state acquisition
  - sends observation packets to A6000
  - receives action proposal packets
  - logs deltas
  - does not call `robot.send_action()` during Stage 33

## Protocol Requirements

Observation packet from syhlabtop to A6000:

```json
{
  "schema": "openarm_folding_observation_v1",
  "obs_id": "snapshot_or_frame_id",
  "timestamp": "ISO-8601",
  "robot_type": "openarms_follower",
  "task": "Fold the T-shirt properly",
  "state_names": [
    "right_joint_1.pos",
    "right_joint_2.pos",
    "right_joint_3.pos",
    "right_joint_4.pos",
    "right_joint_5.pos",
    "right_joint_6.pos",
    "right_joint_7.pos",
    "right_gripper.pos",
    "left_joint_1.pos",
    "left_joint_2.pos",
    "left_joint_3.pos",
    "left_joint_4.pos",
    "left_joint_5.pos",
    "left_joint_6.pos",
    "left_joint_7.pos",
    "left_gripper.pos"
  ],
  "state": ["16 float values"],
  "images": {
    "left_wrist": "encoded image bytes or file reference",
    "right_wrist": "encoded image bytes or file reference",
    "base": "encoded image bytes or file reference"
  },
  "send_action": false
}
```

Action proposal packet from A6000 to syhlabtop:

```json
{
  "schema": "openarm_folding_action_proposal_v1",
  "obs_id": "same as request",
  "model_id": "pi05_openarm_relstats_full_004000",
  "action_names": ["same 16 names as state"],
  "predicted_abs_action": ["16 float values"],
  "delta_deg": ["16 float values"],
  "max_abs_arm_delta_deg": "float",
  "watched_deltas": {
    "right_joint_4.pos": "float",
    "left_joint_4.pos": "float",
    "right_joint_7.pos": "float"
  },
  "send_allowed": false
}
```

During Stage 33, `send_allowed` must always be `false`.

## Acceptance For Stage 33 No-Motion Bridge

Before any guarded first actuator write can be discussed, the bridge must pass:

- syhlabtop can send one observation packet to A6000.
- A6000 returns one action proposal packet.
- `obs_id` round-trips exactly.
- state/action names match the 16D folding order exactly.
- camera keys are not swapped.
- A6000 proposal has no 60-70 degree abnormal arm delta.
- syhlabtop logs the proposal and refuses to send it.
- No robot write, torque enable, zeroing, rollout, replay-to-robot, or
  `robot.send_action()` occurs.

## Implementation Guardrails

Do not use `lerobot-rollout` for Stage 33 until the remote bridge is audited.

Do not modify robot code paths to call the remote server inside a control loop
until a single-frame no-motion bridge has passed.

The first implementation should be a standalone no-send server/client pair:

- A6000: `serve_snapshot_policy.py` or equivalent
- syhlabtop: `send_snapshot_for_action_proposal.py` or equivalent

The client must not import or instantiate a robot write path.

## Stage Order

1. Stage 32: snapshot bundle from syhlabtop to A6000 offline review.
2. Stage 33: single-frame remote serving bridge, no-send.
3. Stage 34: repeated no-send remote serving latency/drift check.
4. Stage 35: guarded first actuator write, only after explicit human approval.

Robot motion remains blocked until Stage 35.
