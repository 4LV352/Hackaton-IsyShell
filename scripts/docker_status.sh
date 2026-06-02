#!/bin/bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Uso: docker_status.sh <cliente>"
  exit 1
fi

cliente="$1"

if [[ ! "$cliente" =~ ^[a-zA-Z0-9_-]{1,32}$ ]]; then
  echo "Cliente invalido."
  exit 1
fi

echo "[1/3] Validando contexto do cliente: $cliente"
echo "[2/3] Simulando consulta aos containers Docker"
echo "[3/3] Simulacao de status concluida com sucesso"
exit 0
