#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$APP_DIR/.." && pwd)"
TOOLS_DIR="$PROJECT_DIR/.local-tools"
UV="$TOOLS_DIR/bin/uv"
VENV="$PROJECT_DIR/venv"
PYTHON="$VENV/bin/python"

export UV_PYTHON_INSTALL_DIR="$TOOLS_DIR/python"
export UV_CACHE_DIR="$TOOLS_DIR/cache"
export UV_PYTHON_BIN_DIR="$TOOLS_DIR/bin"
export PYTHONPATH="$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"

if [[ ! -x "$UV" ]]; then
  command -v curl >/dev/null 2>&1 || { echo 'curl é necessário para baixar o gerenciador uv.' >&2; exit 1; }
  mkdir -p "$TOOLS_DIR/bin"
  INSTALLER="$(mktemp)"
  trap 'rm -f "$INSTALLER"' EXIT
  curl -LsSf https://astral.sh/uv/install.sh -o "$INSTALLER"
  UV_UNMANAGED_INSTALL="$TOOLS_DIR/bin" sh "$INSTALLER"
  rm -f "$INSTALLER"
  trap - EXIT
fi

# O projeto exige Python >=3.12,<3.14; o Python gerenciado fica somente nesta pasta.
if [[ ! -x "$PYTHON" ]] || ! "$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 13)' 2>/dev/null; then
  echo 'Criando ambiente virtual com Python 3.13...'
  "$UV" venv --python 3.13 --clear "$VENV"
fi

echo 'Instalando ou atualizando as dependências declaradas em pyproject.toml...'
"$UV" pip install --python "$PYTHON" "$PROJECT_DIR"
"$PYTHON" -c 'import scipy; from RUFAS.biophysical.animal.ration.ration_optimizer import RationOptimizer' \
  || { echo 'Não foi possível carregar o otimizador RuFaS.' >&2; exit 1; }

echo "NutriPlan: http://127.0.0.1:${PORT:-8765}"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:${PORT:-8765}" >/dev/null 2>&1 || true
fi
cd "$APP_DIR"
exec "$PYTHON" server.py
