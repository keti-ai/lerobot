# syhlabtop handover_v0 clean dataset 생성 기록 (A1.5)

## 1. 입력

- Source repo: `KETI-IRRC/openarm_handover_v0_20260521_202117`
- Source root: `/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117`
- Clean repo: `KETI-IRRC/openarm_handover_v0_20260521_202117_clean`
- Clean root: `/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117_clean`
- 제외 episode: `[13, 24, 25, 51, 55]`
- 제외 이유: 사용자 review 결과 실패 episode로 확정.
- 원본 보존 확인: source dataset은 작업 후에도 `total_episodes=65`, `total_frames=58340`, `total_tasks=3`.

## 2. 실행

```bash
cd /home/syhlabtop/workspace/lerobot

uv run lerobot-edit-dataset \
  --repo_id KETI-IRRC/openarm_handover_v0_20260521_202117 \
  --root /home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117 \
  --new_repo_id KETI-IRRC/openarm_handover_v0_20260521_202117_clean \
  --new_root /home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117_clean \
  --operation.type delete_episodes \
  --operation.episode_indices "[13, 24, 25, 51, 55]"
```

## 3. 결과

- Clean `total_episodes`: `60`
- Clean `total_frames`: `53851`
- Clean `total_tasks`: `3`
- Clean size: `1.4G`
- Source-clean frame diff: `4489`
- 삭제 episode frame 합계: `4489`

삭제된 source episode:

| source episode | task | frames |
| --- | --- | ---: |
| 13 | Pick the banana, hand it over to the other arm, and place it at the target. | 898 |
| 24 | Pick the olive green cup, hand it over to the other arm, and place it at the target. | 898 |
| 25 | Pick the olive green cup, hand it over to the other arm, and place it at the target. | 898 |
| 51 | Pick the blue toothpaste, hand it over to the other arm, and place it at the target. | 898 |
| 55 | Pick the blue toothpaste, hand it over to the other arm, and place it at the target. | 897 |

Clean task별 episode 수:

| task | source episodes | clean episodes |
| --- | ---: | ---: |
| Pick the banana, hand it over to the other arm, and place it at the target. | 20 | 19 |
| Pick the olive green cup, hand it over to the other arm, and place it at the target. | 25 | 23 |
| Pick the blue toothpaste, hand it over to the other arm, and place it at the target. | 20 | 18 |

## 4. tasks.parquet 비교

Source tasks:

| task | task_index |
| --- | ---: |
| Pick the banana, hand it over to the other arm, and place it at the target. | 0 |
| Pick the olive green cup, hand it over to the other arm, and place it at the target. | 1 |
| Pick the blue toothpaste, hand it over to the other arm, and place it at the target. | 2 |

Clean tasks:

| task | task_index |
| --- | ---: |
| Pick the blue toothpaste, hand it over to the other arm, and place it at the target. | 0 |
| Pick the olive green cup, hand it over to the other arm, and place it at the target. | 1 |
| Pick the banana, hand it over to the other arm, and place it at the target. | 2 |

Task text 목록은 source 3 row에서 clean 3 row로 유지됐다. 다만 `delete_episodes` 실행 중 `task_index` 값은 자동 재할당됐다.

## 5. Episode reindex 결과

- Clean episode metadata path: `meta/episodes/chunk-000/file-000.parquet`
- Clean episode count: `60`
- Clean episode index range: `0..59`
- Missing index in `0..59`: 없음
- Source에서 `[13, 24, 25, 51, 55]`를 제거한 뒤 남은 episode의 task/length 시퀀스가 clean과 일치함: `True`

Reindex 예:

| source episode | clean episode | note |
| ---: | ---: | --- |
| 12 | 12 | 삭제 전 |
| 14 | 13 | source 13 삭제 반영 |
| 23 | 22 | source 24/25 삭제 전 |
| 26 | 23 | source 24/25 삭제 반영 |
| 50 | 47 | source 13/24/25 삭제 반영 |
| 52 | 48 | source 51 삭제 반영 |
| 56 | 51 | source 55 삭제 반영 |

## 6. HF push 결정

- HF push: 실행 완료.
- 사용자 확인: A1.5 검증 PASS 후 `continue` 지시로 진행.
- Dataset URL: `https://huggingface.co/datasets/KETI-IRRC/openarm_handover_v0_20260521_202117_clean`
- HF repo visibility: private
- HF remote commit SHA: `526acb21eb6a1896c2bf4e4710ad6117aef1fcad`
- HF file count: `41`
- HF 확인: `meta/info.json`, `meta/tasks.parquet` 존재 확인.

실행 명령:

```bash
huggingface-cli upload \
  "KETI-IRRC/openarm_handover_v0_20260521_202117_clean" \
  "/home/syhlabtop/.cache/huggingface/lerobot/KETI-IRRC/openarm_handover_v0_20260521_202117_clean" \
  --repo-type=dataset \
  --private \
  --commit-message "initial upload - clean dataset (excluded ep [13,24,25,51,55])"
```

## 7. 다음

- A2: clean dataset 기준 relstats 변환.
