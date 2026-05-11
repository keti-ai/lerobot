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
Stage 19 first actuator write execution              OPERATOR GATED
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
```

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

## Motion Gate

Motion remains blocked. A6000 has produced offline action proposals only; no
policy output has been sent to robot actuators. The only hardware write after
the original no-send pipeline was the operator-approved gripper-only zero on
motor ID `008` for `can0` and `can1`. Stage 15 defined a dry-run target table
only, Stage 16 verified current readback without command writes, and Stage 17
built a no-send execution packet. Stage 18 now has a guarded right-arm writer
and its dry-run validation passed, but actual execution remains blocked until
the operator explicitly runs the execute command while holding power/abort.
