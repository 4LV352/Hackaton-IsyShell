# Manual de Testes Manuais - isy-shell-api

Este manual mostra como iniciar o projeto localmente no Windows e testar a API manualmente pelo Swagger ou por `curl`.

## 1. Pre-requisitos

- Python instalado
- PowerShell
- Git Bash, MSYS2 ou WSL se quiser executar os scripts `.sh` no Windows
- Projeto aberto na pasta:

```powershell
cd "C:\Users\nicol\Desktop\Hackaton API"
```

## 2. Preparar Ambiente

Crie o ambiente virtual se ainda nao existir:

```powershell
python -m venv .venv
```

Instale as dependencias:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Valide se as bibliotecas estao OK:

```powershell
.\.venv\Scripts\python -m pip check
```

Resultado esperado:

```text
No broken requirements found.
```

## 3. Configurar Variaveis Locais

Use modo development para SQLite local:

```powershell
$env:ENVIRONMENT="development"
$env:SCRIPT_BASE_PATH="./scripts"
$env:ISY_API_TOKEN="change-me-token"
```

Se for executar scripts `.sh` no Windows com Git Bash:

```powershell
$env:BASH_EXECUTABLE="C:\Program Files\Git\bin\bash.exe"
```

Se `bash` ja estiver no `PATH`, a variavel `BASH_EXECUTABLE` pode ser omitida.

## 4. Iniciar a API

Use sempre o Python do `.venv`:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

URLs:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## 5. Testar pelo Swagger

1. Abra `http://127.0.0.1:8000/docs`
2. Clique em `Authorize`
3. Informe o token:

```text
change-me-token
```

4. Execute os endpoints no roteiro abaixo.

Depois de regenerar o token, clique em `Authorize` novamente e cole o token novo.

## 6. Roteiro de Teste Manual

### 6.1 Health Check

Endpoint:

```http
GET /health
```

Resultado esperado:

- `success: true`
- `status: success`
- `data.service: isy-shell-api`
- `data.environment: development`
- `data.database_backend: sqlite`

### 6.2 Listar Clientes

Endpoint:

```http
GET /api/v1/clients
```

Header:

```http
X-Isy-Token: change-me-token
```

Resultado esperado:

- `Faculdade XPTO`
- `Loja Alpha`
- `Clínica Beta`

Anote o `id` do cliente que sera usado nos testes.

### 6.3 Listar Scripts

Endpoint:

```http
GET /api/v1/scripts
```

Resultado esperado:

- `cleanup_logs`
- `docker_status`
- `provisionar`
- `backup`

Anote o `id` do script que sera executado.

### 6.4 Listar Scripts Permitidos Para Um Cliente

Endpoint:

```http
GET /api/v1/clients/{client_id}/scripts
```

Exemplo:

```http
GET /api/v1/clients/1/scripts
```

Resultado esperado:

- lista de vinculos cliente-script
- cada item deve ter `client_id`, `script_id`, `script_name` e `active`

Use apenas um `script_id` que esteja ativo para o cliente escolhido.

### 6.5 Executar Script Autorizado

Endpoint:

```http
POST /api/v1/scripts/{script_id}/execute
```

Exemplo para `provisionar`:

```json
{
  "client_id": 1,
  "params": ["cliente01", "cliente01.isy.one", "8155"],
  "confirm": "EXECUTAR"
}
```

Exemplo para `cleanup_logs`, `docker_status` ou `backup`:

```json
{
  "client_id": 1,
  "params": ["cliente01"],
  "confirm": "EXECUTAR"
}
```

Resultado esperado:

- `success: true`
- `status: success`
- `return_code: 0`
- `stdout` preenchido
- `log_id` preenchido

## 7. Testes de Seguranca

### 7.1 Token Ausente

Execute qualquer endpoint protegido sem `X-Isy-Token`.

Resultado esperado:

```json
{
  "success": false,
  "status": "failed",
  "message": "Header X-Isy-Token is required."
}
```

### 7.2 Token Invalido

Use:

```http
X-Isy-Token: token-errado
```

Resultado esperado:

```json
{
  "success": false,
  "status": "failed",
  "message": "Invalid token."
}
```

### 7.3 Parametro Invalido

Tente executar um script com parametro contendo espaco, caractere proibido ou quantidade errada de parametros.

Exemplo:

```json
{
  "client_id": 1,
  "params": ["cliente invalido"]
}
```

Resultado esperado:

- `success: false`
- `status: failed`
- mensagem de validacao do parametro

### 7.4 Script Nao Permitido Para Cliente

Tente executar um `script_id` que nao aparece em:

```http
GET /api/v1/clients/{client_id}/scripts
```

Resultado esperado:

- `success: false`
- `message: Script not allowed for this client`

### 7.5 Acao Critica Sem Confirmacao

Tente executar script sem `confirm` ou com valor errado:

```json
{
  "client_id": 1,
  "params": ["cliente01"],
  "confirm": "ERRADO"
}
```

Resultado esperado:

- `success: false`
- `status: failed`
- `message: Confirmation required: EXECUTAR.`

## 8. Consultar Logs

Endpoint:

```http
GET /api/v1/logs
```

Resultado esperado:

- registros das execucoes
- `stdout` e `stderr`
- `requester_ip`
- `token_fingerprint`
- `duration_ms`

Consultar log especifico:

```http
GET /api/v1/logs/{log_id}
```

## 9. Consultar Metricas

Endpoint:

```http
GET /api/v1/metrics
```

Resultado esperado:

- `total_executions`
- `successful_executions`
- `failed_executions`
- `success_rate`
- `average_duration_ms`
- `executions_today`
- `last_script_executed`
- `active_clients`
- `active_scripts`

## 10. Regenerar Token

Endpoint:

```http
POST /api/v1/auth/token/regenerate
```

Header:

```http
X-Isy-Token: token-atual
```

Body:

```json
{
  "confirm": "REGENERAR_TOKEN"
}
```

Resultado esperado:

- `success: true`
- `token` com o novo token gerado
- `token_fingerprint`

Copie o token novo nessa resposta. Ele nao sera exibido novamente.

Depois disso:

1. Clique em `Authorize` no Swagger.
2. Substitua o token antigo pelo novo.
3. Teste `GET /api/v1/clients`.
4. Confirme que o token antigo nao funciona mais.

## 11. Testes por Curl

Listar clientes:

```powershell
curl.exe -H "X-Isy-Token: change-me-token" http://127.0.0.1:8000/api/v1/clients
```

Listar scripts:

```powershell
curl.exe -H "X-Isy-Token: change-me-token" http://127.0.0.1:8000/api/v1/scripts
```

Listar scripts permitidos para o cliente `1`:

```powershell
curl.exe -H "X-Isy-Token: change-me-token" http://127.0.0.1:8000/api/v1/clients/1/scripts
```

Executar script:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/scripts/3/execute" `
  -H "Content-Type: application/json" `
  -H "X-Isy-Token: change-me-token" `
  -d "{\"client_id\":1,\"params\":[\"cliente01\",\"cliente01.isy.one\",\"8155\"],\"confirm\":\"EXECUTAR\"}"
```

Regenerar token:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/auth/token/regenerate" `
  -H "Content-Type: application/json" `
  -H "X-Isy-Token: change-me-token" `
  -d "{\"confirm\":\"REGENERAR_TOKEN\"}"
```

Consultar logs:

```powershell
curl.exe -H "X-Isy-Token: change-me-token" http://127.0.0.1:8000/api/v1/logs
```

Consultar metricas:

```powershell
curl.exe -H "X-Isy-Token: change-me-token" http://127.0.0.1:8000/api/v1/metrics
```

## 12. Rodar Testes Automatizados

```powershell
.\.venv\Scripts\python -m pytest tests -q
```

Resultado esperado:

```text
13 passed
```

Warnings de deprecacao podem aparecer e nao impedem a execucao.

## 13. Problemas Comuns

### ModuleNotFoundError: No module named 'fastapi'

Voce esta usando o Python errado. Rode com:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

### Scripts .sh nao executam no Windows

Instale Git Bash, MSYS2 ou WSL e configure:

```powershell
$env:BASH_EXECUTABLE="C:\Program Files\Git\bin\bash.exe"
```

### Porta 8000 ocupada

Use outra porta:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8010
```

### IDs diferentes dos exemplos

Sempre confirme IDs antes:

```http
GET /api/v1/clients
GET /api/v1/scripts
GET /api/v1/clients/{client_id}/scripts
```
