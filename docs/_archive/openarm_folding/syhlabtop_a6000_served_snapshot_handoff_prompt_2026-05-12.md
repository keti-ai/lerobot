# syhlabtop A6000-Served Snapshot Handoff Prompt

Date: 2026-05-12

Copy this whole prompt to the syhlabtop agent.

---

You are the syhlabtop agent for the OpenArm folding Stage 32 no-send handoff.

The baseline architecture is two-machine:

- syhlabtop owns real robot/camera I/O and safety.
- A6000 owns the PI0.5 model weights and inference/review.

Do not try to run the PI0.5 model on syhlabtop. Do not transfer
`model.safetensors` to syhlabtop for the baseline path. syhlabtop should produce
a read-only observation snapshot bundle and transfer that bundle to A6000.

## Current A6000 Candidate

A6000 final checkpoint:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
```

A6000 final status:

- Full retraining: PASS, exit `0`.
- Corrected Stage 29 metadata gate: PASS.
- Stage 31 dataset replay acceptance: PASS.
- No 60-70 degree abnormal delta in checked replay frames.

Latest repo branch:

```text
audit/openarm-folding-baseline
```

Minimum required history:

```text
50078e4dff69e66acd12864b3990d954f24d6288
```

The actual HEAD may be newer. It is acceptable if the repo contains this file
and includes commit `50078e4d` in history.

## Hard Stops

Do not run:

- `lerobot-rollout`
- `lerobot-record`
- `lerobot-replay`
- real robot rollout
- dataset replay to robot
- `robot.send_action()`
- torque enable for motion
- zeroing
- actuator write
- CAN write
- calibration write
- any command that can physically move the robot

Do not download or transfer:

- `model.safetensors`
- full datasets

If a command might move the robot, stop and ask the human operator for explicit
approval with the exact command and expected physical effect.

## Work Root

Use:

```bash
WORK=/home/syhlabtop/openarm_folding_20260512
```

Expected directories:

```bash
mkdir -p \
  "$WORK/audits" \
  "$WORK/camera_maps" \
  "$WORK/hardware/openarm" \
  "$WORK/calibration" \
  "$WORK/shadow_snapshots" \
  "$WORK/shadow_reviews" \
  "$WORK/safety_configs"
```

Do not create a local model checkpoint directory unless the human explicitly
changes the architecture away from A6000 serving/review.

## Step 1: Sync Repo

Run:

```bash
cd /home/syhlabtop/workspace/lerobot
git status --short
git pull origin audit/openarm-folding-baseline
git rev-parse HEAD
git merge-base --is-ancestor 50078e4dff69e66acd12864b3990d954f24d6288 HEAD
test -f audits/openarm_folding/syhlabtop_a6000_served_snapshot_handoff_prompt_2026-05-12.md
```

Expected:

- `git merge-base --is-ancestor ...` exits `0`.
- This prompt file exists.

If the worktree has local changes, report them. Do not revert anything unless
the human explicitly asks.

## Step 2: Record A6000-Served Architecture

Write:

```text
$WORK/audits/stage32_architecture_precheck_2026-05-12.md
```

Include:

- syhlabtop will not load PI0.5 model weights.
- syhlabtop will not receive `model.safetensors`.
- A6000 remains model/inference owner.
- syhlabtop will produce a snapshot bundle only.
- motion status is `BLOCKED`.

This converts the earlier missing-local-model result from a blocker into an
expected architecture choice.

## Step 3: Read-Only Hardware And Camera Preflight

This step touches real hardware interfaces but must remain read-only.

Allowed:

- list USB/video devices
- inspect camera serial/path mapping
- capture single camera frames if the capture path is read-only
- read robot state only if the local operator confirms the read path does not
  torque-enable or command motion

Forbidden:

- torque enable
- zeroing
- calibration write
- actuator write
- `send_action`
- any motion

Capture/report:

- camera device paths
- mapping to left wrist, right wrist, base
- observed frame shapes
- read-only robot state availability
- current 16D state vector if safely available

Expected camera files for A6000 snapshot review:

```text
left_wrist.png
right_wrist.png
base.png
```

Expected state order:

```text
right_joint_1.pos
right_joint_2.pos
right_joint_3.pos
right_joint_4.pos
right_joint_5.pos
right_joint_6.pos
right_joint_7.pos
right_gripper.pos
left_joint_1.pos
left_joint_2.pos
left_joint_3.pos
left_joint_4.pos
left_joint_5.pos
left_joint_6.pos
left_joint_7.pos
left_gripper.pos
```

Write:

```text
$WORK/audits/stage32_readonly_hardware_preflight_2026-05-12.md
```

## Step 4: Create Snapshot Bundle

Only after read-only camera/state checks pass, create one snapshot directory:

```bash
SNAP="$WORK/shadow_snapshots/snapshot_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SNAP"
```

Required snapshot layout:

```text
$SNAP/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

`state_16.csv` must have exactly the 16 columns in the expected state order
above, followed by one row of current read-only values.

`metadata.json` should include:

```json
{
  "obs_id": "snapshot_YYYYMMDD_HHMMSS",
  "timestamp": "YYYY-MM-DDTHH:MM:SS+09:00",
  "robot_type": "openarms_follower",
  "task": "Fold the T-shirt properly",
  "motion_status": "BLOCKED",
  "model_owner": "A6000",
  "inference_location": "A6000_offline_review",
  "send_action": false
}
```

Write:

```text
$WORK/audits/stage32_snapshot_bundle_manifest_2026-05-12.md
```

Include file sizes and SHA256 sums:

```bash
cd "$SNAP"
sha256sum state_16.csv left_wrist.png right_wrist.png base.png metadata.json
```

## Step 5: Transfer Snapshot Bundle To A6000

Preferred direct transfer from syhlabtop:

```bash
A6000_HOST=<fill-real-a6000-host-or-ip>
SNAP=<snapshot-dir-created-above>
A6000_DEST=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots

ssh "syh@$A6000_HOST" "mkdir -p '$A6000_DEST'"
rsync -avh --progress "$SNAP/" "syh@$A6000_HOST:$A6000_DEST/$(basename "$SNAP")/"
```

If direct SSH is not available, stop and report the local snapshot path. Do not
invent a transfer method without operator approval.

## Step 6: A6000 No-Send Review Command

This step is for the A6000 agent/operator, not syhlabtop.

Once the snapshot is on A6000, run on A6000:

```bash
BASE=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
CKPT=$BASE/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
SNAP=$BASE/syhlabtop_snapshots/<snapshot-dir-name>

TRANSFORMERS_OFFLINE=1 \
HF_HOME=/mnt/nas/huggingface \
HF_HUB_CACHE=/mnt/nas/huggingface/hub \
$BASE/probevenv/bin/python \
  $BASE/tools/a6000_snapshot_action_review.py \
  --model-dir "$CKPT" \
  --snapshot-dir "$SNAP" \
  --device cuda:0 \
  --csv-out "$BASE/shadow_replays/$(basename "$SNAP")_action_review.csv" \
  --json-out "$BASE/shadow_replays/$(basename "$SNAP")_action_review.json"
```

The review output is no-send only. It does not authorize robot motion.

## Step 7: Report Back

Report in this format:

```text
repo_head:
architecture: syhlabtop_snapshot__a6000_inference
local_model_on_syhlabtop: NO
candidate_checksum: NOT_APPLICABLE_A6000_OWNS_MODEL
camera_mapping:
state_order_check: PASS/FAIL/NOT_RUN
snapshot_bundle: CREATED/NOT_CREATED
snapshot_path:
snapshot_transfer_to_a6000: DONE/BLOCKED/NOT_RUN
a6000_review: PASS/FAIL/NOT_RUN
motion_status: BLOCKED
next_blocker:
artifact_paths:
```

The only acceptable `motion_status` is `BLOCKED`.

## Stop Conditions

Stop immediately if:

- camera mapping is ambiguous
- state order is ambiguous
- read-only robot state access appears to torque-enable or write to hardware
- required snapshot files cannot be created
- direct transfer to A6000 is unavailable and no approved alternative exists

Do not proceed to guarded first motion. Live A6000 serving for robot control is
a separate architecture gate because the current LeRobot rollout code does not
provide an audited split-host inference transport.
