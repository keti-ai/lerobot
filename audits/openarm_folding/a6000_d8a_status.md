# a6000 D-8a 진행 상태

마지막 갱신: 2026-05-18T10:50:38+09:00
학습 시작: 20260515_163251
run log: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/d8a_run_20260515_163251.log
checkpoint 디렉토리: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints

진행 현황:
- 상태: 종료됨
- stop_reason: FrameTimestampError
- final_step: 12120 부근
- final_loss: step 12100 loss 0.053, grad_norm 0.481, lr 7.5e-06
- checkpoint: 001000~012000 저장 완료
- gate: 001000~012000 recipe FAIL, replay SKIPPED
- deploy_candidate: 없음
- 실패 지점: `videos/observation.images.right_wrist/chunk-000/file-557.mp4`
- 실패 상세: queried timestamp 1352.2334, loaded timestamps 1352.2000/1352.2333/1352.2667, tolerance 0.0001 초과
- GPU: 학습 프로세스 종료, 4x RTX A6000 idle

다음 checkpoint 예정: 없음
다음 gate 예정 ckpt: 없음

gate 산출물:
- summary: `audits/openarm_folding/a6000_d8a_gate_summary.md`
- no-candidate: `audits/openarm_folding/a6000_d8a_no_candidate.md`
- raw artifacts: `/data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/full_folding_parallel_20260514/audits/d8a_recipe_gate_<step>.{md,json}`

주의:
- torch 2.7.1+cu126 / cuDNN 90501 venv 사용.
- `dataset.video_backend=pyav` 유지.
- gate 통과 전 deploy 후보 표기 금지.
- 재시작 여부는 결정 필요. 임의로 tolerance, dataset, sampler, 코드 변경 금지.
