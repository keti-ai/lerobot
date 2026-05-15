# a6000 D-8a 진행 상태

마지막 갱신: 2026-05-15T16:35:14+09:00
학습 시작: 20260515_163251
run log: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/audits/d8a_run_20260515_163251.log
checkpoint 디렉토리: /data/keti/syh/lerobot_openarm_folding/a6000_prep_20260511/train/pi05_openarm_full_folding_continue003000_torch27_pyav_20260515/checkpoints

진행 현황:
- 현재 step: 초기화 중, 첫 train step 로그 전
- 최근 loss: 아직 없음
- GPU: 4x RTX A6000, python worker 4개 실행, memory 508/539/491/539 MiB, util 0%

다음 checkpoint 예정: run-local 001000
다음 gate 예정 ckpt: 아직 없음

주의:
- torch 2.7.1+cu126 / cuDNN 90501 venv 사용.
- `dataset.video_backend=pyav` 유지.
- gate 통과 전 deploy 후보 표기 금지.
