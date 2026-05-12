# Stage 36 A6000 Serving Bridge

Date: 2026-05-12

## Purpose

Serve the corrected folding PI0.5 checkpoint on A6000 while syhlabtop owns
camera/robot I/O. Stage 36 is a no-send bridge: A6000 returns action proposals
and syhlabtop logs them, but syhlabtop does not send actions to the robot.

## Boundary

```text
a6000_model_server: RUNNING
syhlabtop_client: PASS
robot_write: FORBIDDEN
send_action: false
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```

The bridge must pass a single-frame proposal check before any new actuator
write can be discussed. Any next actuator write requires a separate exact
command, target table, and operator approval.

## A6000 Server

Tool:

```text
audits/openarm_folding/a6000_snapshot_policy_server.py
```

Command:

```bash
BASE=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
CKPT=$BASE/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
cd /home/syh/workspace/lerobot
TRANSFORMERS_OFFLINE=1 \
HF_HOME=/mnt/nas/huggingface \
HF_HUB_CACHE=/mnt/nas/huggingface/hub \
PYTHONPATH=/home/syh/workspace/lerobot/src \
  $BASE/probevenv/bin/python \
  audits/openarm_folding/a6000_snapshot_policy_server.py \
  --model-dir "$CKPT" \
  --allowed-snapshot-root "$BASE/syhlabtop_snapshots" \
  --host 0.0.0.0 \
  --port 8765 \
  --device cuda:0
```

The server has no robot access and always returns:

```text
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
```

## syhlabtop Client

Tool:

```text
audits/openarm_folding/syhlabtop_snapshot_policy_client.py
```

The client posts an A6000 snapshot directory reference to:

```text
http://10.252.205.103:8765/predict_snapshot
```

The client never imports or calls a robot write path.

## 2026-05-12 Result

The bridge returned one no-send action proposal for
`snapshot_20260512_194042`.

```text
all_finite: true
action_shape: [1, 30, 16]
max_abs_arm_delta_deg: 2.1111412048339844
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
```

Artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_a6000_served_action_proposal.json
sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_a6000_served_action_proposal.md
sha256: 3159601cf434dd6e0299ca24ae66180ff64d637d8adb59c8cb8db11085afe04e
```

The artifacts were copied to A6000 and checksums matched:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage36_served_proposals/snapshot_20260512_194042/
```

The next motion target table is drafted in:

```text
audits/openarm_folding/stage37_served_proposal_motion_approval_draft_2026-05-12.md
```
