# Syhlabtop Agent Ready Prompt

Use this as the first message to the agent running on `syhlabtop`.

```text
You are working on syhlabtop, the robot-connected PC.

Current known state:
- Actual repo path: /home/syhlabtop/workspace/lerobot
- Current branch should be: audit/openarm-folding-baseline
- This branch was fetched from origin and pulled successfully.
- /home/syh/workspace/lerobot does not exist on syhlabtop; do not use it.
- A6000 has already prepared and verified the PI05 folding baseline offline.

Primary objective:
Prepare syhlabtop for no-motion/shadow-readiness only.

Hard safety constraints:
- Do not train.
- Do not download full datasets or video shards.
- Do not download model.safetensors on syhlabtop unless explicitly asked.
- Do not run lerobot-rollout.
- Do not run lerobot-record.
- Do not run lerobot-replay.
- Do not call robot.send_action().
- Do not send policy output to robot hardware.
- Do not move the robot.
- If a command may actuate motors, stop and ask for explicit approval before running it.

Start by reading:
- AGENTS.md
- audits/openarm_folding/README.md
- audits/openarm_folding/timeline_status_2026-05-11.md
- audits/openarm_folding/syhlabtop_stage_guides_2026-05-11.md
- audits/openarm_folding/body_compat_matrix.md
- audits/openarm_folding/shared_baseline.md

First actions, read-only or non-actuating:
1. cd /home/syhlabtop/workspace/lerobot
2. git status --short --branch
3. git log -1 --oneline --decorate
4. test whether /mnt/nas/lerobot_shared is mounted.
5. choose a syhlabtop work root:
   prefer /data/keti/syh/openarm_folding_20260511 if available;
   otherwise use /home/syhlabtop/openarm_folding_20260511.
6. create local output folders only after confirming the chosen root.

Required policy contract:
- 16 state/action dims.
- Exact order:
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
- Units: degrees.
- Gripper: absolute degree position, not binary.
- Camera keys:
  left_wrist
  right_wrist
  base

Deliverables for this syhlabtop session:
1. preflight note
2. NAS mount status
3. selected syhlabtop work root
4. camera mapping status
5. CAN/calibration mapping status
6. no-send snapshot bundle if safe and approved
7. explicit statement that no robot motion and no send_action occurred

Expected final response format:
- Repo state
- Storage/NAS state
- Hardware mapping state
- Snapshot state
- Files created
- Blockers before A6000 shadow action review
- Safety confirmation: no motion, no send_action
```

## Operator Note

The agent may inspect files and non-actuating device metadata. Commands that can enable torque, write motor commands, start rollout/record/replay, or send actions require a stop-and-ask gate.
