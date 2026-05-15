# Open Arms Mini Print Timeline

Date: 2026-05-12
Printers: Bambu Lab P1S, Bambu Lab X1 Carbon
Material baseline: PETG HF / PETG Basic, 0.4 mm nozzle, 0.20 mm layer

This is a planning timeline before final Bambu Studio slicing. Replace estimated durations with slicer output after each plate is arranged.

## Assumptions

- Build target: one complete pair.
- Print count: 32 arm parts plus 1 shared WaveShare plate.
- Optional `arducam_holder v6.stl` is not in the critical path.
- Fit check is skipped because prior local printing already produced acceptable fit.
- PETG print speed is kept conservative enough for dimensional reliability.

## Estimated Duration Summary

| Phase | Wall-clock estimate | Human work | Gate |
| --- | ---: | ---: | --- |
| Core joints pair | 6-8 h | 20-30 min | visual check |
| Holders and gripper set | 4-6 h | 20-30 min | visual check |
| Wrist/handle pair | 5-7 h | 30-45 min | strap and palm-surface check |
| Controller plate and spares | 1-3 h | 10-20 min | board mount fit |
| Total active print time | 12-18 h | 1.5-2.5 h | assembly-ready parts |

Practical calendar: 1 long day, or overnight if starting late.

## Calendar Plan

### Day 1 Morning: Main Parallel Start

| Time block | Printer | Plate | Files | Estimate |
| --- | --- | --- | --- | ---: |
| 09:00-16:00 | X1C | Core joints pair | `J1`, `J2`, `J3`, `J4`, `J5`, `J6`, `J7` x2 each | 6-8 h |
| 09:00-14:00 | P1S | Holders pair | `J1_holder`, `J2_holder`, `J4_holder`, `J7_holder` x2 each | 4-5 h |

Quick check at completion:

- Confirm no obvious warping or layer separation.
- Confirm screw bosses are clean and not buried by support.
- Remove only the worst support scars before later assembly.

### Day 1 Afternoon/Evening: Wrist, Handle, Gripper

| Time block | Printer | Plate | Files | Estimate |
| --- | --- | --- | --- | ---: |
| 16:30-22:30 | X1C | Hand load pair | `J6 holder with strap` x2, `J Handle` x2 | 5-7 h |
| 14:30-18:30 | P1S | Gripper and triggers | `J8 L`, `J8 R`, `J8 holder L`, `J8 holder R`, `J trigger L`, `J trigger R` | 3-4.5 h |

Quick check:

- Remove support scars from handle and strap path.
- Confirm strap slides without cutting/fraying.
- Confirm gripper trigger returns freely.

### Day 1 Evening or Day 2 Morning: Shared Plate and Spares

| Time block | Printer | Plate | Files | Estimate |
| --- | --- | --- | --- | ---: |
| 19:00-21:00 | P1S | Controller | `WaveShare_Mounting_Plate_SO101` x1 | 1-2 h |
| 21:00-23:00 | P1S | Spares | highest-risk small parts: `J trigger L/R`, one holder, optional `arducam_holder` | 1-3 h |

### Final Inspection

| Time block | Work | Estimate |
| --- | --- | ---: |
| next available block | deburr, remove support scars, label parts | 1 h |
| next available block | servo dry-fit, screw/horn check, cable path check | 1-1.5 h |
| next available block | update manifest statuses and reprint list | 30 min |

## Plate Strategy

### X1C Plates

| Plate | Files | Purpose |
| --- | --- | --- |
| X1C-A | `J1`-`J7` x2 each | pair core joints |
| X1C-B | `J6 holder with strap` x2, `J Handle` x2 | pair hand-load parts |

### P1S Plates

| Plate | Files | Purpose |
| --- | --- | --- |
| P1S-A | `J1_holder`, `J2_holder`, `J4_holder`, `J7_holder` x2 each | pair holders |
| P1S-B | `J8 L/R`, `J8 holder L/R`, `J trigger L/R` | gripper set |
| P1S-C | `WaveShare_Mounting_Plate_SO101`, spares, optional camera mount | shared and spare parts |

## Priority If Time Is Tight

1. Core joints pair.
2. Holders pair.
3. Handle/strap holder pair.
4. Gripper set.
5. Shared WaveShare plate.
6. Optional camera mount and spares.

## What To Update After Slicing

For each plate, record:

- Bambu Studio estimated print time.
- Filament grams.
- Support material grams.
- Plate name and printer.
- Any orientation/support changes.

Use the TSV timeline file beside this document for tracking.
