# Manual de Demo - 3 a 5 minutos

## Objetivo

Mostrar que a IsyShell reduz o acesso manual via SSH e padroniza a execucao segura de scripts por cliente, com auditoria e metricas.

## Preparacao

Suba a API:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Abra:

```text
http://127.0.0.1:8000/docs
```

Clique em `Authorize` e informe o token atual.

## Roteiro

1. Contexto do problema

Explique: hoje a operacao precisa acessar servidores por SSH para executar rotinas como limpeza, backup, status de containers e provisionamento.

2. Health e Info

Abra:

```text
GET /health
GET /api/v1/info
```

Mostre ambiente, versao, banco e URLs operacionais.

3. Clientes e scripts

Execute:

```text
GET /api/v1/clients
GET /api/v1/scripts
GET /api/v1/clients/{client_id}/scripts
```

Explique que o cliente so executa scripts vinculados explicitamente.

4. Execucao segura

Execute:

```text
POST /api/v1/scripts/{script_id}/execute
```

Body exemplo:

```json
{
  "client_id": 1,
  "params": ["cliente01", "cliente01.isy.one", "8155"],
  "confirm": "EXECUTAR"
}
```

Reforce: sem comando livre, sem `shell=True`, parametros validados e confirmacao obrigatoria.

5. Auditoria e metricas

Execute:

```text
GET /api/v1/logs
GET /api/v1/metrics
```

Mostre `stdout`, `stderr`, `return_code`, `duration_ms`, fingerprint do token e taxa de sucesso.

6. Regeneracao de token

Execute:

```text
POST /api/v1/auth/token/regenerate
```

Body:

```json
{
  "confirm": "REGENERAR_TOKEN"
}
```

Explique que o token novo aparece apenas uma vez e que o token antigo deixa de funcionar.

## Fechamento

A solucao reduz risco operacional, padroniza execucao, cria rastreabilidade e escala para dezenas de clientes sem liberar comando livre para o operador.
