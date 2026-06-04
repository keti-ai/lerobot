# A6000 handover_v0 clean relstats transform (A2)

마지막 갱신: 2026-06-05T00:20:00+09:00

## 1. 변환 입력

- source repo id: `KETI-IRRC/openarm_handover_v0_20260521_202117_clean`
- source HF snapshot: `/mnt/nas/huggingface/hub/datasets--KETI-IRRC--openarm_handover_v0_20260521_202117_clean/snapshots/526acb21eb6a1896c2bf4e4710ad6117aef1fcad`
- target repo id: `KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- target root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30`
- tool: `lerobot.openarm_adaptation.action.transform_dataset_to_relative_chunk`
- git head before transform: `b09f7722 docs(status): A1.5 완료 — clean dataset 60 ep HF push, A2 변환 next`
- python env: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- GPU: not used (`CUDA_VISIBLE_DEVICES=`)

Transform arguments:

- `chunk_size=30`
- `exclude_joint_indices=(7, 15)`
- `state_key="observation.state"`
- `action_key="action"`
- `push_to_hub=False`
- `private=True`
- `verify=True`
- `verify_mean_abs_max=5.0`
- `verify_q_range_max=70.0`

Execution note:

- `source_root=None` was tried first, but failed before target creation because the current LeRobotDataset path expected `/mnt/nas/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117_clean/meta/info.json` and then hit a `RevisionNotFoundError` constructor mismatch in the installed `huggingface_hub`.
- Final run used the already downloaded clean HF snapshot above as explicit `source_root`. The source repo, target repo, target root, chunking, excluded joints, keys, verification thresholds, and `push_to_hub=False` were unchanged.

## 2. 변환 결과 verification

Built-in verification result:

- `verification.is_relative_like=True`
- `mean_abs_max=1.4375325441360474`
- `quantile_abs_max=60.71202850341797`
- `verify_mean_abs_max=5.0`
- `verify_q_range_max=70.0`
- `valid_chunks=52111`
- `relative_rows=1563330`
- `stats_method=RunningQuantileStats`
- `chunk_size=30`
- `action_dim=16`
- `converted_indices=[0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14]`
- `excluded_indices=[7, 15]`
- `pushed_to_hub=False`
- marker: `.relstats_complete` exists

Marker contents:

```text
source_repo_id=KETI-IRRC/openarm_handover_v0_20260521_202117_clean
target_repo_id=KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30
chunk_size=30
exclude_joint_indices=7,15
relative_rows=1563330
```

## 3. source vs target action stats 비교

Source stats are the clean 60 ep absolute-action stats. Target stats are the rewritten relative-chunk action stats.

| idx | source_mean | target_mean | source_q01 | target_q01 | source_q99 | target_q99 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -11.919999 | -0.404844 | -64.507981 | -42.884532 | 12.956546 | 36.487837 |
| 1 | 16.127436 | 0.702926 | -4.094754 | -20.018216 | 49.857271 | 29.808139 |
| 2 | 2.348790 | 0.324438 | -26.842081 | -28.990379 | 40.713160 | 33.463867 |
| 3 | 59.191147 | 0.526349 | -2.355740 | -60.712029 | 110.796363 | 55.974019 |
| 4 | 27.692004 | 1.437533 | -11.213033 | -34.865895 | 74.042658 | 37.190628 |
| 5 | 4.422533 | 0.217573 | -6.134102 | -17.179667 | 13.145707 | 11.668494 |
| 6 | -18.275379 | 0.668795 | -50.921930 | -30.409188 | 27.333270 | 39.401743 |
| 7 | -12.567598 | -12.861794 | -42.228679 | -55.149351 | -0.094510 | -0.001279 |
| 8 | 21.444002 | 0.061259 | -8.921473 | -29.393150 | 64.869684 | 40.940034 |
| 9 | -18.834448 | -0.322772 | -46.914181 | -20.250739 | 1.550214 | 15.507041 |
| 10 | -1.200394 | -0.233273 | -28.151536 | -29.160738 | 28.109277 | 24.190219 |
| 11 | 67.512569 | 0.669032 | 3.306887 | -57.035355 | 116.660418 | 52.391573 |
| 12 | -11.591500 | -0.092283 | -36.444569 | -25.675149 | 3.400656 | 23.233309 |
| 13 | 3.190059 | 0.264916 | 0.909944 | -1.599977 | 6.943997 | 2.258943 |
| 14 | 3.316200 | -0.905821 | -24.272609 | -30.479392 | 26.255885 | 25.087136 |
| 15 | -14.856462 | -15.234609 | -53.047036 | -65.000000 | -0.000585 | -0.000265 |

## 4. gripper indices `(7, 15)` 보존 확인

- Verification metadata reports `excluded_indices=[7, 15]`.
- Converted indices exclude both gripper columns, so `to_relative_actions()` does not subtract state for gripper dimensions.
- Target gripper stats remain absolute-action-like rather than near-zero relative deltas:
  - idx 7: mean `-12.861794`, q01 `-55.149351`, q99 `-0.001279`
  - idx 15: mean `-15.234609`, q01 `-65.000000`, q99 `-0.000265`
- Source and target gripper stats are not expected to be identical because target stats are recomputed over valid chunk rows (`1,563,330`) rather than source flat frames (`53,851`). The preservation claim is conversion exclusion, not statistic equality.

## 5. dataset 무결성

Metadata:

- target `total_episodes=60`
- target `total_frames=53851`
- target `total_tasks=3`
- target `fps=30`
- `action.shape=[16]`
- `observation.state.shape=[16]`
- video features: `left_wrist`, `right_wrist`, `base`; each `480x640x3`, AV1, 30 fps

File checks:

- `.relstats_complete`: exists
- `meta/info.json`: exists
- `meta/stats.json`: exists and action stats rewritten
- source clean files: `41`
- target files: `42` including `.relstats_complete`
- target size: `1.4G`
- `diff -qr --exclude=stats.json --exclude=.relstats_complete <clean_source_snapshot> <target_root>` produced no output.

This confirms the clean dataset payload and metadata other than rewritten `meta/stats.json` plus marker are unchanged.

## 6. M2 / 65 ep 기준과의 비교

Clean 전 65 ep source snapshot:

- source repo id: `KETI-IRRC/openarm_handover_v0_20260521_202117`
- snapshot: `/mnt/nas/huggingface/hub/datasets--KETI-IRRC--openarm_handover_v0_20260521_202117/snapshots/9b07ecdfe27f5870b32b42574cda3ef666dbb276`
- metadata: `65` episodes, `58340` frames, `3` tasks
- comparison method: target dataset은 만들지 않고 동일 relstats 계산 경로로 65 ep action stats만 메모리 산출

Summary:

| metric | 65 ep relstats | clean 60 ep relstats | delta |
| --- | ---: | ---: | ---: |
| valid_chunks | 56455 | 52111 | -4344 |
| relative_rows | 1693650 | 1563330 | -130320 |
| mean_abs_max | 1.562549 | 1.437533 | -0.125017 |
| quantile_abs_max | 61.702087 | 60.712029 | -0.990059 |

The valid chunk delta is exactly `4489 removed frames - 5 removed episodes * 29 chunk-edge rows = 4344`.

Per-dimension relstats comparison:

| idx | 65_mean | clean_mean | delta_mean | 65_q01 | clean_q01 | delta_q01 | 65_q99 | clean_q99 | delta_q99 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -0.816036 | -0.404844 | 0.411192 | -43.058102 | -42.884532 | 0.173570 | 36.445317 | 36.487837 | 0.042521 |
| 1 | 1.160985 | 0.702926 | -0.458060 | -19.928824 | -20.018216 | -0.089392 | 38.673763 | 29.808139 | -8.865624 |
| 2 | 0.335103 | 0.324438 | -0.010665 | -29.123082 | -28.990379 | 0.132703 | 33.382780 | 33.463867 | 0.081087 |
| 3 | 0.593593 | 0.526349 | -0.067243 | -61.702086 | -60.712029 | 0.990058 | 57.617576 | 55.974019 | -1.643557 |
| 4 | 1.562549 | 1.437533 | -0.125017 | -34.655755 | -34.865895 | -0.210140 | 36.699704 | 37.190628 | 0.490923 |
| 5 | 0.221420 | 0.217573 | -0.003846 | -16.458903 | -17.179667 | -0.720764 | 11.620251 | 11.668494 | 0.048243 |
| 6 | 0.681768 | 0.668795 | -0.012974 | -30.238387 | -30.409188 | -0.170801 | 39.327347 | 39.401743 | 0.074395 |
| 7 | -13.662263 | -12.861794 | 0.800468 | -55.150113 | -55.149351 | 0.000761 | -0.001259 | -0.001279 | -0.000020 |
| 8 | 0.032792 | 0.061259 | 0.028467 | -29.513919 | -29.393150 | 0.120770 | 40.374552 | 40.940034 | 0.565482 |
| 9 | -0.316607 | -0.322772 | -0.006165 | -20.555025 | -20.250739 | 0.304286 | 15.824665 | 15.507041 | -0.317624 |
| 10 | 0.040176 | -0.233273 | -0.273449 | -28.933889 | -29.160738 | -0.226849 | 28.018085 | 24.190219 | -3.827866 |
| 11 | 0.672776 | 0.669032 | -0.003744 | -57.217579 | -57.035355 | 0.182224 | 52.867178 | 52.391573 | -0.475605 |
| 12 | -0.377349 | -0.092283 | 0.285066 | -29.061356 | -25.675149 | 3.386206 | 23.423105 | 23.233309 | -0.189796 |
| 13 | 0.276824 | 0.264916 | -0.011908 | -1.619866 | -1.599977 | 0.019889 | 2.270506 | 2.258943 | -0.011563 |
| 14 | -0.920661 | -0.905821 | 0.014840 | -29.889294 | -30.479392 | -0.590098 | 24.375581 | 25.087136 | 0.711555 |
| 15 | -15.675111 | -15.234609 | 0.440502 | -65.000000 | -65.000000 | 0.000000 | -0.000270 | -0.000265 | 0.000006 |

Largest clean-vs-65 changes on converted arm dims:

- mean: idx 1 `-0.458060`, idx 0 `+0.411192`, idx 12 `+0.285066`
- q01: idx 12 `+3.386206`, idx 3 `+0.990058`, idx 5 `-0.720764`
- q99: idx 1 `-8.865624`, idx 10 `-3.827866`, idx 3 `-1.643557`

Diagnosis:

- Removing the 5 failed episodes reduced the relstats tail slightly: converted `quantile_abs_max` moved from `61.70` to `60.71`.
- Mean centering also improved slightly: converted `mean_abs_max` moved from `1.56` to `1.44`.
- The largest change is idx 1 q99 (`-8.87 deg`), so the removed episodes had some upper-tail influence, but the clean distribution remains in the same relative-like scale as the 65 ep source.
- Historical D-33 M2 audit (`a6000_handover_v0_relstats_transform_20260522.md`) was the earlier 20 ep banana-only relstats dataset (`valid_chunks=17364`, `mean_abs_max=0.795548`, `quantile_abs_max=64.902863`), so it is not a clean-pre 65 ep baseline. It remains useful only as a previous task-specific relstats reference.

## 7. PASS/FAIL 판정

PASS.

Reasons:

- Built-in relative-like verification passed.
- `mean_abs_max=1.4375325441360474 < 5.0`.
- `quantile_abs_max=60.71202850341797 < 70.0`.
- `.relstats_complete` marker exists.
- `pushed_to_hub=False`; HF push was not performed.
- Target metadata reports `60` episodes and `53,851` frames.
- Payload diff excluding `meta/stats.json` and `.relstats_complete` is clean.
- Target size is `1.4G`, below the expected `15G` bound.

## 8. 다음 단계

- A2b HF push completed on 2026-06-05; details below.
- A3 alpha-double-prime training started from this clean relstats dataset on GPU1:
  - status: `audits/openarm_folding/a6000_pi05_handover_v0_clean_alpha2prime_status_20260605_015232.md`
  - dataset args include both `--dataset.repo_id=KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30` and the local `--dataset.root`.

---

## A2b HF Push (2026-06-05)

- repo: `https://huggingface.co/datasets/KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30`
- private: `true`
- upload method: `huggingface-cli upload KETI-IRRC/openarm_handover_v0_clean_relstats_chunk30 <target_root> --repo-type=dataset --private`
- source folder: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_clean_relstats_chunk30`

Hub verification:

- `whoami`: `syh4661`
- org access: `KETI-IRRC`
- file count: `42`
- `.relstats_complete` in repo files: `True`
- `meta/stats.json` in repo files: `True`
- `action.mean[:4]`: `[-0.4048439860343933, 0.7029255628585815, 0.3244377672672272, 0.5263494849205017]`
- `action.q01[:4]`: `[-42.884531908215216, -20.018216276168822, -28.99037908713023, -60.71202855791364]`
- `action.q99[:4]`: `[36.48783746802285, 29.808138561248754, 33.463866707130656, 55.97401901245114]`
- converted action mean abs max: `1.4375325441360474`
- converted action q01/q99 abs max: `60.71202855791364`

A2b 판정: PASS. Dataset HF push completed as private; marker and relstats action stats were verified from the Hub.
