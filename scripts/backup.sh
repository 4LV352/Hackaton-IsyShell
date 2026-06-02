#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: backup.sh <cliente>"
  exit 1
fi

cliente="$1"

if [[ ! "$cliente" =~ ^[a-zA-Z0-9_-]{1,32}$ ]]; then
  echo "Cliente invalido."
  exit 1
fi

echo "[1/3] Iniciando backup para $cliente"
echo "[2/3] Simulando compressao e envio"
echo "[3/3] Backup simulado concluido com sucesso"
exit 0
