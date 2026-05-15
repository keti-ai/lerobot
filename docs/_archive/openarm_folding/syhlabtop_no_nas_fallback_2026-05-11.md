# Syhlabtop No-NAS Fallback

Date: 2026-05-11
Machine: `syhlabtop`

## Confirmed State

From the live syhlabtop session:

```text
repo: /home/syhlabtop/workspace/lerobot
branch: audit/openarm-folding-baseline
HEAD observed during no-NAS check: f4476842
/mnt/nas/lerobot_shared: not mounted
/data: not present
/: /dev/nvme0n1p2, 468G total, 131G available
```

## What This Means

Important docs are not blocked by NAS. They are in the repository:

```text
/home/syhlabtop/workspace/lerobot/audits/openarm_folding/
```

NAS was only a convenient handoff path for snapshots and review files. Since NAS is absent on syhlabtop, use local syhlabtop storage first.

## Work Root

Use:

```text
/home/syhlabtop/openarm_folding_20260511
```

Create:

```text
/home/syhlabtop/openarm_folding_20260511/audits
/home/syhlabtop/openarm_folding_20260511/camera_maps
/home/syhlabtop/openarm_folding_20260511/hardware/openarm
/home/syhlabtop/openarm_folding_20260511/calibration
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots
/home/syhlabtop/openarm_folding_20260511/shadow_reviews
/home/syhlabtop/openarm_folding_20260511/safety_configs
```

The `mkdir -p` command for these directories is non-actuating and safe. It does not touch robot IO.

## Snapshot Location

If a no-send snapshot is created, keep it local:

```text
/home/syhlabtop/openarm_folding_20260511/shadow_snapshots/snapshot_YYYYMMDD_HHMMSS/
```

Required contents:

```text
state_16.csv
left_wrist.png
right_wrist.png
base.png
metadata.json
```

`metadata.json` must include:

```json
{
  "send_allowed": false,
  "motion_allowed": false,
  "transfer_status": "local_only_no_nas"
}
```

## Transfer Status

A6000 shadow action review remains blocked until the snapshot reaches A6000.

Allowed next transfer choices, only after operator approval:

- mount NAS on syhlabtop,
- `scp` or `rsync` the snapshot from syhlabtop to A6000,
- copy via another approved removable or network path.

Do not improvise a transfer command from inside the robot session without explicit approval.

## Safety Line

No NAS does not change the safety rule:

- no `robot.send_action()`,
- no rollout/record/replay,
- no policy output to robot,
- no robot motion.
