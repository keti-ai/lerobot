# OpenArm Adaptation 미니 레포 — 스터디 노트

PLAN.md §5 D-34 의 사이드 트랙. 메인 트랙 (D-33 handover relstats 재학습 + α
재학습) 과 병행 진행한다.

**위치**: 이 디렉토리는 스터디 / plan / 결과 누적 영역이다. 실제 모듈 코드는
`src/lerobot/openarm_adaptation/` (fork-specific 패키지) 에 둔다.

**마지막 갱신**: 2026-05-22 (D-34 초안)

---

## 1. 왜 (Motivation)

학습 데이터셋의 분포와 현재 운영 환경 (OpenArm bimanual follower + RealSense
3 cam) 의 분포 사이에 큰 간극이 있다. 이 간극이 학습 결과가 라이브에서
무너지는 주요 원인 중 하나다.

**구체 사례 (지금까지 누적)**:

| 사례 | 학습 데이터 | 운영 환경 | 결과 |
|---|---|---|---|
| **A** action contract | level2: chunk30 + arm relative + gripper excluded | handover_v0: absolute action rows | D-32 case α REJECTED (PI0.5 α 학습 자체 결함) |
| **B** base camera FOV | full_folding base view (overhead, wider FOV) | OpenArm base 213622075840 (낮은 위치, 좁은 FOV) | STATUS.md 미해결 이슈 #2 |
| **C** wrist camera resolution | training recipe 1280x720 | syhlabtop capture 640x480 | STATUS.md 미해결 이슈 #4 |
| **D** joint zero/unit | dataset 별로 degrees + zero offset | OpenArmFollower 16D contract, gripper [-65, 0] | upstream 일치 확인됨, future 확장 대비 |
| **E** color/exposure | dataset 의 카메라 gain/exposure 고정 | RealSense auto exposure | 미진단 |

**해결책**: dataset ↔ inference 양쪽에서 같은 preprocessing 함수를 통과시켜
분포를 맞춘다. 양방향 (offline transform + online ProcessorStep) 패턴.

---

## 2. 무엇을 (Scope)

사용자 우선순위: **P0 vision → P1 proprio → P2 action contract**.

### P0 vision (우선)

| 함수 | 입력 | 출력 | 사용처 |
|---|---|---|---|
| `resize_align` | image + target_size + crop_mode | resized + center-cropped image | dataset video frame → train, live frame → infer |
| `color_match` | image + reference histogram (또는 single ref frame) | white-balance + exposure 정규화 image | live frame → infer (학습 분포 맞춤) |
| `intrinsic_compensate` | image + src_intrinsic + dst_intrinsic | reproject 또는 affine warp | 카메라 FOV 차이가 큰 경우 (사례 B) |

### P1 proprio (그 다음)

| 함수 | 입력 | 출력 | 사용처 |
|---|---|---|---|
| `joint_offset` | state vector + offset table | zero-shifted state | dataset → train, live → infer |
| `joint_unit_convert` | state vector + (degrees↔radians, gripper_range) | unit 정규화 state | 같음 |
| `joint_range_clip` | state vector + software limit table | clipped state + saturation mask | live → infer (안전 + 분포 매칭) |

### P2 action contract (D-33 의 일반화)

| 함수 | 입력 | 출력 | 사용처 |
|---|---|---|---|
| `to_relative_chunk` | absolute action dataset + chunk_size + exclude_joints | relative action dataset + relstats marker | offline dataset transform |
| `from_relative_chunk` | relative action prediction + current state | absolute target | live ProcessorStep |

**참고**: lerobot 에 이미 `src/lerobot/processor/relative_action_processor.py`
의 `to_relative_actions` / `to_absolute_actions` 가 있다. P2 함수는 그 위에
dataset-level wrapper 와 OpenArm-specific exclude_joints/chunk 기본값을 얹는
형태로 만든다.

---

## 3. 어디에 (Location)

```
src/lerobot/openarm_adaptation/        ← fork-specific 패키지
├── __init__.py                        ← public API
├── vision/
│   ├── __init__.py
│   ├── resize_align.py                ← ProcessorStep 호환
│   ├── color_match.py                 ← ProcessorStep 호환
│   └── intrinsic_compensate.py        ← (선택, P0 후반)
├── proprio/
│   ├── __init__.py
│   ├── joint_offset.py
│   ├── joint_unit_convert.py
│   └── joint_range_clip.py
└── action/
    ├── __init__.py
    └── relstats_transform.py          ← D-33 도구의 일반화

docs/STUDY/openarm_adaptation/         ← 스터디 / 결과 누적
├── README.md                          ← 이 파일
├── p0_vision_design.md                ← (다음 commit)
├── p1_proprio_design.md               ← P0 끝나고
└── p2_action_results.md               ← D-33 결과 누적
```

**왜 fork-specific 패키지인가**:
- upstream lerobot 변경과 격리 → merge 충돌 회피
- `src/lerobot/processor/` 와 같은 ProcessorStep 패턴 따름 → pipeline 통합 가능
- import path 가 명확: `from lerobot.openarm_adaptation.vision import ResizeAlign`

**대안 (기각)**:
- `src/lerobot/processor/` 직접 추가 — upstream merge 충돌 위험
- `audits/openarm_adaptation/` — 라이브 inference 와 통합 어려움
- `docs/STUDY/` 단독 — 코드 X, 스터디 문서만

---

## 4. 어떻게 (Pattern)

`src/lerobot/processor/relative_action_processor.py` 를 모범으로 둔다:

```python
# 1) 순수 함수 (offline 변환 가능)
def to_relative_actions(actions, state, mask): ...

# 2) ProcessorStep (pipeline 통합)
@ProcessorStepRegistry.register("openarm_adaptation.vision.resize_align")
@dataclass
class ResizeAlignStep(ProcessorStep):
    target_size: tuple[int, int]
    crop_mode: str = "center"
    def __call__(self, transition: EnvTransition) -> EnvTransition: ...
```

양방향 사용:
- **Offline** (dataset 생성): 순수 함수로 LeRobotDataset 의 frames 를 transform
  후 새 dataset 으로 push (D-33 의 P2 use case)
- **Online** (라이브 inference): ProcessorStep 을 PolicyProcessorPipeline 에
  등록. lerobot-rollout 자동 활용.

---

## 5. 진입 시점 + 우선순위

```
D-33 (메인 트랙) 과 병행 가능. 메인 BLOCKED 시간 (Codex 의 a6000 측 학습이
도는 동안 syhlabtop 측) 에 진행.

Phase A (지금 ~ D-33 dataset 변환 끝까지):
  [A1] src/lerobot/openarm_adaptation/ 패키지 scaffold (Codex, ~30분)
       __init__.py + vision/__init__.py 만 비어 있는 형태
  [A2] action/relstats_transform.py 작성 (Codex, ~1-2h)
       D-33 의 handover dataset 변환에 즉시 사용. P2 함수가 메인 트랙의
       도구로 동시에 작동.

Phase B (D-33 α 재학습이 도는 동안, overnight):
  [B1] vision/resize_align.py + ProcessorStep (Codex, ~1-2h)
       기본 target_size = handover dataset 의 카메라 해상도
  [B2] vision/color_match.py (Codex, ~1-2h)
       reference frame 1개 기반 simple histogram match

Phase C (D-33 결과 본 뒤):
  [C1] vision/intrinsic_compensate.py (필요 시)
  [C2] proprio/* (P1)
```

---

## 6. 검증

각 단계 commit 시:

```
[A1]  ls src/lerobot/openarm_adaptation/ 가 비어 있지 않음
       uv run python -c "import lerobot.openarm_adaptation" OK
[A2]  uv run python -c "from lerobot.openarm_adaptation.action import relstats_transform"
       D-33 의 handover dataset 변환이 이 함수로 실제 가능
[B*]  ProcessorStepRegistry 에 등록됨 (uv run python -c "from lerobot.processor import ProcessorStepRegistry; print(ProcessorStepRegistry.list())")
       LeRobotDataset frame 1개 통과 smoke test
[C*]  동일
```

각 phase 끝나면 STATUS.md 트랙 G 행 갱신.

---

## 7. 사용자 결정 필요 항목

```
D-34a  src/lerobot/openarm_adaptation/ 위치 OK 인지 확인
D-34b  Phase A scaffold + relstats_transform 우선 진행 vs P0 vision 우선 진행
D-34c  ProcessorStepRegistry 등록 prefix = "openarm_adaptation.*" OK 인지
```

기본 권장 = D-34a YES, D-34b A 우선 (D-33 의 즉시 도구화), D-34c YES.

---

## 8. 결과 누적

`docs/STUDY/openarm_adaptation/` 안에:
- `p0_vision_design.md` — P0 함수 별 design + smoke test 결과
- `p1_proprio_design.md` — P1 동일
- `p2_action_results.md` — D-33 의 handover relstats 변환 결과 (전/후 stats
  비교, α 재학습 결과)
- `feasibility_impact_<YYYYMMDD>.md` — 라이브 트랙에서 adaptation 사용 전/후
  성능 차이

---

## 9. 참조

- SSOT: `docs/PLAN.md` §5 D-34
- 현황: `docs/STATUS.md` 트랙 G
- lerobot upstream processor 패턴: `src/lerobot/processor/relative_action_processor.py`
- 메인 트랙: D-33 (handover dataset relstats 변환 + α 재학습)
- 사이드 트랙 인접: `docs/STUDY/mini_leader/` (산업 양팔 데이터 수집 플랫폼)
