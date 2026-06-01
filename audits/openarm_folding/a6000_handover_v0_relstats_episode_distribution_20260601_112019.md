# D-35 U handover relstats episode distribution diagnosis

마지막 갱신: 2026-06-01T11:20:19+09:00

## 1. 목적

M4 shortlist gate `b7897a06` 는 handover alpha-prime relstats checkpoint 5개를 episode 0 하나로만 replay 했다. 이번 D-35 U 의 원래 목적은 같은 5개 checkpoint 에 대해 episode 0-19 전체 replay ratio 와 raw normalized error 분포를 만들어서, magnitude 문제가 episode 0 특이 현상인지 전체 episode 에서 일관된 문제인지 진단하는 것이었다.

이번 실행은 diagnostic-only 로 수행했다. 코드 변경, 학습, gate 통과 시도, dataset/checkpoint 수정, 8766 serving 조작은 하지 않았다.

## 2. 입력

- branch start: `audit/openarm-folding-baseline`
- synced head: `3d1a66bb docs(plan): M4 후속 분기 D-35 (U→P→Q→R) + D-29 갱신 (8766 정지)`
- dataset repo: `KETI-IRRC/openarm_handover_v0_relstats_chunk30`
- dataset root: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/datasets/openarm_handover_v0_relstats_chunk30`
- run dir: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/handover_alpha_relstats_20260522/train/pi05_handover_v0_alpha_relstats_20260522_213056`
- checkpoint shortlist: `022000`, `024000`, `026000`, `028000`, `030000`
- requested episodes: `0-19`
- replay options intended: `--no-recipe-gate`, `--action-is-relative true`, `--video-backend ffmpeg`
- environment: `UV_PROJECT_ENVIRONMENT=/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/venv312_torch27_20260515`
- offline flags used after tokenizer network attempt: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`

GPU status at start:

- All GPUs were occupied by existing processes.
- The D-35 U diagnostic attempted the intended `cuda:0` path but fell back to CPU because CUDA was unavailable in the Codex execution context.
- Existing GPU jobs and serving processes were not touched.

## 3. 실행 결과

Full 5 checkpoint x 20 episode replay was not completed.

Failure handling path:

- First optimized attempt imported the existing Stage 22 functions and tried to load each checkpoint once instead of invoking 100 separate subprocesses.
- Sandbox network blocked tokenizer metadata lookup; retry used `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.
- CPU fallback then completed only one replay cell before the runtime became impractical:
  - `022000`, episode `0`
  - elapsed for that one cell: `885.0s`
- At that pace, even the reduced 5 checkpoint x 5 episode fallback would take multiple hours, exceeding the requested `>1h` stop condition.

Completed D-35 U replay cell:

| step | episode | ratio_range | arm_raw_max_err | max_delta_deg | elapsed |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 022000 | 0 | 0.040-0.107 | 4.847 | 49.107 | 885.0s |

Existing M4 episode 0 replay matrix from `audits/openarm_folding/a6000_pi05_handover_alpha_relstats_shortlist_gate_20260526.md`:

| step | episode | ratio_range | arm_raw_max_err | arm max delta deg | max_delta_deg | replay |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 022000 | 0 | 0.041-0.141 | 4.943 | 5.356 | 47.811 | FAIL |
| 024000 | 0 | 0.038-0.105 | 4.861 | 2.840 | 50.742 | FAIL |
| 026000 | 0 | 0.029-0.096 | 4.838 | 2.994 | 16.214 | FAIL |
| 028000 | 0 | 0.035-0.129 | 4.824 | 4.712 | 67.237 | FAIL |
| 030000 | 0 | 0.031-0.097 | 4.844 | 3.503 | 57.711 | FAIL |

The new D-35 U `022000` episode 0 cell is directionally consistent with M4: low ratio and high raw normalized error. Exact values differ slightly because PI0.5 replay is not bit-for-bit stable across separate CPU invocations.

## 4. Target-only episode distribution

Because full model replay was too slow on CPU, I computed a fast target-only all-episode distribution over the same Stage 22 auto frames: `0, 1, 2, 10, 30, 60, 120, 300`. This does not replace replay ratio, but it checks whether episode 0 was an unusually large recorded target episode.

Raw output: `/tmp/pi05_handover_alpha_relstats_episode_distribution_20260601_1045/target_only_summary.json`

| ep | recorded arm mean delta mean | recorded arm mean delta min | recorded arm mean delta max | target norm arm abs mean | target norm arm abs max |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 9.768 | 7.246 | 22.041 | 0.619 | 4.678 |
| 1 | 14.428 | 7.686 | 30.392 | 0.500 | 1.789 |
| 2 | 14.812 | 7.460 | 28.666 | 0.563 | 1.994 |
| 3 | 13.042 | 5.645 | 27.981 | 0.466 | 2.084 |
| 4 | 15.543 | 5.413 | 30.298 | 0.494 | 2.358 |
| 5 | 9.175 | 3.014 | 29.903 | 0.347 | 1.822 |
| 6 | 11.497 | 4.571 | 27.385 | 0.362 | 1.825 |
| 7 | 3.958 | 0.747 | 25.771 | 0.142 | 1.883 |
| 8 | 8.442 | 4.641 | 34.129 | 0.326 | 2.731 |
| 9 | 10.538 | 5.281 | 35.447 | 0.341 | 2.692 |
| 10 | 15.883 | 5.212 | 35.071 | 0.913 | 5.960 |
| 11 | 13.673 | 4.126 | 38.499 | 0.828 | 6.005 |
| 12 | 14.794 | 4.515 | 30.976 | 0.824 | 6.321 |
| 13 | 9.155 | 3.918 | 34.242 | 0.710 | 5.960 |
| 14 | 11.245 | 7.962 | 33.771 | 0.970 | 9.431 |
| 15 | 14.071 | 4.885 | 29.626 | 1.038 | 9.702 |
| 16 | 14.210 | 3.121 | 34.286 | 0.600 | 7.653 |
| 17 | 16.560 | 5.796 | 33.237 | 0.748 | 3.932 |
| 18 | 14.666 | 4.885 | 33.181 | 0.684 | 4.022 |
| 19 | 16.068 | 4.766 | 35.805 | 0.767 | 3.887 |

Target-only summary:

- overall recorded arm mean delta mean: `12.576`
- first 7 episodes recorded arm mean delta mean: `12.609`
- later 13 episodes recorded arm mean delta mean: `12.559`
- lowest recorded arm mean delta episode: episode `7` (`3.958`)
- highest recorded arm mean delta episode: episode `17` (`16.560`)
- highest target normalized arm abs max: episode `15` (`9.702`)

## 5. 분포 요약

Replay ratio distribution across all 20 episodes is not available from this run because CPU replay exceeded the time budget.

Available replay evidence:

- M4 episode 0 ratio max over all 5 checkpoints: `0.141`
- M4 episode 0 `ratio > 0.5` count: `0/5` checkpoints
- M4 episode 0 `ratio > 0.8` count: `0/5` checkpoints
- D-35 U repeated `022000` episode 0 ratio max: `0.107`

Target-only evidence:

- Episode 0 is not a uniquely large recorded-action episode by mean arm delta.
- First 7 vs later 13 episodes have nearly identical recorded arm mean delta averages (`12.609` vs `12.559`).
- Later episodes, especially `10-16`, have larger normalized target outliers than the first 7 episodes.

## 6. 진단

The requested all-episode replay diagnosis remains incomplete because model inference on CPU was too slow.

What can be said from the completed evidence:

- The M4 episode 0 magnitude failure is reproducible for `022000` under D-35 U conditions.
- Episode 0 does not look like an outlier in recorded target magnitude; many later episodes have equal or larger recorded arm deltas.
- The first-7 vs later-13 collection split does not show a large difference in mean recorded arm delta.
- Later episodes do show larger normalized target outliers, so if the model already under-predicts episode 0, it is unlikely that later episodes would trivially clear the replay threshold.

This is still an inference from target-only distribution plus episode 0 replay, not a substitute for the requested 100-cell replay matrix.

## 7. 다음 단계 input

Recommended next run for D-35 U:

- Wait until at least one A6000 GPU is available, then rerun the 5 checkpoint x 20 episode replay on GPU.
- Keep the optimized "load checkpoint once, loop episodes" approach, but execute it in a GPU-visible environment.
- Keep `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1` to avoid tokenizer metadata network calls.

Inputs to D-35 P/Q from this partial result:

- P: A handover-specific gate should not inherit the locked folding robot/camera/RABC checks unchanged.
- Q: The current replay threshold is not meaningful for handover until a GPU-completed all-episode distribution exists.
- Q: If full replay confirms ratios remain near the M4 range, task-specific ratio thresholds must be defined from handover distributions rather than copied from folding gates.

## 8. 판정

STOPPED / INCOMPLETE for the requested 100-cell replay distribution.

Reason:

- `022000` episode 0 alone took `885.0s` on CPU fallback.
- Full 100-cell replay and even reduced 25-cell fallback would exceed the explicit `>1h` stop condition.

No checkpoint was deleted, moved, pushed, or served.
