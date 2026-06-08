# a6000 오버엔지니어링 및 타이밍 점검 — 2026-05-19

## 범위

- serving core: `a6000_live_policy_server.py`, `a6000_snapshot_policy_server.py`
- gate tools: `stage22_dataset_replay_and_ablation.py`, `stage29_candidate_recipe_gate.py`
- repo tracked `a6000_*` 문서
- user-level persistent hook 확인: crontab, user systemd unit, shell profile의 a6000 관련 항목

모션, 학습, serving 재기동, checkpoint 변경은 수행하지 않았다.

## Serving timing review

검색 키워드: `time.sleep`, `asyncio.sleep`, `threading.Timer`, `Event.wait`, `warmup`, `pre_warm`, `dummy_forward`, `ready_after`, `startup_delay`, `retry`, `backoff`, `poll`, `watch`

| 파일:line | 코드 한 줄 | 목적 | 길이(초) | 위치 | 본질적인가? | 권장 |
|---|---|---|---|---|---|---|
| `a6000_snapshot_policy_server.py:235` | `"watched_deltas": {` | 특정 joint delta를 응답 payload에 요약 | N/A | response payload | false positive | timing buffer가 아니므로 보존 |

판정:
- serving request path 또는 main-loop 안에서 `sleep`/`wait`/`retry`/`backoff`/`poll` buffer는 발견되지 않았다.
- `a6000_live_policy_server.py`의 `time.time()`/`time.strftime()`은 latency/timestamp 측정이며 timing buffer가 아니다.
- GPU/model/processor startup warmup 코드는 별도 loop 없이 model load 시점에만 존재한다.

## (a) ping 파일 자동 생성 watcher / cron / daemon

status: not_found

locations:
- 없음

risk:
- `a6000_d8a_status.md`는 수동 ping/status 문서로만 확인된다.

recommendation:
- 현재처럼 수동 갱신 + 수동 commit/push로 운영한다.

patch_applied: no

user_decision_needed: no

## (b) 학습 종료 자동 감지 → 자동 gate 실행 hook

status: not_found

locations:
- 없음

risk:
- `stage22_dataset_replay_and_ablation.py`, `stage29_candidate_recipe_gate.py`는 수동 실행 gate 도구이며 자동 watcher가 아니다.

recommendation:
- 학습 종료 후 사람이 한 번 gate를 트리거하고, 결과 summary를 수동 commit한다.

patch_applied: no

user_decision_needed: no

## (c) 서빙 checkpoint hot-swap / reload

status: not_found

locations:
- 없음

risk:
- live/snapshot server는 startup에서 `--model-dir`를 한 번 load한 뒤 `serve_forever()`로 동작한다. request 중 reload/hot-swap path는 없다.

recommendation:
- feasibility 단계에서는 checkpoint 변경 시 정지 후 재기동을 유지한다.

patch_applied: no

user_decision_needed: no

## (d) HF Hub auto-upload / NAS auto-sync

status: not_found

locations:
- 없음

risk:
- tracked a6000 serving/gate path에 `upload`, `rsync`, auto-sync hook은 없다.

recommendation:
- 필요한 경우 수동 rsync 또는 수동 upload만 사용한다.

patch_applied: no

user_decision_needed: no

## (e) systemd unit / crontab / dotenv 영속 등록

status: found

locations:
- `/home/syh/.bashrc:99` — `export HF_HOME=/mnt/nas/huggingface`
- `/home/syh/.bashrc:172` — `export HF_HOME=/mnt/nas/huggingface`

risk:
- crontab은 `no crontab for syh`, user/system systemd unit은 a6000/OpenArm/LeRobot 관련 파일 없음.
- `.bashrc`의 HF cache 환경변수는 daemon이 아니라 interactive shell 환경 설정이다.

recommendation:
- serving/training daemon 등록은 추가하지 않는다.
- HF offline 실행에는 명령 단위 explicit env export를 계속 사용한다.

patch_applied: no

user_decision_needed: no

## (f) 다단계 retry/backoff/circuit breaker

status: not_found

locations:
- 없음

risk:
- tracked a6000 server/gate path에 exponential backoff 또는 circuit breaker 패턴 없음.

recommendation:
- 장애 시 사용자 수동 재실행 또는 명시적 단순 retry만 사용한다.

patch_applied: no

user_decision_needed: no

## (g) 학습 step 별 자동 checkpoint cleanup / 디스크 정리 cron

status: not_found

locations:
- 없음

risk:
- checkpoint 또는 `/data/.../audits` 산출물을 자동 삭제하는 tracked 코드/cron은 발견되지 않았다.

recommendation:
- 학습 결과 파일은 자동 삭제하지 않는다. cleanup은 사용자 확인 후 수동으로만 수행한다.

patch_applied: no

user_decision_needed: no

## Out-of-scope hits

- `syhlabtop_live_guarded_rollout.py`, `syhlabtop_live_policy_input_viewer.py`의 `time.sleep`/daemon thread hit는 syhlabtop 전용 파일이므로 이번 a6000 작업 범위에서 제외했다.
- `stage22_dataset_replay_and_ablation.py`의 `watched` 변수는 abnormal delta gate용 joint set이며 watcher/daemon이 아니다.

## 단순화 패치 판정

- 즉시 적용 가능한 30줄 이하 a6000 code simplification 후보 없음.
- README 운영 원칙 보강만 적용한다.
- HTTP server, `/health`, RTC metadata, `/predict_live`, model load, processor path는 변경하지 않는다.
