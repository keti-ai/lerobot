# OpenArm Mini / Leader Teleop Bambu Print Plan

Date: 2026-05-12

## Printer Scope

Use only the Bambu Lab P1S and Bambu Lab X1 Carbon for this run.

Observed from Bambu Studio config:

- X1 Carbon profile: `BL-P001`
- P1S profile: `C12`
- Last selected machine in Bambu Studio: `01P...0836`, mapped to P1S class in local config

## Current Local CAD State

Official OpenArm hardware repo is present at:

- `/home/syhlabtop/workspace/openarm_hardware`

That repo currently contains Google Drive file IDs, not downloaded STL payloads. The STL list needed for leader teleop is in:

- `/home/syhlabtop/workspace/openarm_hardware/dev/google-drive-files/file-ids.tsv`

Already-local custom printable files:

- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/J3-J4_Cover_front_extended.stl`
- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/J3-J4_Cover_back_extended.stl`
- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/arducam_holder.stl`
- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/head_camera_holder_v4.stl`
- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/jaw_normal.stl`

## Required Official STL Pull List

Leader end-effector:

| Part | Qty | Source path in file-ids.tsv | Printer |
| --- | ---: | --- | --- |
| Rail Connector (Leader) | 2 | `STL (3d print)/Leader Gripper/rail-connector-leader.STL` | X1C |
| Swivel Rotor (Leader) | 2 | `STL (3d print)/Leader Gripper/swivel-rotor-leader.STL` | X1C |
| Swivel Link (Leader) | 4 | `STL (3d print)/Leader Gripper/swivel-link-leader.STL` | P1S |
| Right Pincer | 2 | `STL (3d print)/Leader Gripper/right-pincer.STL` | P1S |
| Left Pincer | 2 | `STL (3d print)/Leader Gripper/left-pincer.STL` | P1S |

Leader casing / arm covers:

| Part | Qty | Source path in file-ids.tsv | Printer |
| --- | ---: | --- | --- |
| `J4-J5_Cover_Leader_B.STL` | 1 | `STL (3d print)/Casing/J4-J5_Cover_Leader_B.STL` | P1S |
| `J4-J5_Cover_A.STL` | 1 | `STL (3d print)/Casing/J4-J5_Cover_A.STL` | P1S |
| `J3-J4_Cover_A.STL` | 1 | `STL (3d print)/Casing/J3-J4_Cover_A.STL` | P1S |
| `J3-J4_Cover_B.STL` | 1 | `STL (3d print)/Casing/J3-J4_Cover_B.STL` | P1S |
| `J2-J3_Cover_A.STL` | 1 | `STL (3d print)/Casing/J2-J3_Cover_A.STL` | P1S |
| `J2-J3_Cover_B.STL` | 1 | `STL (3d print)/Casing/J2-J3_Cover_B.STL` | P1S |
| `J1-J2_Cover_A.STL` | 1 | `STL (3d print)/Casing/J1-J2_Cover_A.STL` | P1S |
| `J1-J2_Cover_B.STL` | 1 | `STL (3d print)/Casing/J1-J2_Cover_B.STL` | P1S |

Optional attachments:

| Part | Use | Printer |
| --- | --- | --- |
| `pcb-hub_base.stl` | hub mount | P1S |
| `wrist-camera_base.stl` | camera mount base | P1S |
| `wrist-camera_D405.stl` | D405 camera mount | P1S |
| `chest-camera_D435.stl` | D435 camera mount | P1S |

## Material Assignment

Use PETG first for fit validation.

| Part class | First pass | Final pass if needed | Printer |
| --- | --- | --- | --- |
| Rail connector, swivel rotor | PETG HF / PETG Basic | PETG-CF or PAHT-CF | X1C |
| Swivel links, pincers | PETG HF / PETG Basic | PETG-CF only if flex/wear appears | P1S or X1C |
| Covers and camera mounts | PETG HF / PETG Basic | PETG | P1S |
| Custom jaw | PETG | PETG-CF if grip face deforms | P1S |

Do not start with PAHT-CF for all parts. Print one PETG validation set, dry-fit, then reprint only load-sensitive or wear-sensitive parts.

## Bambu Studio Profiles

X1 Carbon structural profile:

- Machine: `Bambu Lab X1 Carbon 0.4 nozzle`
- Process: `0.20mm Strength @BBL X1C`
- Filament: Bambu PETG HF or PETG Basic for validation
- Walls: 5-6
- Infill: 45-60%, gyroid or cubic
- Top/bottom shells: 5-7
- Brim: on for long/thin parts
- Supports: manual only, avoid support contact on bearing or bolt reference faces

P1S cover/small-part profile:

- Machine: `Bambu Lab P1S 0.4 nozzle`
- Process: `0.20mm Standard @BBL X1C/P1S` for covers, `0.16mm High Quality` for small linkage parts
- Filament: PETG HF or PETG Basic
- Walls: 4 for covers, 5 for links/pincers
- Infill: 25-35% for covers, 40-50% for links/pincers
- Brim: on for thin covers

If printing abrasive filament on P1S, confirm hardened nozzle and hardened extruder gear first. Otherwise keep abrasive filament on X1C.

## Execution Queue

### Batch 0: Download and Intake

- Download official STL files from the Google Drive IDs listed in `file-ids.tsv`.
- Place files under `/home/syhlabtop/workspace/openarm_printing/intake/openarm_official_stl/`.
- Preserve original filenames.
- Record source file ID beside each downloaded file.

### Batch 1: Fit Coupons

Printer: P1S

- M3 clearance coupon
- M4 clearance coupon
- heat-set insert coupon, if inserts are used
- bearing/shaft pocket coupon, if applicable to the downloaded leader files

Decision gate:

- If holes are tight, compensate in Bambu Studio XY hole compensation before printing the full set.

### Batch 2: Leader End-Effector Validation

X1C:

- `rail-connector-leader.STL`, qty 2
- `swivel-rotor-leader.STL`, qty 2

P1S:

- `swivel-link-leader.STL`, qty 4
- `right-pincer.STL`, qty 2
- `left-pincer.STL`, qty 2

Inspection gate:

- No layer separation at pin/bolt holes.
- Pincers are symmetric after tightening.
- Swivel parts rotate freely without visible slop.

### Batch 3: Covers and Attachments

P1S:

- Official leader casing covers listed above
- `pcb-hub_base.stl`, if hub mount is needed
- camera mounts only if cameras are part of this teleop station

Use local custom parts only if the physical build needs the cloth-folding modifications:

- `J3-J4_Cover_front_extended.stl`
- `J3-J4_Cover_back_extended.stl`
- `head_camera_holder_v4.stl`
- `arducam_holder.stl`
- `jaw_normal.stl`

### Batch 4: Final Reprint

Only after dry-fit:

- Reprint high-wear leader gripper parts on X1C with PETG-CF or PAHT-CF if PETG is too flexible.
- Keep covers in PETG unless heat or impact damage appears.

## Acceptance Checklist

- [ ] All official STL files downloaded and source IDs recorded.
- [ ] Bambu Studio project created for X1C structural batch.
- [ ] Bambu Studio project created for P1S small/casing batch.
- [ ] Fit coupons printed and measured.
- [ ] End-effector PETG validation set printed.
- [ ] Dry-fit completed before any CF reprint.
- [ ] All sharp support scars removed from hand-contact surfaces.
- [ ] Cables clear joint rotation range.
- [ ] Printed parts bagged and labeled by assembly stage.

## Stop Conditions

Stop and re-slice before continuing if any of these appear:

- Rail connector holes crack during screw insertion.
- Swivel rotor/link binds after tightening.
- Pincer tips are visibly asymmetric.
- Covers require force that bends the arm or cable path.
- PETG part softens near motor or electronics heat during bench test.
