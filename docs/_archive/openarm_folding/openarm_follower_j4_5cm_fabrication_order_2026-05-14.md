# OpenArm Follower J4 +5 cm Fabrication Order

Date: 2026-05-14

## Source File

Metal/CNC candidate:

- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/J4_5cm_extended.step`

Related printed covers:

- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/J3-J4_Cover_front_extended.stl`
- `/home/syhlabtop/openarm_folding_20260511/hardware_modifications/J3-J4_Cover_back_extended.stl`

The hardware modification README describes `J4_5cm_extended.step` as the extended upper arm/bicep segment that adds +5 cm of reach.

## Required Quantity

For bimanual follower deployment:

| Part | Required | Practical order |
| --- | ---: | ---: |
| `J4_5cm_extended.step` metal part | 2 | 3 if one spare is affordable; 4 if setup cost dominates |
| `J3-J4_Cover_front_extended.stl` printed cover | 2 | 2-3 |
| `J3-J4_Cover_back_extended.stl` printed cover | 2 | 2-3 |

Reason: each follower arm needs one extended J4 upper-arm segment. A bimanual follower has left and right arms, so the installed count is 2.

Clarification: the official J3-J4 assembly has both `J4_A` and `J4_B`, but the local extended STEP identifies itself as `J4_A v3`. Do not count `J4_A` plus `J4_B` as two copies of `J4_5cm_extended.step` unless the fabricator or CAD review confirms that the extended design requires a second mirrored/paired metal part.

## Order Notes

- Use the same `J4_5cm_extended.step` file for the required pair unless the fabricator confirms a true left/right mirrored requirement from the assembly.
- Do not let the fabricator mirror one copy automatically without confirmation.
- Ask for material, heat treatment, surface finish, thread/tap, and tolerance assumptions to be listed explicitly in the quotation.
- Keep the original standard J4 parts until the extended pair has been installed and checked.
