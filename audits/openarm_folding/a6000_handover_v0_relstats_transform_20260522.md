# A6000 handover v0 relstats transform

마지막 갱신: 2026-05-22T21:14:42+09:00

## 1. 변환 입력

- source repo id: `KETI-IRRC/openarm_handover_v0_20260521_202117`
- source root: `/mnt/nas/huggingface/lerobot/hub/datasets--KETI-IRRC--openarm_handover_v0_20260521_202117/snapshots/ef6e5a449db6c78cfd1a103e250ac84a17de0e35`
- target repo id: `KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- target root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`
- tool: `lerobot.openarm_adaptation.action.transform_dataset_to_relative_chunk`
- git head: `ca532645 study(adaptation): D-34 P2 - relstats_transform (handover ->relative chunk30)`
- python env: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- torch reported by env: `2.11.0+cu128`

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

## 2. 변환 결과 verification

Built-in verification result:

- `verification.is_relative_like=True`
- `mean_abs_max=0.7955476641654968`
- `quantile_abs_max=64.90286254882812`
- `verify_mean_abs_max=5.0`
- `verify_q_range_max=70.0`
- `valid_chunks=17364`
- `relative_rows=520920`
- `stats_method=get_feature_stats`
- `action_dim=16`
- `converted_indices=[0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14]`
- `excluded_indices=[7, 15]`
- `pushed_to_hub=False`
- marker: `.relstats_complete` exists

Marker contents:

```text
source_repo_id=KETI-IRRC/openarm_handover_v0_20260521_202117
target_repo_id=KETI-IRRC/openarm_handover_v0_relstats_chunk30
chunk_size=30
exclude_joint_indices=7,15
relative_rows=520920
```

Target metadata exists:

- `meta/info.json`
- `meta/stats.json`

Target size:

- `426M`

## 3. source vs target action stats 16D 표

| idx | source_mean | target_mean | source_q01 | target_q01 | source_q99 | target_q99 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | -6.913732 | 0.133677 | -53.696561 | -34.532536 | 15.821073 | 34.837295 |
| 1 | 9.102550 | 0.187757 | -3.946715 | -18.412674 | 35.468585 | 19.871199 |
| 2 | -1.319622 | 0.189990 | -31.899256 | -22.993805 | 33.291127 | 35.272423 |
| 3 | 46.858784 | 0.734952 | -2.856793 | -55.969768 | 106.158355 | 64.902864 |
| 4 | 17.216415 | 0.372737 | -6.306092 | -25.513354 | 52.704707 | 26.990352 |
| 5 | 12.506412 | 0.312952 | 1.238660 | -11.514679 | 18.889636 | 11.175688 |
| 6 | -18.400555 | 0.630468 | -45.675553 | -25.594199 | 11.438140 | 24.056997 |
| 7 | -15.002465 | -15.249902 | -45.106168 | -55.182118 | -0.177754 | -0.001072 |
| 8 | 10.382701 | -0.077234 | -16.290435 | -30.431080 | 58.329362 | 45.105192 |
| 9 | -11.700112 | -0.227538 | -40.515305 | -23.225681 | 5.365323 | 17.974770 |
| 10 | -1.267590 | -0.092946 | -30.788661 | -24.630690 | 24.909343 | 25.654131 |
| 11 | 55.115723 | 0.742565 | 3.526179 | -62.425461 | 113.034871 | 59.798914 |
| 12 | -19.302902 | -0.185268 | -50.380406 | -30.961857 | 0.732852 | 25.340089 |
| 13 | 4.136197 | -0.089780 | 0.641669 | -2.190136 | 7.652941 | 1.710513 |
| 14 | 11.102468 | -0.795548 | -22.486979 | -35.388463 | 43.896063 | 32.949030 |
| 15 | -15.851535 | -16.172138 | -46.323311 | -51.226046 | -0.001205 | -0.000307 |

## 4. gripper indices `(7,15)` 보존 확인

- Verification metadata reports `excluded_indices=[7, 15]`.
- `to_relative_actions()` subtracts `state * mask`; with mask false for indices 7 and 15, no relative subtraction is applied to those dimensions.
- The target stats for indices 7 and 15 remain absolute-action-like rather than near-zero relative deltas:
  - idx 7: mean `-15.249902`, q01 `-55.182118`, q99 `-0.001072`
  - idx 15: mean `-16.172138`, q01 `-51.226046`, q99 `-0.000307`

Note: source and target gripper stats are not expected to be bit-identical because target action stats are recomputed over valid chunk rows (`520920` rows), not the original flat frame distribution (`17944` rows). The preservation claim here is conversion exclusion, not full-dataset statistic equality.

## 5. dataset 무결성 체크

Load check:

- source frames: `17944`
- target frames: `17944`
- source episodes: `20`
- target episodes: `20`
- source fps: `30`
- target fps: `30`
- target action shape: `(16,)`
- target state shape: `(16,)`

File/content check:

- source files: `15`
- target files: `16` including `.relstats_complete`
- source bytes excluding `stats.json`/marker: `445875915`
- target bytes excluding `stats.json`/marker: `445875915`
- `diff -qr --exclude=stats.json --exclude=.relstats_complete <source> <target>` produced no output.

This confirms the dataset payload and metadata other than rewritten action stats plus the marker are unchanged.

## 6. PASS/FAIL 판정

PASS.

Reasons:

- Built-in relative-like verification passed.
- `mean_abs_max=0.7955476641654968 < 5.0`.
- `quantile_abs_max=64.90286254882812 < 70.0`.
- `.relstats_complete` marker exists.
- `pushed_to_hub=False`; no HF push was performed.
- Source and target load with identical frame/episode/fps counts.
- Dataset payload matches source outside `meta/stats.json` and marker.

## 7. 다음 단계 pending

- M2b: decide whether to push `KETI-IRRC/openarm_handover_v0_relstats_chunk30` to HF Hub.
- M3: alpha-prime retraining against the local relstats variant after push/local-path decision.

---

## HF Push (2026-05-22)

- updated: `2026-05-22T21:28:09+09:00`
- repo: `https://huggingface.co/datasets/KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- private: `true`
- upload method: `huggingface_hub.HfApi.upload_folder(..., allow_patterns=["**"], ignore_patterns=[])`
- source folder: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`

Hub verification:

- `whoami`: `syh4661`
- org access: `KETI-IRRC`
- file count: `16`
- `.relstats_complete` in repo files: `True`
- `meta/stats.json` in repo files: `True`
- `action.mean[:4]`: `[0.13367731869220734, 0.18775713443756104, 0.18998955190181732, 0.7349516749382019]`
- `action.q01[:4]`: `[-34.532536155299134, -18.41267444065639, -22.99380534778942, -55.96976826985677]`
- `action.q99[:4]`: `[34.83729527064731, 19.871198527018223, 35.27242279052731, 64.90286407470694]`
- converted action mean abs max: `0.7955476641654968`
- converted action q01/q99 abs max: `64.90286407470694`

M2b 판정: PASS. Dataset HF push completed as private; marker and relstats action stats were verified from the Hub.
