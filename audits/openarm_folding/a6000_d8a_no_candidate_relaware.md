# a6000 D-8a relstats-aware no-candidate 판정

## 결론

D-8a continuation `001000`~`012000` 중 deploy candidate는 없다.

## 근거

- level2 corrected `004000` 회귀: recipe PASS, replay PASS
- D-8a `001000`~`012000`: relstats-aware recipe PASS
- D-8a `001000`~`012000`: relstats-aware replay FAIL
- replay 실패 원인: delta ratio 하한 미달과 raw normalized arm target error 초과

## 다음 선택지

1. D-8b fold-only subset 재학습으로 데이터 노이즈 가설을 검증한다.
2. D-8a 추가 step을 계속할지 결정한다. 단, `012000`까지 replay 개선이 deploy 수준에 도달하지 못했다.
3. full_folding recipe 자체 또는 task variant 혼합 문제를 별도 결정 항목으로 다룬다.

현재 level2 corrected `004000`만 deploy 경로에 남는다. full_folding D-8a checkpoint는 서빙 전환 대상이 아니다.
