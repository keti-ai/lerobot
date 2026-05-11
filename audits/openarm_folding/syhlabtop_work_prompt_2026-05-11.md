# Syhlabtop Work Prompt for OpenArm Folding Shadow Readiness

Use this prompt on `syhlabtop`, the robot work PC.

```text
We are on syhlabtop, the real robot work PC, for the LeRobot OpenArm folding baseline.

Date: 2026-05-11
Repo expected: /home/syh/workspace/lerobot
Branch expected: audit/openarm-folding-baseline
Primary objective: no-motion/shadow readiness only.

Hard constraints:
- Do not train.
- Do not download full datasets or video shards.
- Do not download model.safetensors on syhlabtop unless explicitly requested.
- Do not run autonomous rollout.
- Do not run lerobot-rollout, lerobot-record, or lerobot-replay as the first action.
- Do not send policy output to the robot.
- Do not call robot.send_action().
- Do not move the robot without explicit operator approval in this session.
- If any command could actuate motors, stop and ask before running it.

Read first:
- AGENTS.md
- audits/openarm_folding/README.md
- audits/openarm_folding/artifact_audit.md
- audits/openarm_folding/body_compat_matrix.md
- audits/openarm_folding/shared_baseline.md
- audits/openarm_folding/two_machine_pipeline_2026-05-11.md
- audits/openarm_folding/robot_test_work_spec_2026-05-11.md
- audits/openarm_folding/a6000_persistent_setup_2026-05-11.md

Known A6000 side status:
- A6000 persistent setup exists at:
  /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
- A6000 policy load probe passed for lerobot/folding_latest on cuda:0.
- A6000 synthetic no-robot action probe passed.
- NAS Hugging Face cache is used on A6000:
  HF_HOME=/mnt/nas/huggingface
  HF_HUB_CACHE=/mnt/nas/huggingface/hub
- NAS handoff root, if mounted on syhlabtop:
  /mnt/nas/lerobot_shared/openarm_folding_20260511

Baseline policy contract:
- Policy repo: lerobot/folding_latest
- Policy type: pi05, LeRobot-native checkpoint layout, OpenPI-derived implementation, no runtime OpenPI import expected.
- State/action length: 16.
- State/action exact order:
  1. right_joint_1.pos
  2. right_joint_2.pos
  3. right_joint_3.pos
  4. right_joint_4.pos
  5. right_joint_5.pos
  6. right_joint_6.pos
  7. right_joint_7.pos
  8. right_gripper.pos
  9. left_joint_1.pos
  10. left_joint_2.pos
  11. left_joint_3.pos
  12. left_joint_4.pos
  13. left_joint_5.pos
  14. left_joint_6.pos
  15. left_joint_7.pos
  16. left_gripper.pos
- Units: degrees for OpenArm/Damiao .pos values.
- Gripper semantics: absolute positional degree command, not binary; gripper is excluded from relative action conversion.
- Camera keys expected by policy:
  observation.images.left_wrist
  observation.images.right_wrist
  observation.images.base
- Processor chain:
  preprocessor includes RelativeActionsProcessorStep before normalization.
  postprocessor includes UnnormalizerProcessorStep then AbsoluteActionsProcessorStep.

Start by doing only non-actuating preflight:
1. Confirm repo path, branch, and git status.
2. Confirm whether /mnt/nas/lerobot_shared is mounted.
3. Choose syhlabtop local work root:
   <syhlabtop-work-root>
   Recommended if available:
   /data/keti/syh/openarm_folding_20260511
   Otherwise:
   ~/openarm_folding_20260511
4. Create local folders:
   <syhlabtop-work-root>/audits
   <syhlabtop-work-root>/camera_maps
   <syhlabtop-work-root>/hardware/openarm
   <syhlabtop-work-root>/calibration
   <syhlabtop-work-root>/shadow_snapshots
   <syhlabtop-work-root>/shadow_reviews
   <syhlabtop-work-root>/safety_configs
5. Write a preflight note:
   <syhlabtop-work-root>/audits/2026-05-11_preflight_syhlabtop.md

Next, inspect hardware mapping without motion:
1. Identify available cameras and map them to:
   left_wrist
   right_wrist
   base
2. Save camera probe output under:
   <syhlabtop-work-root>/camera_maps/
3. Identify CAN interfaces, motor bus names, calibration files, and left/right arm mapping.
4. Save CAN/calibration notes under:
   <syhlabtop-work-root>/hardware/openarm/
   <syhlabtop-work-root>/calibration/

If and only if the operator confirms it is safe to connect to robot IO without motion, produce a no-send snapshot bundle:

snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json

Snapshot requirements:
- The state_16.csv columns must exactly match the 16 names above.
- Values must be degrees.
- metadata.json must include timestamp, syhlabtop hostname, repo commit, branch, camera mapping, robot config path if used, and send_allowed=false.
- Do not compute policy action on syhlabtop unless explicitly requested.
- Do not send any action.

If NAS is mounted, copy the snapshot bundle to:
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/

Expected final response:
- Summarize repo/branch/worktree.
- State whether NAS is mounted.
- State selected syhlabtop work root.
- List camera mapping status.
- List CAN/calibration mapping status.
- List snapshot path if created.
- Clearly state that no robot motion and no send_action occurred.
- List blockers before A6000 shadow action review.
```
