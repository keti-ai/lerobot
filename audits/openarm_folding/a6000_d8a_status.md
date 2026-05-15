# a6000 D-8a 진행 상태

마지막 갱신: 2026-05-15T20:12:08+09:00
학습 시작: 20260515_163251
run log: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/d8a_run_20260515_163251.log
checkpoint 디렉토리: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints

진행 현황:
- 현재 step: 8200 부근 진행 중
- 최근 loss: step 8200 loss 0.056, grad_norm 0.470, lr 1.9e-05, update 1.451s, data 0.005s
- checkpoint: 001000, 002000, 003000, 004000, 005000, 006000, 007000, 008000 저장 완료
- GPU: 4x RTX A6000, memory 47646/47677/47629/47697 MiB, util 69/82/78/75%

다음 checkpoint 예정: run-local 009000
다음 gate 예정 ckpt: 001000~008000

주의:
- torch 2.7.1+cu126 / cuDNN 90501 venv 사용.
- `dataset.video_backend=pyav` 유지.
- gate 통과 전 deploy 후보 표기 금지.
