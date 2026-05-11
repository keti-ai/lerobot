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
Stage 5  syhlabtop repo/handoff readiness            PARTIAL
Stage 6  syhlabtop camera mapping                    NOT DONE
Stage 7  syhlabtop CAN/calibration mapping           NOT DONE
Stage 8  syhlabtop no-send observation snapshot      NOT DONE
Stage 9  A6000 snapshot action review                BLOCKED
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

Committed and pushed:

```text
faa94c4b docs: add OpenArm folding baseline audit
65de9226 docs: prepare syhlabtop shadow readiness handoff
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

`syhlabtop` still needs to confirm the same NAS mount. If it is not mounted, use local syhlabtop storage and transfer snapshots manually.

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

## Blockers Before A6000 Shadow Action Review

- Need syhlabtop NAS mount status.
- Need selected syhlabtop work root.
- Need camera mapping for `left_wrist`, `right_wrist`, `base`.
- Need CAN interface and calibration mapping.
- Need exact 16-dim state snapshot in degrees.
- Need metadata with `send_allowed=false`.

## Motion Gate

Motion remains blocked. The next acceptable milestone is no-send snapshot capture and offline A6000 review only.
