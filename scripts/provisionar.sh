#!/bin/bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Uso: provisionar.sh <cliente> <dominio> <porta>"
  exit 1
fi

cliente="$1"
dominio="$2"
porta="$3"

if [[ ! "$cliente" =~ ^[a-zA-Z0-9_-]{1,32}$ ]]; then
  echo "Cliente invalido."
  exit 1
fi

if [[ ! "$dominio" =~ ^[a-zA-Z0-9.-]{1,253}$ ]]; then
  echo "Dominio invalido."
  exit 1
fi

if [[ ! "$porta" =~ ^[0-9]{2,5}$ ]]; then
  echo "Porta invalida."
  exit 1
fi

echo "[1/4] Preparando provisionamento para $cliente"
echo "[2/4] Aplicando dominio $dominio"
echo "[3/4] Aplicando porta $porta"
echo "[4/4] Provisionamento simulado com sucesso"
exit 0
