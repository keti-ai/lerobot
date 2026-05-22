# PI0.5 handover alpha train result

마지막 갱신: 2026-05-22T10:25:00+09:00

## 요약

- run id: `20260522_002624`
- output: `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624`
- train log: `/data/keti/syh/lerobot_openarm_industrial/train/pi05_handover_v0_alpha_20260522_002624.train.log`
- init ckpt: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_relstats_full_nocompile_bsz4_20260512/checkpoints/004000/pretrained_model`
- dataset: `KETI-IRRC/openarm_handover_v0_20260521_202117`
- policy repo id in config: `KETI-IRRC/pi05_openarm_handover_v0_alpha`
- result: 20,000 step 정상 종료

## 학습 설정

- batch_size: 4
- steps: 20,000
- save_freq: 2,000
- scheduler_decay_steps: 20,000
- compile_model: false
- wandb: false
- execution: single-process `uv run --no-sync lerobot-train --policy.device=cuda`
- GPU: GPU0 only

GPU0만 사용한 이유는 `accelerate launch`/DDP가 아니라 plain `lerobot-train`
단일 프로세스로 실행했기 때문이다. 이 실행은 요청한 `batch_size=4` 조건을 유지한다.
4-GPU 재실행은 effective batch/optimizer 동작이 달라질 수 있으므로 별도 결정이 필요하다.

## 종료 상태

로그 기준:

- start: 2026-05-22 00:28 KST 전후
- end: 2026-05-22 10:04:54 KST
- wall time: 9:36:02
- final metric:
  - `step:20K smpl:80K ep:89 epch:4.46 loss:0.010 grdn:0.426 lr:2.5e-06 updt_s:1.703 data_s:0.005`
- error scan: OOM / NaN / traceback 없음

## Loss trend

| 구간 | 대표 로그 | 관찰 |
|---|---:|---|
| early | step 400 loss 0.111 | 정상 시작, 급격히 하강 |
| 4K 전후 | loss 0.038~0.042 | 안정화 시작 |
| 8K 전후 | loss 0.024~0.026 | 완만한 하강 |
| 12K 전후 | loss 0.016~0.017 | 추가 개선 |
| 16K 전후 | loss 0.012~0.013 | 수렴권 |
| 20K | loss 0.010 | train loss 기준 최저권 |

주의: train loss 기준으로는 020000이 가장 좋아 보이지만, live/eval best step은 아직
결정되지 않았다. checkpoint 선택은 TensorBoard 곡선, metadata 검증, inference smoke,
필요 시 live feasibility 결과를 보고 별도 결정해야 한다.

## Checkpoints

생성된 checkpoint:

- `002000`
- `004000`
- `006000`
- `008000`
- `010000`
- `012000`
- `014000`
- `016000`
- `018000`
- `020000`

각 checkpoint에는 `pretrained_model/model.safetensors`, `config.json`,
`train_config.json`, policy pre/postprocessor 파일, training_state가 존재한다.

저장 용량:

- run directory: 약 229G
- train log: 약 1.6M

중간 checkpoint 자동 삭제는 하지 않았다. 정리 여부는 평가/후보 선정 후 사용자 결정이 필요하다.

## HF Hub 상태

저장된 config 확인 결과:

- `repo_id`: `KETI-IRRC/pi05_openarm_handover_v0_alpha`
- `push_to_hub`: false

따라서 이번 학습은 로컬 checkpoint 저장까지 완료됐고, HF Hub 업로드는 자동 수행되지 않았다.
업로드가 필요하면 best checkpoint 결정 후 수동 push가 필요하다.

## 현재 서버/GPU 상태

- training tmux `pi05_handover_alpha`: 종료됨
- TensorBoard tmux `tb_pi05_handover`: 유지됨
- TensorBoard URL: `http://10.252.205.103:6007`
- GPU: 학습 프로세스 해제됨. GPU0에는 `trung` label backend 약 2.4 GiB만 남아 있음.
- 8766/8765 serving: 학습 시작 전 정지한 상태 그대로. 재기동하지 않았다.

## 판정

학습 자체는 PASS:

- 20,000 step 완료
- final checkpoint 저장 완료
- loss 안정 하강
- OOM / NaN / traceback 없음

deploy 또는 live 후보 판정은 아직 보류:

- HF push 미수행
- checkpoint별 inference/gate/live feasibility 미실행
- 020000은 train loss 기준 후보일 뿐, 운영 후보로 확정하지 않는다.

## 다음 작업 후보

1. TensorBoard에서 002000~020000 구간 loss/gradient 곡선 확인 후 평가 대상 checkpoint shortlist 선정.
2. 선택한 checkpoint의 local inference smoke 또는 metadata 검증 수행.
3. 필요 시 best checkpoint를 `KETI-IRRC/pi05_openarm_handover_v0_alpha`로 수동 push.
4. Track A가 필요하면 8766/8765 serving을 선택 checkpoint로 재기동하되, 학습 결과 리뷰 후 별도 지시로 진행.
