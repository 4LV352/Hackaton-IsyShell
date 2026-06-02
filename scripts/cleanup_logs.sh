#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: cleanup_logs.sh <cliente>"
  exit 1
fi

cliente="$1"

if [[ ! "$cliente" =~ ^[a-zA-Z0-9_-]{1,32}$ ]]; then
  echo "Cliente invalido."
  exit 1
fi

echo "[1/3] Validando cliente: $cliente"
echo "[2/3] Simulando identificacao de logs antigos"
echo "[3/3] Simulando limpeza concluida com sucesso"
exit 0
