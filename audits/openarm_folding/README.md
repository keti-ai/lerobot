# OpenArm Folding Audit Index

이 디렉토리는 OpenArm folding audit 산출물과 gate 도구를 보관한다.

## 운영 정보

- 현재 전략/결정 항목: `docs/PLAN.md`
- 현재 상태/다음 작업: `docs/STATUS.md`
- 에이전트용 운영 포인터: `AGENTS.md`
- 종료된 historical 작업: `docs/_archive/openarm_folding/`, `docs/_archive/INDEX.md`

## 현역 파일

- `stage22_dataset_replay_and_ablation.py` — dataset replay gate 도구
- `stage29_candidate_recipe_gate.py` — candidate recipe gate 도구
- `a6000_live_policy_server.py` — A6000 live policy server, port 8766
- `a6000_snapshot_policy_server.py` — A6000 snapshot policy server, port 8765
- `a6000_*.md` — a6000 측 진행/진단 ping 파일

## Archive 기준

2026-05-19 이후 syhlabtop custom rollout harness, viewer/client, Track A trial report,
legacy Track D 계획 문서는 현역 경로가 아니라 archive 로 보존한다. 새 live rollout
기준은 official `lerobot-rollout` baseline 이며, 세부 준비 상태는 `docs/PLAN.md`를
참조한다.
