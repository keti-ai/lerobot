#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
ENV_SCRIPT="${RSUSB_ENV_SCRIPT:-/home/syhlabtop/workspace/openarm_lerobot/scripts/env_rsusb_py312.sh}"
PYTHON_BIN="${RSUSB_PYTHON:-/home/syhlabtop/workspace/openarm_lerobot/.venv312/bin/python}"

source "${ENV_SCRIPT}"
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

exec "${PYTHON_BIN}" "$@"
