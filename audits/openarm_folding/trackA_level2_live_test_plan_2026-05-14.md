# Track A Level2 Live Test Plan

## Current Status

```text
track_a_status: DEFERRED_UNTIL_TRACK_B_DONE
track_b_status: ACTIVE_ON_A6000_FULL_FOLDING_RETRAIN
a6000_gpu_use: ALL_FOUR_GPUS_EXPECTED
robot_motion_from_this_plan: NOT_AUTHORIZED_NOW
```

Do not execute the rollout commands in this file while Track B is using the
A6000 GPUs for `full_folding` training. This file is the ready-to-run Track A
template for after Track B finishes, A6000 serving is re-established, and a new
operator approval envelope is generated.

## Goal

Evaluate whether the current corrected level2 checkpoint produces useful folding motion on the real OpenArm setup before switching to the parallel `full_folding` retrain candidate.

This track stays on syhlabtop. After Track B, A6000 only serves inference for
the selected checkpoint.

## Current Model Server

This was the last known corrected level2 live server. Re-check it after Track B
finishes before generating any approval envelope.

- Live server: `http://10.252.205.103:8766`
- Health endpoint: `http://10.252.205.103:8766/health`
- Model path: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- Checkpoint: `004000`
- Action space: `openarm_folding_abs_16d_deg_v1`
- Joint order: 16D right arm, right gripper, left arm, left gripper
- Motion flags from server: `send_allowed=false`, `motion_allowed=false`

## Physical Setup

- Put the shirt in the level2-like initial condition: centered and crumpled/bunched, not neatly spread.
- Keep all three cameras connected.
- Use the current base camera first; do not change camera preprocessing before one baseline trial.
- Operator remains at robot with power abort held.

## Pre-Run Checks

1. Confirm live server health at port `8766`.
2. Confirm policy input viewer shows all three camera feeds.
3. Confirm no `send_action`, no `lerobot-rollout`, no `OpenArmFollower.connect` in the actual execution path.
4. Confirm the live harness uses `DamiaoMotorsBus.connect(handshake=False)` and guarded MIT batch commands.
5. Use session-envelope approval, not per-action table approval.

## Baseline Trial Shape

- Scope: `full-16`
- Duration: 120 seconds (full folding cycle)
- Queue: live closed-loop chunk refresh
- Safety mode: monitor-only software measurements; operator visual review and power cutoff are the hard safety gate
- Delta handling: clip to cap
- Limit handling: allow gripper, joint4, and general joint limit saturation while logging counts
- Record eval frames for visual comparison

## Command Template

These commands are templates for after Track B completes. Do not run them during
the A6000 four-GPU training session.

Create an approval draft first:

```bash
TRIAL=/home/syhlabtop/openarm_folding_20260512/rollout_trial_$(date +%Y%m%d_%H%M%S)_level2_messy_shirt
mkdir -p "$TRIAL"
bash audits/openarm_folding/run_rsusb_py312.sh \
  audits/openarm_folding/syhlabtop_live_guarded_rollout.py \
  --trial-root "$TRIAL" \
  --health-url http://10.252.205.103:8766/health \
  --predict-url http://10.252.205.103:8766/predict_live \
  --base-serial 213622075840 \
  --selected-scope full-16 \
  --max-session-duration-s 120 \
  --max-chunks 60 \
  --execution-horizon 20 \
  --refresh-queue-threshold 10 \
  --action-period-s 0.03333333333333333 \
  --interpolation-multiplier 3 \
  --arm-delta-cap-deg 7 \
  --gripper-delta-cap-deg 30 \
  --clip-to-delta-cap \
  --allow-gripper-limit-saturation \
  --allow-joint4-limit-saturation \
  --allow-joint-limit-saturation \
  --readback-stride 0 \
  --hold-last-action \
  --relaxed-proposal-validation \
  --max-consecutive-inference-errors 5 \
  --request-timeout-s 60 \
  --safety-monitor-only \
  --record-eval-frames \
  --record-frame-every-n-obs 30 \
  --approval-draft-json "$TRIAL/live_session/session_envelope.json" \
  --approval-draft-md "$TRIAL/live_session/session_envelope.md"
```

Execute only after the operator approval phrase in the draft is explicitly provided:

```bash
bash audits/openarm_folding/run_rsusb_py312.sh \
  audits/openarm_folding/syhlabtop_live_guarded_rollout.py \
  --trial-root "$TRIAL" \
  --health-url http://10.252.205.103:8766/health \
  --predict-url http://10.252.205.103:8766/predict_live \
  --base-serial 213622075840 \
  --selected-scope full-16 \
  --max-session-duration-s 120 \
  --max-chunks 60 \
  --execution-horizon 20 \
  --refresh-queue-threshold 10 \
  --action-period-s 0.03333333333333333 \
  --interpolation-multiplier 3 \
  --arm-delta-cap-deg 7 \
  --gripper-delta-cap-deg 30 \
  --clip-to-delta-cap \
  --allow-gripper-limit-saturation \
  --allow-joint4-limit-saturation \
  --allow-joint-limit-saturation \
  --readback-stride 0 \
  --hold-last-action \
  --relaxed-proposal-validation \
  --max-consecutive-inference-errors 5 \
  --request-timeout-s 60 \
  --safety-monitor-only \
  --record-eval-frames \
  --record-frame-every-n-obs 30 \
  --session-envelope-json "$TRIAL/live_session/session_envelope.json" \
  --execute \
  --operator-session-approval-given \
  --operator-at-robot \
  --power-held \
  --abort-ready \
  --estop-ready \
  --right-arm-workspace-clear \
  --left-arm-workspace-clear \
  --gripper-workspace-clear \
  --human-body-clear-of-arm \
  --confirm "<APPROVAL_PHRASE_FROM_DRAFT>"
```

## Acceptance Signals

- The policy reaches toward the shirt instead of drifting away.
- The arms try to bring fabric onto the tabletop.
- Gripper actions are directionally useful even if saturated.
- Saturation is logged but does not dominate every step.
- No persistent post-run torque/LED issue.

## Failure Signals

- Base camera mismatch causes clear wrong target selection.
- Both arms move in a way inconsistent with visible shirt location.
- Joint4 or gripper saturation dominates without useful cloth interaction.
- Cleanup summary reports `torque_disable_complete=false`.

## Cleanup Fix

The live harness now disables selected motors one motor at a time and sends repeated disable frames during cleanup. This avoids a single earlier joint disable failure preventing the right gripper disable command from being sent.

The summary records:

- `cleanup_errors`
- `remaining_torque_enabled_motors`
- `torque_disable_complete`
