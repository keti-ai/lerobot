# Bambu Project Status

Date: 2026-05-12

Checked folder:

- `/home/syhlabtop/workspace/lerobot/audits/openarm_printing/open_arms_mini/source/open-arms-mini/bambu_proj`

## Projects Found

| File | Modified | Contents | Intended printer | Status |
| --- | --- | --- | --- | --- |
| `J1_7.3mf` | 2026-05-12 16:05 | `J1`, `J2`, `J3`, `J4`, `J5`, `J6`, `J7` x1 each | X1 | completed first copy |
| `J1_hol_J7_hol_J8LR.3mf` | 2026-05-12 16:08 | `J1_holder`, `J2_holder`, `J4_holder`, `J7_holder` x2 each; `J8 L`, `J8 R` | P1S | completed |

## Remaining Critical Prints

| Printer | Parts |
| --- | --- |
| X1 | second copy of `J1`-`J7`; `J6 holder with strap` x2; `J Handle` x2 |
| P1S | `J8 holder L`, `J8 holder R`, `J trigger L`, `J trigger R`; `WaveShare_Mounting_Plate_SO101`; optional `arducam_holder`; optional trigger spares |

## Metadata Note

The two `.3mf` files currently store Bambu Studio metadata as:

- printer profile: `Bambu Lab X1 Carbon 0.4 nozzle`
- process profile: `0.20mm Standard @BBL X1C`
- layer height: `0.2`
- sparse infill: `15%`
- wall loops: `2`
- filament profile: `Bambu PLA Basic @BBL X1C`

If `J1_hol_J7_hol_J8LR.3mf` was sent to P1S after switching machines inside Bambu Studio, the printer-side job may still be correct. Before reusing the file later, reopen it and confirm the active machine/filament profile.
