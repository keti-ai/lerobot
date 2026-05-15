# OpenArm Folding Timeline Status

Date: 2026-05-11
Task: LeRobot OpenArm folding baseline, no-motion/shadow readiness and
post-gripper-zero bringup.

## Current Position in the Timeline

The original no-send two-machine pipeline reached Stage 11. A gripper-only zero
adjustment was then completed on `syhlabtop`. A refreshed post-gripper-zero
snapshot and A6000 offline review have now completed; the next milestone is a
guarded first-motion command path specification only.

```text
Stage 0  Goal/safety framing                         DONE
Stage 1  Repo preflight on A6000                     DONE
Stage 2  Shared audit docs                           DONE
Stage 3  A6000 model/config asset preparation        DONE
Stage 4  A6000 offline policy load                   DONE
Stage 5  syhlabtop repo/handoff readiness            DONE
Stage 6  syhlabtop camera mapping                    DONE
Stage 7  syhlabtop CAN/calibration mapping           DONE
Stage 8  syhlabtop no-send observation snapshot      DONE
Stage 9  A6000 snapshot action review                DONE
Stage 10 syhlabtop human/safety review               DONE FOR NO-SEND
Stage 11 summary and next blocker list               DONE
Stage 12 syhlabtop gripper-only zero adjustment      DONE
Stage 13 refreshed no-send snapshot after gripper    DONE
Stage 14 refreshed A6000 snapshot action review      DONE
Stage 15 guarded first-motion command path spec      DONE FOR DRY-RUN
Stage 16 guarded first-motion runtime preflight      DONE FOR NO-SEND
Stage 17 guarded first-motion execution packet       DONE FOR NO-SEND
Stage 18 guarded first-motion actuator writer        DONE FOR DRY-RUN
Stage 19 first actuator write execution              BLOCKED: STALE PACKET
Stage 20 high-overview camera/action review loop     DONE: LARGE DELTAS REMAIN
Stage 21 action contract diagnosis                   DONE: POLICY DELTAS OFF-DISTRIBUTION
```

The next real-machine work is on `syhlabtop`. The objective is still not motion.
Stage 15 produced a guarded dry-run target table, Stage 16 verified current
readback drift, and Stage 17 built a no-send execution packet. Guarded actuator
write remains blocked until a separate writer, operator gate, and abort
procedure exist.

Current renewed work spec:

```text
audits/openarm_folding/renewed_bringup_plan_2026-05-11.md
audits/openarm_folding/post_gripper_zero_snapshot_review_2026-05-11.md
audits/openarm_folding/stage15_guarded_first_motion_spec_2026-05-11.md
audits/openarm_folding/stage16_runtime_preflight_spec_2026-05-11.md
audits/openarm_folding/stage17_execution_packet_spec_2026-05-11.md
audits/openarm_folding/stage18_guarded_actuator_write_spec_2026-05-11.md
audits/openarm_folding/stage19_first_write_blocked_2026-05-11.md
audits/openarm_folding/stage20_high_overview_camera_trial_2026-05-11.md
audits/openarm_folding/stage21_action_contract_diagnosis_2026-05-11.md
```

Stage 20 tested a raised D435I base camera on a temporary 25 cm jig. The base
view became closer to the `full_folding` high overview framing, but the A6000
offline review still produced large bimanual arm deltas:

```text
snapshot_20260511_175613
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
mean_abs_delta: 26.593 deg
max_abs_delta: 72.753 deg at right_joint_4.pos
clamped_rows: 4
```

This keeps motion blocked and shifts the likely root cause toward folding
embodiment mismatch, wrist camera/task-signal mismatch, or action/state contract
details rather than base camera height alone.

Stage 21 compared `lerobot/full_folding` episode 0 parquet data against the
syhlabtop A6000 action reviews. Dataset arm action deltas are small, while both
syhlabtop snapshots are far outside the dataset delta distribution:

```text
dataset rows compared: 1505
chest_154554 mean_abs_delta: 25.462 deg
high_175613  mean_abs_delta: 26.593 deg
right_joint_4 dataset p99 delta: 3.389 deg
right_joint_4 syhlabtop delta: -67.930 / -72.753 deg
postprocessor reconstruction error: 0.000000 deg
```

This rules out the paired relative/absolute postprocessor as the immediate
cause and keeps policy RUN blocked. The next diagnostic target is the mismatch
between current ready/zero state, visual input distribution, and dataset feature
semantics before policy inference.

## A6000 Status

Repo:

```text
/home/syh/workspace/lerobot
branch: audit/openarm-folding-baseline
```

Committed and pushed before this no-NAS follow-up:

```text
faa94c4b docs: add OpenArm folding baseline audit
65de9226 docs: prepare syhlabtop shadow readiness handoff
f4476842 docs: update OpenArm timeline commit status
origin/audit/openarm-folding-baseline
```

Persistent runtime root:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511
```

Verified:

- `lerobot/folding_latest` model/config/processor files exist under `/data`.
- PI05 policy loads on `cuda:0`.
- Runtime preprocessor and postprocessor load successfully.
- NAS Hugging Face cache resolves the PaliGemma tokenizer dependency.
- Synthetic no-robot action probe returns finite `[1, 30, 16]` actions.
- Synthetic probe records `send_allowed=false`.

Not performed:

- No robot IO.
- No training.
- No rollout/replay/record.
- No full dataset/video shard download.

## NAS Status from A6000

Available on A6000:

```text
/mnt/nas/huggingface
/mnt/nas/lerobot_shared
```

Handoff root prepared:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511
  audits/
  syhlabtop_snapshots/
  a6000_shadow_replays/
```

`syhlabtop` has confirmed that this NAS path is not mounted. Use local syhlabtop storage and transfer snapshots manually after operator approval.

## Syhlabtop Status from Live Session

Confirmed by the live syhlabtop session:

```text
repo path: /home/syhlabtop/workspace/lerobot
branch: audit/openarm-folding-baseline
git pull: Already up to date
origin/audit/openarm-folding-baseline: fetched
```

Also confirmed:

- `/home/syh/workspace/lerobot` does not exist on syhlabtop.
- The syhlabtop agent successfully read `audits/openarm_folding/syhlabtop_work_prompt_2026-05-11.md`.
- Some git operations initially hit read-only sandbox restrictions, then succeeded after explicit approval.
- `/mnt/nas/lerobot_shared` is not mounted on syhlabtop.
- `/data` does not exist on syhlabtop.
- syhlabtop root filesystem has about 131G available.
- Recommended syhlabtop work root is `/home/syhlabtop/openarm_folding_20260511`.
- The latest real-robot context was imported from `/home/syhlabtop/workspace/openarm_lerobot`.
- Camera mapping was confirmed from existing dataset/LeRobot contract and RSUSB samples:
  - `left_wrist`: D405 `315122270766`
  - `right_wrist`: D405 `230322273311`
  - `base`: D435 `234322070493`
  - D415 `211622062255` is auxiliary situation/workspace recording only.
- CAN mapping from the existing OpenArm real-robot records:
  - `can0`: physical left arm
  - `can1`: physical right arm
- A no-send snapshot was created without `OpenArmFollower.connect()`, without
  handshake enable, without zeroing, without goal writes, without `send_action`,
  and without rollout/record/replay.

## Next Required Output from Syhlabtop

Minimum no-motion output produced:

```text
/home/syhlabtop/openarm_folding_20260511/audits/2026-05-11_preflight_syhlabtop.md
/home/syhlabtop/openarm_folding_20260511/camera_maps/2026-05-11_camera_probe.md
/home/syhlabtop/openarm_folding_20260511/hardware/openarm/2026-05-11_can_calibration_probe.md
/home/syhlabtop/openarm_folding_20260511/calibration/2026-05-11_calibration_probe.md
```

Target snapshot output produced:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_135634/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

NAS is not mounted on syhlabtop. If mounted later, copy snapshots to:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/
```

Current syhlabtop status says NAS is not mounted. Until that changes, the snapshot remains local under:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/
```

Then use an explicit operator-approved transfer method to A6000. Do not improvise a transfer command inside the robot session.

## A6000 Snapshot Action Review

Snapshot transfer completed by approved `scp` from syhlabtop to A6000/NAS:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/snapshot_20260511_135634.tar.gz
sha256: 97f1a3d18b13ff4cc3deb78bb7c070991290bcca29e748d48fbab31972de8fbb
```

A6000 offline review completed with `a6000_snapshot_action_review.py`.

Results:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
rows in review csv: 16
clamped rows: 4
max_abs_delta: 62.198 deg at action_id=0, right_joint_4.pos
```

Output artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_135634_action_review.csv
sha256: 7542511654c2124bade6047a3f7b91ae96b169d23fe21d41c20037db3605de9e

/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_135634_action_review.json
sha256: c2c53b2545ab3122d82602b4c1adc8c775db46eebc5ddeaf431f607da8e1b06f

/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/snapshot_20260511_135634_action_review.csv
/mnt/nas/lerobot_shared/openarm_folding_20260511/a6000_shadow_replays/snapshot_20260511_135634_action_review.json
```

Human review of camera orientation and proposed action deltas is still required
before any later motion gate.

The A6000 review artifacts were also copied back to syhlabtop for Stage 10:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_135634_action_review.csv
/home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_135634_action_review.json
```

Received-review note:

```text
audits/openarm_folding/syhlabtop_shadow_action_review_received_2026-05-11.md
```

Operator hardware review:

- The current robot posture is the intended zero posture.
- Camera mounts are judged correct at the hardware level.
- Continue review against the existing dataset/LeRobot camera convention and the
  A6000 action proposal deltas.

Stage 10/11 review summary:

```text
audits/openarm_folding/stage10_stage11_review_and_blockers_2026-05-11.md
```

Result:

- no-send two-machine pipeline validated end to end;
- A6000 action proposal received and inspected on syhlabtop;
- 4 clamped rows and several large deltas were identified;
- the action proposal is not approved as an actuator command;
- motion remains blocked until a separate guarded motion path is implemented
  and explicitly approved.

Manual no-send direction probe:

```text
audits/openarm_folding/no_send_direction_probe_results_2026-05-11.md
```

Key findings:

- `right_joint_2` physical shoulder lift is positive, while `left_joint_2`
  physical shoulder lift is negative; this matches the existing mirrored limits.
- `joint_4` elbow flex is positive on both arms.
- `right_joint_7` wrist flap up is positive, while `left_joint_7` wrist flap up
  is negative; `left_joint_7` range/sign needs explicit handling before motion.
- both grippers close in the positive direction and reached about `+36` to
  `+38 deg`; this shows the existing bimanual record preset `[-90, 45]` covers
  more physical travel than the LeRobot baseline `[-65, 0]`, but does not prove
  the baseline range is wrong.
- For initial deploy safety, prefer the LeRobot baseline gripper range unless a
  separate folding-specific gripper range is explicitly approved.
- After confirming the vendor-provided follower arms were already zeroed and
  only gripper motors had been replaced, both follower gripper motors were
  manually closed and zeroed individually with motor ID `008` only:
  `can0 008` and `can1 008`.
- Post-adjustment closed readback was approximately `-0.011 deg` on both
  grippers; slightly open readback moved negative (`left=-26.633`,
  `right=-23.245`), matching OpenArm's `0=closed`, negative=open convention.
- No arm joint zero was changed and no full-arm zero-position calibration was
  run.

Impact of the gripper-only zero adjustment:

- The old A6000 review for `snapshot_20260511_135634` remains useful as an
  end-to-end no-send pipeline validation.
- That old review is stale as a command candidate because it used the
  pre-gripper-zero hardware state.
- The next required output is a refreshed post-gripper-zero no-send snapshot,
  followed by a refreshed A6000 offline action review.

Post-gripper-zero snapshot and A6000 review completed:

```text
snapshot: /home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_20260511_154554
snapshot tar sha256: b47804f7e29821fc7c0714cdd6ded02a87f4c8c9b1f2bc184310a2e43931df8b

A6000 csv: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_154554_action_review.csv
A6000 json: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260511_154554_action_review.json
csv sha256: ae203f49bca1d05ea01f9cd43affec69b45750d843c1809fde2bc7d64f8d1fb6
json sha256: 75a2136cb6eba5d3870d4d23a516d9b3050a21d1055871562b8e839142bfb6a1
```

Review result:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
rows: 16
clamped_rows: 4
max_abs_delta: 67.930 deg at right_joint_4.pos
```

The refreshed action proposal is not approved as an actuator command.

Stage 15 guarded dry-run completed:

```text
tool: audits/openarm_folding/guarded_first_motion_dry_run.py
spec: audits/openarm_folding/stage15_guarded_first_motion_spec_2026-05-11.md
dry-run json: /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_guarded_first_motion_dry_run.json
dry-run json sha256: ce6c6efb2d6b2d7532500cb7b4ca61273993358ccd1ef437e4ae25781ee2cef3
arm cap: 2 deg
gripper cap: 5 deg
held key: left_joint_7.pos
max final delta: 5 deg
send_allowed: false
motion_allowed: false
```

Stage 16 no-send runtime preflight completed:

```text
tool: audits/openarm_folding/guarded_first_motion_runtime_preflight.py
spec: audits/openarm_folding/stage16_runtime_preflight_spec_2026-05-11.md
preflight json: /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_runtime_preflight.json
preflight json sha256: e29ca7aa1ec00a124a0f141842b7efa1a01a8bbb45397ad6ade6f9db3dcc49aa
all_within_drift_limit: true
blocking_keys: []
arm drift limit: 1 deg
gripper drift limit: 3 deg
send_allowed: false
motion_allowed: false
```

Stage 17 no-send execution packet completed:

```text
tool: audits/openarm_folding/guarded_first_motion_execution_packet.py
spec: audits/openarm_folding/stage17_execution_packet_spec_2026-05-11.md
packet json: /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_execution_packet_no_send.json
packet json sha256: e2627900430cda3aac90739babb35cc0ba7df8b19a89d3704ea8545505187d2f
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
all rows would_send: false
```

Stage 18 guarded actuator writer prepared:

```text
tool: audits/openarm_folding/guarded_first_motion_actuator_write.py
spec: audits/openarm_folding/stage18_guarded_actuator_write_spec_2026-05-11.md
scope: can1 right arm joint_1..joint_7 only
excluded: left arm, right_gripper, left_gripper
default: dry-run readback validation only
execute gate: --execute --power-held --confirm SEND_RIGHT_ARM_JOINTS_ONCE_20260511
dry-run json: /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_stage18_dry_run.json
dry-run json sha256: c300381df2ac5d7fc93123a9bb2168bed28f7e475bb7b7dfed9dcc3e9fdbb8ad
dry-run actuator_commands_sent: false
```

Stage 19 operator-gated write attempt blocked:

```text
log: /home/syhlabtop/openarm_folding_20260511/shadow_reviews/snapshot_20260511_154554_stage18_execute_blocked.json
sha256: 4aefc44e4b7dd74583bbebd63a57d1e6dbece9ecb294edfc7c7ca54589999d28
send_allowed: false
motion_allowed: false
actuator_commands_sent: false
blocked keys: right_joint_1.pos, right_joint_2.pos, right_joint_3.pos, right_joint_4.pos, right_joint_7.pos
reason: fresh readback drift/target delta exceeded stale-packet limits
```

## Motion Gate

Motion remains blocked. A6000 has produced offline action proposals only; no
policy output has been sent to robot actuators. The only hardware write after
the original no-send pipeline was the operator-approved gripper-only zero on
motor ID `008` for `can0` and `can1`. Stage 15 defined a dry-run target table
only, Stage 16 verified current readback without command writes, and Stage 17
built a no-send execution packet. Stage 18 added a guarded right-arm writer and
its dry-run validation passed. Stage 19 was operator-gated but blocked before
torque enable or MIT batch because the packet became stale. The next step is a
new no-send snapshot and A6000 offline review from the current hardware state.

## 2026-05-11 Stage 20-23 Update

Stage 20 high-overview camera trial completed. Raising/swapping the base camera
improved the visual match to the dataset overview, but large policy deltas
remained.

Stage 21 action-contract diagnosis completed. The PI0.5 postprocessor
relative-to-absolute reconstruction is internally consistent, and the
`full_folding` recorded `action - observation.state` deltas are small.

Stage 22 dataset replay and Stage 23 ablation completed. The loaded
`folding_latest` checkpoint produces large deltas even on actual
`lerobot/full_folding` episode 0 dataset images and dataset state:

```text
frame 0  model mean_abs_delta=25.055 deg, recorded mean_abs_delta=0.674 deg
frame 1  model mean_abs_delta=25.978 deg, recorded mean_abs_delta=0.465 deg
frame 10 model mean_abs_delta=26.492 deg, recorded mean_abs_delta=0.621 deg
frame 30 model mean_abs_delta=24.052 deg, recorded mean_abs_delta=0.472 deg
```

State/visual ablation did not isolate the issue to syhlabtop hardware inputs;
all combinations remained in the 24-27 deg mean absolute delta range.

Current conclusion: deployment is blocked by checkpoint/runtime/processor
contract validation, not by a first-write clamp tuning problem. The checkpoint
postprocessor action quantiles appear to match absolute joint-angle
distributions while `use_relative_actions=true`, which must be validated against
the training-time normalization path before any robot motion.

Stage 24 normalized target probe completed. On dataset frames `0` and `1`, the
model's raw normalized action output does not match the normalized recorded
relative target:

```text
frame 0 mean_abs_raw_error=0.680, max_abs_raw_error=1.518 at right_joint_4.pos
frame 1 mean_abs_raw_error=0.673, max_abs_raw_error=1.483 at right_joint_4.pos
```

This confirms the failure exists before postprocessing and before any
syhlabtop-specific hardware input. The next required step is to verify the
intended checkpoint identity/training export and reproduce dataset replay with
the exact training-time inference code or a known-good Hugging Face baseline
script. Robot motion remains blocked.

Stage 25 replayed the model-card training dataset
`lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`, not
`lerobot/full_folding`. The same large-delta failure remained:

```text
frame 0  model mean_abs_delta=25.588 deg, recorded mean_abs_delta=1.300 deg
frame 1  model mean_abs_delta=24.644 deg, recorded mean_abs_delta=1.156 deg
frame 10 model mean_abs_delta=26.065 deg, recorded mean_abs_delta=1.424 deg
frame 30 model mean_abs_delta=27.654 deg, recorded mean_abs_delta=1.325 deg
```

Stage 26 recipe alignment identified the strongest root cause: `folding_latest`
has `use_relative_actions=true`, but its saved action normalizer/unnormalizer
quantiles match absolute action stats from the training dataset. Official
LeRobot Pi05/action-representation docs require recomputing stats in relative
action space before training with relative actions. The current recipe is
therefore not aligned, and robot motion remains blocked until a corrected
checkpoint/processor recipe passes dataset replay.

Stage 27 added a hard folding recipe gate to
`audits/openarm_folding/stage22_dataset_replay_and_ablation.py`. The gate is
based on the `robot-folding` Space recipe: bimanual OpenArm, 16D state/action,
three camera keys/shapes, Pi05, chunk 30, relative trajectory with gripper
excluded, SARM/RABC recorded, and RTC/interpolation as deployment expectations.
The current `folding_latest` passes structural checks but fails the critical
relative-action stats check:

```text
postprocessor_action_stats_are_relative_for_arm_joints: FAIL
max_post_vs_relative_q01_error_deg: 69.973
max_post_vs_relative_q99_error_deg: 110.695
max_arm_span_ratio_postprocessor_over_sampled_relative: 14.230
```

The script now returns exit code `2` when the recipe gate fails, while still
writing JSON/Markdown diagnostics. Robot motion remains blocked.

## 2026-05-11 Stage 28-30 Update

Stage 28 locked the recovery runbook and source map for the folding recipe.
The canonical gate source remains
`audits/openarm_folding/stage22_dataset_replay_and_ablation.py`; bypassing the
recipe gate is reserved only for forensics.

Stage 29 ran the lightweight candidate recipe gate on A6000. The expanded
search checked 37 public folding/level/ablation checkpoint candidates and found
zero deploy candidates. The two direct target-dataset candidates,
`lerobot/folding_latest` and `lerobot-data-collection/folding_final10`, both
failed only the relative-action postprocessor stats check:

```text
postprocessor_action_stats_are_relative_for_arm_joints: FAIL
max_post_vs_relative_q01_error_deg: 69.973
max_post_vs_relative_q99_error_deg: 110.695
max_arm_span_ratio_postprocessor_over_sampled_relative: 14.230
```

Stage 30 computed the target dataset relative-action reference over all
`3414338` rows:

```text
dataset: lerobot-data-collection/level2_final_quality3_t_0_hil_data_c
robot_type: openarms_follower
arm mean abs relative delta: 1.722 deg
arm p99 abs relative delta: 19.789 deg
arm max abs relative delta: 116.352 deg at left_joint_4.pos
```

Current conclusion: no currently checked public checkpoint can advance to robot
deployment. The next required work is corrected relative-action dataset stats
followed by retrain or re-export, then Stage 29 gate and Stage 31 dataset
replay. Robot motion remains blocked.

## 2026-05-12 Stage 31-32 Update

A6000 offline recovery training completed. The training used a new chunk-size
30 relative-stats dataset root derived from
`lerobot-data-collection/level2_final_quality3_t_0_hil_data_c`, with arm joints
converted to relative actions and grippers excluded from relative conversion.

Final checkpoint:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
```

Training outcome:

```text
steps: 4000/4000
exit_status: 0
final logged loss: 0.066
final logged grad norm: 0.443
```

The corrected Stage 29 metadata gate passed for the final checkpoint:

```text
deploy_candidate: true
policy_type_pi05: PASS
model_training_dataset_matches_replay_dataset: PASS
dataset_robot_type_openarms_follower: PASS
action_names_match_folding_16d: PASS
state_names_match_folding_16d: PASS
camera_keys_and_shapes_match_space_recipe: PASS
use_relative_actions_enabled: PASS
relative_exclude_gripper_only: PASS
chunk_size_30: PASS
n_action_steps_30: PASS
rabc_recorded_in_train_config: PASS
postprocessor_action_stats_match_chunk30_relative_stats: PASS
```

Stage 31 dataset replay acceptance also passed on frames `0,1,10,30`:

```text
frame 0  model mean_abs_delta=0.408 deg, recorded mean_abs_delta=1.300 deg
frame 1  model mean_abs_delta=0.631 deg, recorded mean_abs_delta=1.156 deg
frame 10 model mean_abs_delta=2.077 deg, recorded mean_abs_delta=1.424 deg
frame 30 model mean_abs_delta=1.236 deg, recorded mean_abs_delta=1.325 deg
```

No 60-70 degree abnormal delta was observed on `right_joint_4.pos`,
`left_joint_4.pos`, `right_joint_7.pos`, or any global action dimension in the
checked replay frames. Raw normalized arm outputs were close to the normalized
recorded relative arm targets; grippers were evaluated as absolute targets
because the recipe excludes grippers from relative conversion.

Stage 31 artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage29_full_nocompile_bsz4_corrected_relstats_gate_2026-05-12.md
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/stage31_full_nocompile_bsz4_acceptance_gate_2026-05-12.md
```

A syhlabtop transfer packet and checksums were prepared:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/transfer/syhlabtop_pi05_openarm_relstats_full_004000_20260512/
```

The next required work is Stage 32 on syhlabtop:

1. Transfer only the final `004000/pretrained_model` checkpoint and audit
   packet to `/home/syhlabtop/openarm_folding_20260512`.
2. Verify the transferred checkpoint with `sha256sum -c`.
3. Run metadata and read-only hardware/camera checks.
4. Run a no-send policy snapshot only.
5. Run shadow review against the Stage 31 acceptance contract.

Robot motion remains blocked. The A6000 Stage 31 PASS does not authorize
torque enable, zeroing, actuator writes, rollout, replay-to-robot, or
`robot.send_action()`. First motion remains a separate guarded actuator-write
gate requiring explicit human approval.

## 2026-05-12 Stage 32 Architecture Correction

syhlabtop Stage 32 precheck confirmed that the real robot PC does not have the
A6000 final candidate or manifest locally. This is acceptable for the baseline
two-machine plan.

Corrected architecture:

```text
syhlabtop: robot/camera IO, read-only snapshot bundle creation
A6000: model weights, no-send inference, action review
```

The PI0.5 `model.safetensors` should not be copied to syhlabtop for the
baseline path. syhlabtop should create a fresh snapshot bundle:

```text
snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

That snapshot is then transferred to A6000 and reviewed with:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/tools/a6000_snapshot_action_review.py
```

Live split-host A6000 serving for robot control remains a separate architecture
gate because the current LeRobot rollout path does not provide an audited
remote inference transport. Until such a bridge exists and passes no-motion
tests, the approved path is snapshot-based A6000 offline review only.

Use:

```text
audits/openarm_folding/syhlabtop_a6000_served_snapshot_handoff_prompt_2026-05-12.md
```

Stage 33 is reserved for the actual remote A6000 serving bridge. The bridge is
not considered available just because the model is on A6000; it still needs a
standalone no-motion server/client path that round-trips one observation and
returns an action proposal with `send_allowed=false`.

Use:

```text
audits/openarm_folding/stage33_a6000_remote_serving_bridge_plan_2026-05-12.md
```

## 2026-05-12 Stage 32 PASS And Stage 34 Boundary

syhlabtop completed the corrected A6000-served snapshot handoff.

Result:

```text
repo_head: 388a302df024139eb92548f859fcd48182fdf77d
architecture: syhlabtop_snapshot__a6000_inference
local_model_on_syhlabtop: NO
camera_mapping: PASS
state_order_check: PASS
snapshot_bundle: CREATED
snapshot_path: /home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260512_155652
snapshot_transfer_to_a6000: DONE
a6000_review: PASS
motion_status: BLOCKED
```

A6000 no-send review:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
max_first_action_arm_delta_deg: 1.3073272705078125 at right_joint_1.pos
right_joint_4_delta_deg: 0.7648124694824219
left_joint_4_delta_deg: -0.0755462646484375
right_joint_7_delta_deg: 0.4439506530761719
```

A6000 artifacts:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260512_155652/
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.csv
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_action_review.json
```

No syhlabtop local model inference, rollout, record, replay, zeroing,
calibration write, actuator write, or `send_action` was run.

The next step is Stage 34: regenerate or parameterize the guarded first-motion
dry-run/preflight gates for `snapshot_20260512_155652`. The existing Stage
15-18 scripts are hardcoded to older `snapshot_20260511_154554` checksums and
must not be run directly against the new snapshot.

Use:

```text
audits/openarm_folding/stage32_syhlabtop_a6000_snapshot_review_2026-05-12.md
audits/openarm_folding/stage34_guarded_first_actuator_write_readiness_plan_2026-05-12.md
```

Motion remains blocked. Stage 35 actuator write requires a separate explicit
human approval of the exact command and target table.

## 2026-05-12 Stage 34 Dry-Run Blocker

Stage 34 generated a new no-motion dry-run table from
`snapshot_20260512_155652` using:

```text
audits/openarm_folding/guarded_first_motion_dry_run_v2.py
```

Output:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.json
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/shadow_replays/snapshot_20260512_155652_guarded_first_motion_dry_run.md
```

Result:

```text
send_allowed: false
motion_allowed: false
stage35_candidate_ready: false
max_abs_right_arm_candidate_delta_deg: 2.0
blocking_first_write_keys: ["right_joint_4.pos"]
```

`right_joint_4.pos` is currently the blocker. The review current value was
`-4.229 deg`, while the review limits are `[0, 135]`. With the 2 degree dry-run
cap, the target becomes `-2.229 deg`, which is still outside the review limit
range.

Stage 35 actuator write remains blocked. The next required decision is whether
the `right_joint_4.pos` limit source is correct for the current robot/readback
convention, and if so how to handle a current readback below the limit without
violating the step cap.

Use:

```text
audits/openarm_folding/stage34_guarded_first_motion_dry_run_2026-05-12.md
```

## 2026-05-12 Stage 34 Right Joint 4 Fresh Read

syhlabtop completed the read-only right-joint-4 limit check using:

```text
DamiaoMotorsBus.connect(handshake=False) + sync_read_all_states() on can1 right arm
```

Reported result:

```text
repo_head: 3420dfb3563ce8ae313464cb618107f1588232dc
snapshot_right_joint_4_deg: -4.2293176683380596
fresh_right_joint_4_deg: 8.272851356413208
right_joint_4_review_limit: [0, 135]
fresh_within_limit: true
drift_from_snapshot_deg: 12.502169024751267
torque_enabled: false
actuator_commands_sent: false
send_action_called: false
motion_status: BLOCKED
```

Interpretation:

```text
right_joint_4.pos is currently inside the [0, 135] review limit.
snapshot_20260512_155652 is stale.
snapshot_20260512_155652_action_review.* is stale.
snapshot_20260512_155652_guarded_first_motion_dry_run.* is stale.
Stage 35 actuator write remains blocked.
```

Next step:

```text
Capture a fresh Stage 32 syhlabtop snapshot, transfer it to A6000, rerun A6000
no-send review, then regenerate Stage 34 dry-run artifacts from the fresh
review outputs.
```

Use:

```text
audits/openarm_folding/stage34_right_joint4_limit_check_2026-05-12.md
audits/openarm_folding/syhlabtop_stage32_refresh_snapshot_prompt_2026-05-12.md
```

## 2026-05-12 Stage 34 Completed For Fresh Snapshot 171650

syhlabtop refreshed the stale Stage 32 snapshot and transferred the new snapshot
to A6000:

```text
snapshot_20260512_171650
```

A6000 no-send review for `snapshot_20260512_171650` passed:

```text
action_shape: [1, 30, 16]
all_finite: true
send_allowed: false
```

A6000 Stage 34 dry-run passed for no-send planning:

```text
max_abs_right_arm_candidate_delta_deg: 0.588154
right_arm_candidate_targets_within_review_limits: true
send_allowed: false
motion_allowed: false
```

syhlabtop then reported:

```text
stage34_runtime_preflight: PASS
stage34_execution_packet_no_send: CREATED
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
```

Latest syhlabtop artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_runtime_preflight.md
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.json
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_execution_packet_no_send.md
```

Stage 35 is now the next boundary, but it is actual actuator write and remains
blocked. Before any Stage 35 approval, A6000 must receive or audit the exact
Stage 34 packet files and checksums, then record the exact selected joints,
target table, max delta, operator readiness, and abort/power procedure.

Use:

```text
audits/openarm_folding/stage35_first_actuator_write_boundary_2026-05-12.md
audits/openarm_folding/syhlabtop_stage35_artifact_handoff_prompt_2026-05-12.md
```

## 2026-05-12 Stage 35 Artifact Handoff Completed

syhlabtop transferred the Stage 34 packet artifacts to A6000:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage34_packets/snapshot_20260512_171650/
```

Checksum verification matched:

```text
runtime_preflight_json_sha256: 8b3d8df7db88eb8bdfaa9975e08cef3d91e9c0769312312cd2d969666b36d920
runtime_preflight_md_sha256: 1858e09841a6b62f9d58ccba15f59ed913eb3339fe67939d14da000f972a6c59
execution_packet_json_sha256: c5411331665ea5b31a9d85de4adf27ce74f0c9596630c4cc8481e6afd58ec259
execution_packet_md_sha256: 43c4ec4464caaaf31b0c6a92e0e4d7446f8edd0fb56c6596c509de2fd2aaa6ee
```

Exact selected joints are the seven right-arm joints only. Expected maximum
delta is:

```text
0.5881538391113281 deg
```

Stage 35 remains blocked:

```text
stage35_no_execute_validator: READY
stage35_a6000_packet_only_validation: PASS
stage35_actual_writer: NOT_READY
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

Next no-motion step:

```text
audits/openarm_folding/syhlabtop_stage35_no_execute_validation_prompt_2026-05-12.md
```

## 2026-05-12 Stage 35 No-Execute Validation Completed

syhlabtop ran the Stage 35 no-execute validator with fresh read-only right-arm
CAN readback for `snapshot_20260512_171650`.

Result:

```text
packet_validation_passed: true
fresh_readback_validation_passed: true
max_abs_right_arm_candidate_delta_deg: 0.5881538391113281
max_abs_fresh_drift_deg: 0.02185693518331755
max_abs_target_delta_from_fresh_deg: 0.5881540488490593
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
execute_path_available: false
operator_motion_approval: NOT_GIVEN
actual_writer_status: NOT_READY
motion_status: BLOCKED
```

Outputs:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.json
sha256: f16c0262cc7f028caa8a6a552015d4ff7e691b9bec57a509b33ef585be4bcd4d

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_no_execute_validation.md
sha256: 772033040723eb488c58ab6249c022e3e96f7a8479bdf0fde730ad7cb0f8f0d5
```

The outputs were transferred to A6000 and checksums matched:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_no_execute_validation/snapshot_20260512_171650/
```

New audit record:

```text
audits/openarm_folding/stage35_syhlabtop_no_execute_validation_result_2026-05-12.md
```

Stage 35 actual actuator write remains blocked. The next allowed work is an
A6000 audit update and a separate operator approval draft; this is not motion
approval.

## 2026-05-12 Stage 35 Actual Writer Prepared

The Stage 35 guarded actual writer was created for the approved
`snapshot_20260512_171650` packet:

```text
audits/openarm_folding/stage35_guarded_actual_actuator_write.py
audits/openarm_folding/stage35_guarded_actual_actuator_write_2026-05-12.md
audits/openarm_folding/stage35_operator_motion_approval_draft_2026-05-12.md
```

syhlabtop ran the writer without `--execute`.

Result:

```text
packet_validation_passed: true
fresh_target_validation_passed: true
execute_requested: false
operator_motion_approval: NOT_GIVEN
send_allowed: false
motion_allowed: false
execution_allowed: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_fresh_drift_deg: 0.0000003661177974123575
max_abs_target_delta_from_fresh_deg: 0.5881540488490593
```

Outputs:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.json
sha256: 4812a9f5479ca3ae9c043a1927b299ef3a776f8ef2f4c6bed2bd0dda6a64b7c2

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_writer_ready_no_send.md
sha256: fca9c238457bb7d307fd17e7cd131fcb1cc1e34127a8feed3cf7bc2f3118d3d8
```

The outputs were transferred to A6000 and checksums matched:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_actual_writer_ready/snapshot_20260512_171650/
```

Negative execute-gate check rejected `--execute` without the required operator
approval, operator-at-robot, power-held, abort-ready, e-stop-ready, and exact
confirmation phrase flags.

Current boundary:

```text
stage35_actual_writer: PREPARED_NOT_EXECUTED
stage35_actual_writer_ready_no_send: PASS
operator_motion_approval: NOT_GIVEN
motion_status: BLOCKED
```

## 2026-05-12 Stage 35 Single Write Attempt Completed

The operator explicitly approved the exact Stage 35 command and confirmation
phrase in the live session. syhlabtop executed one guarded right-arm joint
write.

Result:

```text
packet_validation_passed: true
fresh_target_validation_passed: true
execute_requested: true
operator_motion_approval: GIVEN
send_allowed: true
motion_allowed: true
execution_allowed: true
actuator_commands_sent: true
motion_status: SINGLE_WRITE_ATTEMPTED
errors: []
max_abs_final_target_error_deg: 0.36750044908878676
```

Artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_write_attempt.json
sha256: 2b48d21086fa69da9b5d7828668b9575c7a3e12786c31716965add6982065154

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_actual_write_attempt.md
sha256: fcb0fd677ffb9321ed5c0b6953dff42509eecae5d7ad4c67c003d370d24c0619
```

Post-write readback was then run without `--execute`, and no additional
actuator command was sent:

```text
fresh_target_validation_passed: true
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
max_abs_drift_from_packet_current_deg: 0.6119940781871565
max_abs_target_delta_from_current_deg: 0.38935738794324726
```

Post-write artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_post_write_readback.json
sha256: cc59ed768aaa055ba885b3d2b2a3a50f7bfbd1548e554829fbcfcf0d9b5ca4d5

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_171650_stage35_post_write_readback.md
sha256: 1d35caa17a17dcf24fa581726cd36eaf18277da6c7881122cf811be32a06bfed
```

The attempt and post-write readback artifacts were transferred to A6000 and
checksums matched:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage35_actual_write_attempt/snapshot_20260512_171650/
```

Current boundary:

```text
stage35_single_write_attempt: DONE
stage35_post_write_readback: PASS
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```

## 2026-05-12 Stage 36 A6000 Serving Bridge

A no-send HTTP bridge was added and started on A6000. The server loads the
corrected trained checkpoint and accepts snapshot directory references under
the A6000 snapshot root.

```text
server_url: http://10.252.205.103:8765/predict_snapshot
server_pid: 2702819
model_dir: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model
health: ok
```

syhlabtop captured a fresh post-Stage35 snapshot:

```text
snapshot: snapshot_20260512_194042
local_path: /home/syhlabtop/openarm_folding_20260512/shadow_snapshots/snapshot_20260512_194042/
a6000_path: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_snapshots/snapshot_20260512_194042/
```

The A6000 service returned one no-send action proposal:

```text
all_finite: true
action_shape: [1, 30, 16]
max_abs_arm_delta_deg: 2.1111412048339844
right_joint_4_delta_deg: 1.211517333984375
left_joint_4_delta_deg: -1.4297370910644531
right_joint_7_delta_deg: 2.1111412048339844
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

The proposal artifacts were copied to A6000 and checksums matched:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage36_served_proposals/snapshot_20260512_194042/
```

The operator stated that robot movement is approved, but the exact proposal
target table was generated after that statement. A separate exact-table
confirmation is still required before any next actuator write.

Current boundary:

```text
stage36_a6000_serving_bridge: PASS
stage37_motion_approval: NOT_GIVEN_FOR_EXACT_TABLE
stage37_actual_writer: NOT_CREATED
motion_status: BLOCKED_PENDING_EXACT_TARGET_CONFIRMATION
```

## 2026-05-12 Stage 37 Served Proposal Single Write

The operator gave explicit approval for the exact Stage 37 target table and
confirmation phrase:

```text
operator_at_robot: true
power_abort_control_held: true
estop_ready: true
right_arm_workspace_clear: true
human_body_clear_of_arm: true
approval_applies_to_exact_stage37_target_table: true
approval_phrase: SEND_STAGE37_RIGHT_ARM_SERVED_PROPOSAL_ONCE_20260512_194042
```

The Stage 37 guarded writer was added and validated the A6000 served proposal
checksum before any actuator command:

```text
writer: audits/openarm_folding/stage37_guarded_served_proposal_write.py
proposal_sha256: 498fef8a4467e04ad7a5e01279f484dee7c76a17365e0c5ee12dd3d4e21eb5da
no_execute_validation: PASS
fresh_target_validation_passed: true
```

One right-arm-only guarded write was executed. Left arm, right gripper, and left
gripper remained excluded. No rollout, recording, replay-to-robot,
`send_action`, local PI0.5 inference, zeroing, or calibration write was run.

```text
proposal_validation_passed: true
fresh_target_validation_passed: true
execute_requested: true
operator_motion_approval: GIVEN
send_allowed: true
motion_allowed: true
execution_allowed: true
actuator_commands_sent: true
motion_status: SINGLE_WRITE_ATTEMPTED
errors: []
```

Artifacts:

```text
/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_ready_no_send.json
sha256: f34a0a1d9c4f805b8aeb0c702678f3a24738f5513545cbebc0dae3f0d41ff5f8

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_actual_write_attempt.json
sha256: f30e19372e6195cb2b0cee36f8c7eddb4e457098968a7cb2e1f436530e8e20b0

/home/syhlabtop/openarm_folding_20260512/shadow_reviews/snapshot_20260512_194042_stage37_post_write_readback.json
sha256: 138114716c25002c23cb18cdf39ce54b40140995b41e311dd16c5ff12ace09f6
```

A6000 handoff path:

```text
/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/syhlabtop_stage37_served_proposal_write/snapshot_20260512_194042/
```

The A6000 copies matched syhlabtop checksums.

Actual write final readback:

```text
max_abs_target_delta_from_fresh_deg: 2.0
max_abs_final_target_error_deg: 0.36498359171830963
```

Independent post-write no-execute readback:

```text
execute_requested: false
actuator_commands_sent: false
motion_status: BLOCKED
fresh_target_validation_passed: false
errors: ["fresh_target_validation_failed: ['right_joint_5.pos', 'right_joint_7.pos']"]
max_abs_remaining_to_target_deg: 0.8836636219154279
max_abs_drift_from_proposal_current_deg: 1.48627162345538
```

The post-write readback failed the pre-write freshness gate because the arm had
moved from the proposal-current pose. This blocks reuse of the same proposal.

Current boundary:

```text
stage37_single_write_attempt: DONE
stage37_post_write_readback: RECORDED_PREWRITE_GATE_EXPECTED_FAIL
next_motion_approval: NOT_GIVEN
motion_status: BLOCKED_FOR_REVIEW
```
