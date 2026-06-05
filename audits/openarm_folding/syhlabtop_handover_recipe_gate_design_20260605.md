# syhlabtop handover recipe gate 설계 기록 (A4 P)

## 1. 배경

M4 alpha shortlist gate에서 handover dataset/checkpoint 조합이 folding 전용 recipe lock 때문에 실패했다.

주요 FAIL 항목:

- `robot_type`: handover dataset은 `bi_openarm_follower` 계열을 사용하지만 기존 gate는 `openarms_follower`만 허용했다.
- `camera shape`: handover recording은 3개 camera 모두 `[480, 640, 3]`이고, folding recipe는 wrist camera `[720, 1280, 3]`를 요구했다.
- `RABC`: handover alpha double-prime 학습은 RABC를 필수 조건으로 두지 않았지만 기존 gate는 folding recipe 기준으로 RABC 기록을 요구했다.

A6 shortlist gate에서 handover checkpoint를 평가하려면 folding recipe lock을 유지하면서 handover recipe variant를 별도로 통과시킬 수 있는 P 단계가 필요했다.

## 2. Option D 디자인

Option D는 기존 `validate_folding_recipe()`를 generic `validate_recipe()`로 refactor하고, task별 recipe wrapper를 추가하는 방식이다.

- `LOCKED_FOLDING_RECIPE`: 기존 값 유지.
- `LOCKED_HANDOVER_RECIPE`: handover 전용 lock constant 추가.
- `validate_recipe()`: recipe lock, 허용 robot type, 기대 camera shape, RABC 필수 여부를 인자로 받는 generic gate.
- `validate_folding_recipe()`: backward-compatible wrapper. 기존 외부 호출자는 그대로 사용 가능.
- `validate_handover_recipe()`: handover task wrapper. `bi_openarm_follower` 허용, 480x640 camera shape 사용, RABC optional.
- `stage29_candidate_recipe_gate.py`: `--task {folding,handover}` 옵션 추가. task에 따라 recipe tuple을 선택해 `validate_recipe()` 호출.

## 3. 변경 파일 및 시그니처 요약

변경 파일:

- `audits/openarm_folding/stage22_dataset_replay_and_ablation.py`
- `audits/openarm_folding/stage29_candidate_recipe_gate.py`

`validate_recipe()` 추가 시그니처 요약:

```python
def validate_recipe(
    *,
    cfg: PreTrainedConfig,
    model_dir: Path,
    dataset_repo: str,
    dataset_root: Path,
    info: dict[str, Any],
    max_rows: int,
    relative_stats_tolerance_deg: float,
    action_span_ratio_limit: float,
    action_is_relative: bool,
    action_is_relative_source: str,
    recipe_locked: dict[str, Any],
    allowed_robot_types: frozenset[str],
    expected_image_shapes: dict[str, list[int]],
    require_rabc: bool = True,
) -> dict[str, Any]:
```

일반화된 check:

- `dataset_robot_type_supported`: `allowed_robot_types` 기준으로 검사.
- `camera_keys_and_shapes_match_recipe`: `expected_image_shapes` 기준으로 검사.
- `rabc_recorded_in_train_config`: `require_rabc=True`일 때만 필수 검사.
- `rabc_not_required_for_this_task`: `require_rabc=False`일 때 정보성 pass row로 기록.

`stage29` 변경:

```python
parser.add_argument("--task", default="folding", choices=["folding", "handover"])
```

## 4. 검증

Import smoke:

```bash
uv run python -c "from audits.openarm_folding.stage22_dataset_replay_and_ablation import validate_recipe, validate_folding_recipe, validate_handover_recipe, LOCKED_HANDOVER_RECIPE; print('OK')"
```

결과: `OK`

문법 확인:

```bash
uv run python -m py_compile audits/openarm_folding/stage22_dataset_replay_and_ablation.py audits/openarm_folding/stage29_candidate_recipe_gate.py
```

결과: PASS

`stage29 --help` 확인:

```bash
uv run python audits/openarm_folding/stage29_candidate_recipe_gate.py --help
```

결과: help output에 `--task {folding,handover}` 표시 확인.

## 5. 다음

A6 shortlist gate에서 `stage29_candidate_recipe_gate.py --task=handover`로 alpha double-prime 5개 checkpoint를 clean handover dataset 기준 평가한다.
