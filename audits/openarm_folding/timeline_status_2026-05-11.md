# OpenArm Folding Timeline Status

Date: 2026-05-11
Task: LeRobot OpenArm folding baseline, no-motion/shadow readiness.

## Current Position in the Timeline

We are between pipeline Stage 4 and Stage 5:

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
Stage 10 syhlabtop human/safety review               IN PROGRESS
Stage 11 summary and next blocker list               NOT DONE
```

The next real-machine work is on `syhlabtop`. The objective is not motion. The objective is to prove that the robot PC can collect a correctly ordered observation snapshot without sending any policy output to motors.

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

## Motion Gate

Motion remains blocked. A6000 has produced an offline action proposal only; no
policy output has been sent to robot actuators.
