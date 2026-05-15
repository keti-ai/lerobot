# Archive — OpenArm Folding Stage10~40 작업 기록

## 왜 archive 인가

2026-05-11~05-13 기간 동안 Stage10~40 시퀀스로 진행된 OpenArm 폴딩 첫 모션 bringup,
action contract 진단, 학습 recovery, 그리고 Stage35–40 packet 단위 first-write 작업
기록이다. 현재 운영 룰은 `new_stage_numbers: forbidden` 이므로 이 시퀀스는 종료.
사실관계 검증과 디버깅을 위해 git history 와 함께 보존한다.

새 세션이 다음 작업을 결정할 때는 이 디렉토리가 아니라 다음을 참조해야 한다:

- `docs/PLAN.md` — 단일 진실 공급원 (SSOT)
- `docs/STATUS.md` — 현재 상태
- `AGENTS.md` — 운영 룰
- `audits/openarm_folding/` — 현역 운영 문서 + 스크립트

## 카테고리

### Stage10–19 — OpenArm 초기 bringup, 첫 모션 dry-run 스펙
- `stage10_stage11_review_and_blockers_2026-05-11.md` — bringup 블로커 정리
- `stage15_guarded_first_motion_spec_2026-05-11.md` — guarded first motion 스펙
- `stage16_runtime_preflight_spec_2026-05-11.md` — runtime preflight 스펙
- `stage17_execution_packet_spec_2026-05-11.md` — execution packet 스펙
- `stage18_guarded_actuator_write_spec_2026-05-11.md` — actuator write 스펙
- `stage19_first_write_blocked_2026-05-11.md` — 첫 write 블록 기록

### Stage20–29 — action contract 진단 → recipe gate 발견 → 후보 검증
- `stage20_high_overview_camera_trial_2026-05-11.md` — 고시점 카메라 trial
- `stage21_action_contract_diagnosis_2026-05-11.md` — folding_latest 의 action contract 진단
- `stage22_dataset_replay_and_ablation_2026-05-11.md` — dataset replay 첫 실행 결과
- `stage23_checkpoint_processor_contract_2026-05-11.md` — checkpoint processor 검증
- `stage24_normalized_target_probe_2026-05-11.md` — normalized target 진단
- `stage25_level2_training_dataset_replay_2026-05-11.md` — level2 dataset replay
- `stage26_recipe_alignment_2026-05-11.md` — recipe 정렬 검증
- `stage27_folding_recipe_gate_2026-05-11.md`, `stage27_recipe_gate_current_folding_latest_2026-05-11.md` — recipe gate 첫 발견
- `stage28_to_stage32_recovery_runbook_2026-05-11.md` — recovery 계획
- `stage29_candidate_recipe_gate_2026-05-11.md`, `_expanded` — corrected 후보 gate

### Stage30–32 — corrected level2 retrain + snapshot review
- `stage30_gap_and_execution_plan_2026-05-11.md` — 갭 분석
- `stage30_relative_recipe_reference_2026-05-11.md` — 상대 recipe 참조
- `stage31_a6000_retrain_status_and_next_plan_2026-05-12.md` — corrected level2 학습 완료 기록
- `stage32_syhlabtop_a6000_snapshot_review_2026-05-12.md` — A6000 snapshot review
- `stage32_syhlabtop_candidate_transfer_precheck_2026-05-12.md` — 후보 transfer precheck

### Stage33–40 — A6000 serving bridge + packet write 시퀀스
- `stage33_a6000_remote_serving_bridge_plan_2026-05-12.md` — serving bridge 계획
- `stage34_guarded_first_actuator_write_readiness_plan_2026-05-12.md` — first actuator write readiness
- `stage34_guarded_first_motion_dry_run_2026-05-12.md` — dry-run
- `stage34_right_joint4_limit_check_2026-05-12.md` — right_joint4 limit 검증
- `stage35_*` (7개) — first actuator write, no-execute validation, approval drafts, boundary, syhlabtop validation result
- `stage36_a6000_serving_bridge_2026-05-12.md`, `_result` — A6000 serving bridge 가동/결과
- `stage37_served_proposal_actual_write_result_2026-05-12.md`, `_motion_approval_draft` — served packet write #1
- `stage38_actual_write_result_2026-05-13.md`, `_no_send_readiness`, `_operator_motion_approval_draft` — packet write #2
- `stage39_*` (3개) — packet write #3
- `stage40_*` (3개) — packet write #4 (Stage 시리즈 종료)

### Handoff prompts — syhlabtop ↔ A6000 인계 (종료)
- `syhlabtop_a6000_served_snapshot_handoff_prompt_2026-05-12.md`
- `syhlabtop_agent_ready_prompt_2026-05-11.md`
- `syhlabtop_experiment_ready_handoff_prompt_2026-05-12.md`
- `syhlabtop_stage32_no_send_agent_prompt_2026-05-12.md`
- `syhlabtop_stage32_refresh_snapshot_prompt_2026-05-12.md`
- `syhlabtop_stage34_right_joint4_limit_check_prompt_2026-05-12.md`
- `syhlabtop_stage35_artifact_handoff_prompt_2026-05-12.md`
- `syhlabtop_stage35_no_execute_validation_prompt_2026-05-12.md`
- `syhlabtop_stage_guides_2026-05-11.md`
- `syhlabtop_work_prompt_2026-05-11.md`

### 진단 스크립트 (Python, 17개)
- `guarded_first_motion_*.py` (5개) — Stage15-18 dry-run/preflight/packet/write 도구
- `no_send_direction_probe.py` — 방향 probe
- `stage21_action_contract_probe.py` — action contract 진단 도구
- `stage24_normalized_target_probe.py` — normalized target 진단
- `stage30_relative_recipe_reference.py` — 상대 recipe 참조 계산
- `stage35_no_execute_writer_validation.py`, `stage35_guarded_actual_actuator_write.py` — Stage35 first write 도구
- `stage37/38/39/40_guarded_served_proposal_write.py` (4개) — served packet write
- `rollout_trial_guarded_session.py` — 구버전 rollout 세션 (현역은 `audits/openarm_folding/syhlabtop_live_guarded_rollout.py`)
- `create_no_send_snapshot_trial.py` — no-send snapshot 생성기

### JSON 산출물 (8개) — 게이트/probe 출력
- `stage21_action_contract_diagnosis_2026-05-11.json`
- `stage22_dataset_replay_and_ablation_2026-05-11.json`
- `stage24_normalized_target_probe_2026-05-11.json`
- `stage25_level2_training_dataset_replay_2026-05-11.json`
- `stage27_recipe_gate_current_folding_latest_2026-05-11.json`
- `stage29_candidate_recipe_gate_2026-05-11.json`, `_expanded`
- `stage30_relative_recipe_reference_2026-05-11.json`

### 기타 컨텍스트 (12개)
- `timeline_status_2026-05-11.md` — Stage 시간 흐름 (44KB, 전체 timeline)
- `two_machine_pipeline_2026-05-11.md` — 두 머신 파이프라인 설명
- `shared_baseline.md`, `artifact_audit.md`, `body_compat_matrix.md` — 베이스라인 정의
- `a6000_persistent_setup_2026-05-11.md` — A6000 영구 설정 기록
- `experiment_start_brief_2026-05-12.md` — 실험 시작 브리핑
- `renewed_bringup_plan_2026-05-11.md` — 재bringup 계획
- `robot_test_work_spec_2026-05-11.md` — 로봇 테스트 작업 스펙
- `no_send_direction_probe_results_2026-05-11.md` — 방향 probe 결과
- `post_gripper_zero_snapshot_review_2026-05-11.md` — gripper-zero 이후 snapshot review
- `rollout_trial_progressive_session_2026-05-13.md` — progressive rollout 세션 (구버전)
- `syhlabtop_no_nas_fallback_2026-05-11.md` — NAS 미사용 fallback
- `syhlabtop_openarm_lerobot_context_2026-05-11.md` — syhlabtop OpenArm/lerobot 컨텍스트
- `syhlabtop_shadow_action_review_received_2026-05-11.md` — shadow review 수신

## 복원

git mv 로 옮겼으므로 `git log --follow docs/_archive/openarm_folding/<파일>` 로 모든
history 추적 가능. 필요 시 `git mv docs/_archive/openarm_folding/<파일> audits/openarm_folding/`
로 복원 가능.

총 archive 파일 수: **96개** (md 71 + py 17 + json 8).
