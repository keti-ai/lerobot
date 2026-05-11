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
Stage 5  syhlabtop repo/storage readiness            PARTIAL
Stage 6  syhlabtop camera mapping                    NOT DONE
Stage 7  syhlabtop CAN/calibration mapping           NOT DONE
Stage 8  syhlabtop no-send observation snapshot      NOT DONE
Stage 9  A6000 snapshot action review                BLOCKED ON TRANSFER
Stage 10 syhlabtop human/safety review               BLOCKED
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

## Next Required Output from Syhlabtop

Minimum no-motion output:

```text
<syhlabtop-work-root>/audits/2026-05-11_preflight_syhlabtop.md
<syhlabtop-work-root>/camera_maps/...
<syhlabtop-work-root>/hardware/openarm/...
<syhlabtop-work-root>/calibration/...
```

Target snapshot output, only after operator approves non-actuating robot IO:

```text
snapshot_YYYYMMDD_HHMMSS/
  state_16.csv
  left_wrist.png
  right_wrist.png
  base.png
  metadata.json
```

If NAS is mounted on syhlabtop, copy snapshots to:

```text
/mnt/nas/lerobot_shared/openarm_folding_20260511/syhlabtop_snapshots/
```

Current syhlabtop status says NAS is not mounted. Until that changes, the snapshot remains local under:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/
```

Then use an explicit operator-approved transfer method to A6000. Do not improvise a transfer command inside the robot session.

## Blockers Before A6000 Shadow Action Review

- NAS is not mounted on syhlabtop; need transfer method after local snapshot.
- Selected syhlabtop work root should be `/home/syhlabtop/openarm_folding_20260511`.
- Need camera mapping for `left_wrist`, `right_wrist`, `base`.
- Need CAN interface and calibration mapping.
- Need exact 16-dim state snapshot in degrees.
- Need metadata with `send_allowed=false`.

## Motion Gate

Motion remains blocked. The next acceptable milestone is no-send snapshot capture and offline A6000 review only.
