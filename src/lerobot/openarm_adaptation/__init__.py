"""OpenArm fork-specific adaptation utilities.

D-34 사이드 트랙. dataset 분포와 운영 환경 (OpenArm bimanual follower +
RealSense 3 cam) 의 간극을 메우는 preprocessing 함수 컬렉션.

서브패키지:
- vision   : 카메라 입력 정규화 (resize, color match, intrinsic compensation)
- proprio  : joint state 정규화 (offset, range, unit conversion)
- action   : action contract 변환 (relstats transform 등)

plan: docs/STUDY/openarm_adaptation/README.md
SSOT: docs/PLAN.md §5D-34
"""
