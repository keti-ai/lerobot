# Open Arms Mini Bambu Print Plan

Date: 2026-05-12
Scope: `pkooij/open-arms-mini` only
Source: https://github.com/pkooij/open-arms-mini
Pinned HEAD: `0628e081cfe105dc4156dba5099c2274c4aca2e8`

This plan supersedes the broader OpenArm leader/end-effector plan for the current work. Build the Mini first.

## Build Target

Priority target: one complete pair of Open Arms Mini leader arms.

Repository guidance:

- Complete pair: 32 printed parts, 16 per arm.
- Recommended material: PLA or PETG.
- Recommended layer height: 0.2 mm.
- Recommended infill: 20-40%.
- Recommended nozzle: 0.4 mm.
- Supports: yes, where needed.
- Approximate filament: 150-200 g per arm, 300-400 g per pair.

Count note: the repo README also lists `WaveShare_Mounting_Plate_SO101 v1.stl` as a shared controller plate. Counting every listed STL quantity plus that shared plate gives one additional shared item, so track it separately from the 32 arm parts.

## Printer Split

Use P1S and X1 Carbon only.

| Printer | Role | Reason |
| --- | --- | --- |
| X1 Carbon | accuracy-critical joints, wrist/handle parts | better monitoring and preferred for core structural parts |
| P1S | duplicate universal parts, gripper parts, WaveShare plate, optional camera mount | good throughput for PETG/PLA parts |

Do not use A1 mini for the priority batch.

## Material Decision

First pass: PETG HF or PETG Basic.

Reason: the Mini is hand-driven and low-inertia, but the wrist strap holder, handle, and motor holders see repeated tightening and hand load. PETG is a better first default than PLA if the arm will be used for long teleop sessions.

Fallback:

- Use PLA only for quick geometry checks or non-load parts.
- Use PETG-CF only after dry-fit, and only if a part flexes or wears. Keep abrasive filament on X1C unless P1S has hardened nozzle and hardened gear installed.

## Batch Order

Detailed calendar scheduling is tracked in:

- `audits/openarm_printing/open_arms_mini/mini_bambu_timeline_2026-05-12.md`
- `audits/openarm_printing/open_arms_mini/mini_bambu_timeline_2026-05-12.tsv`

### Batch 0: Intake

Clone or download:

```bash
git clone https://github.com/pkooij/open-arms-mini.git /home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini
```

Then verify:

```bash
git -C /home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini rev-parse HEAD
find /home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini/STL -maxdepth 1 -type f -iname '*.stl' | sort
```

### Batch 1: Core Joint Pair

X1C:

- `J1 v5.stl`, qty 2
- `J2 v2.stl`, qty 2
- `J3 v2.stl`, qty 2
- `J4 v3.stl`, qty 2
- `J5 v4.stl`, qty 2
- `J6 v6.stl`, qty 2
- `J7 v4.stl`, qty 2

P1S:

- `J1_holder v1.stl`, qty 2
- `J2_holder v1.stl`, qty 2
- `J4_holder v1.stl`, qty 2
- `J7_holder v1.stl`, qty 2

Gate:

- Visual inspection only before moving to the next plate.
- Full servo dry-fit happens after all major parts are printed.

### Batch 2: Wrist, Handle, Gripper

X1C:

- `J6 holder with strap v4.stl`, qty 2
- `J Handle v12.stl`, qty 2

P1S:

- `J8 L v4.stl`
- `J8 R v10.stl`
- `J8 holder L v2.stl`
- `J8 holder R v6.stl`
- `J trigger L v2.stl`
- `J trigger R v2.stl`

Gate:

- Strap passes cleanly through holder.
- Handle has no sharp support scars.
- Gripper trigger moves without rubbing after motor installation.

### Batch 3: Controller / Optional Mount

P1S:

- `WaveShare_Mounting_Plate_SO101 v1.stl`, qty 1
- `arducam_holder v6.stl`, optional

## Bambu Studio Profile

Use these as starting points. If the printed parts look over-tight during assembly, update compensation for any reprints.

X1C structural PETG:

- Machine: `Bambu Lab X1 Carbon 0.4 nozzle`
- Layer: 0.20 mm
- Walls: 4-5
- Infill: 35-40%, gyroid or cubic
- Top/bottom: 5 layers
- Supports: tree/manual where needed
- Brim: on for narrow/tall joints

P1S PETG:

- Machine: `Bambu Lab P1S 0.4 nozzle`
- Layer: 0.20 mm
- Walls: 4
- Infill: 30-40%
- Supports: on only where overhangs require it
- Brim: on for holders and triggers if bed contact is small

For handle and wrist strap holder:

- Walls: 5
- Infill: 40%
- Seam: place away from palm/strap contact faces
- Post-process support scars before use

## Assembly Prep

Per arm required hardware from BOM:

- 8x Feetech STS3215-C046 servo
- 1x Waveshare Serial Bus Servo Driver Board
- about 35x M2x6 screws
- about 35x M3x6 screws
- 8x M3x6 horn screws, typically included with motors
- 8x 3-pin servo cables, 150-200 mm
- 1x 7.5 V DC power supply, 2 A minimum
- 1x elastic velcro wrist strap, about 25 mm wide

Configure motor IDs before final assembly.

| ID | Joint | Printed part |
| ---: | --- | --- |
| 1 | Shoulder Pan | J1 |
| 2 | Shoulder Lift | J2 |
| 3 | Shoulder Roll | J3 |
| 4 | Elbow Flex | J4 |
| 5 | Forearm Rotation | J5 |
| 6 | Wrist Flex | J6 |
| 7 | Wrist Roll | J7 |
| 8 | Gripper | J8 L/R |

## Stop Conditions

Stop and reslice/reprint if:

- Servo insertion requires force that bows the printed part.
- M2 screw bosses whiten or crack.
- Horn alignment is off after tightening.
- Wrist strap holder edges are sharp or delaminate.
- Gripper trigger does not return freely.
- Any joint has visible layer separation after hand-load testing.

## Current Next Action

1. Open the local STL folder in Bambu Studio:
   `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini/STL`
2. Start the main pair batch:
   X1C core joints pair and P1S holder pair.
3. Replace estimated plate durations with Bambu Studio slice results in the timeline TSV.
