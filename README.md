# isy-shell-api

API REST corporativa da ISY.ONE para substituir o acesso manual por SSH e executar scripts Bash autorizados de forma segura, auditável e padronizada.

## Problema

A operação atual exige acesso manual aos servidores dos clientes para limpeza de logs, checagem de containers, provisionamento e rotinas de backup. Isso gera risco operacional, baixa rastreabilidade e dependência de intervenção humana.

## Solucao

O `isy-shell-api` centraliza a execução dos scripts em uma API FastAPI com PostgreSQL, auditoria completa e proteção contra `command injection`. O usuário não envia comandos livres, apenas parâmetros validados para scripts previamente cadastrados.

## Mensagem de Demo

### Problema

Hoje a operação precisa acessar servidores por SSH para executar scripts.

### Solucao

Criamos uma API segura para executar scripts autorizados por cliente.

### Seguranca

- sem `shell=True`
- sem comando livre
- parâmetros validados
- token obrigatório
- vínculo cliente-script
- redaction nos logs

### Demo

1. Abrir `/docs`
2. Listar clientes
3. Listar scripts
4. Listar scripts permitidos para um cliente
5. Executar um script
6. Consultar logs
7. Consultar métricas

### Fechamento

`A solução reduz risco operacional, padroniza execução, cria rastreabilidade e escala para dezenas de clientes.`

## Arquitetura

- `FastAPI` expõe os endpoints REST em `/api/v1`
- `SQLAlchemy` modela o PostgreSQL
- `Pydantic` valida payloads e respostas
- `subprocess.run()` executa scripts `.sh` sem `shell=True`
- `Docker` e `Docker Compose` isolam API e banco
- `./scripts` é montado em `/opt/isyone/scripts`

## Estrutura

```text
isy-shell-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── security.py
│   ├── dependencies.py
│   ├── routers/
│   └── services/
├── scripts/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Modelo do banco

### `clients`
- `id`
- `name`
- `slug`
- `domain`
- `active`
- `created_at`
- `updated_at`

### `scripts`
- `id`
- `name`
- `filename`
- `description`
- `allowed_params_schema`
- `active`
- `created_at`
- `updated_at`

### `client_scripts`
- `id`
- `client_id`
- `script_id`
- `active`
- `created_at`

### `execution_logs`
- `id`
- `client_id`
- `script_id`
- `client_name`
- `script_name`
- `params`
- `status`
- `stdout`
- `stderr`
- `return_code`
- `duration_ms`
- `requester_ip`
- `token_fingerprint`
- `executed_at`

### `settings`
- `id`
- `key`
- `value`
- `updated_at`

## Como rodar

### Local sem Docker

Use este modo para desenvolvimento no Windows com SQLite.

1. Copie o exemplo de ambiente:

```powershell
Copy-Item .env.example .env
```

2. Crie e ative um ambiente virtual, depois instale as dependências:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Garanta que o `.env` esteja com:

```env
ENVIRONMENT=development
SCRIPT_BASE_PATH=./scripts
```

4. Suba a API localmente:

```powershell
$env:ENVIRONMENT="development"
python -m uvicorn app.main:app --reload
```

5. Se quiser executar os scripts `.sh` no Windows sem Docker, instale Git Bash, MSYS2 ou WSL e deixe `bash` disponível no `PATH`.
   - Opcionalmente, defina `BASH_EXECUTABLE` com o caminho completo do executável, por exemplo:

```powershell
$env:BASH_EXECUTABLE="C:\\Program Files\\Git\\bin\\bash.exe"
```

6. Acesse:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Com Docker

1. Suba com Docker Compose:

```bash
docker compose up --build
```

2. Acesse:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Configuracao `.env`

```env
ENVIRONMENT=development
DATABASE_URL=postgresql://isy:isy@postgres:5432/isy_shell
ISY_API_TOKEN=change-me-token
SCRIPT_BASE_PATH=./scripts
SCRIPT_TIMEOUT_SECONDS=120
```

### Regra de ambiente

- `ENVIRONMENT=development` usa SQLite automaticamente e aponta para `./scripts`.
- `ENVIRONMENT=production` usa PostgreSQL e o caminho `/opt/isyone/scripts`.
- O Docker Compose define `ENVIRONMENT=production` na API.
- Em desenvolvimento, `DATABASE_URL` é ignorada porque o banco ativo é SQLite local.

## Autenticacao

Todos os endpoints protegidos exigem:

```http
X-Isy-Token: change-me-token
```

O token é persistido na tabela `settings`, carregado no startup e pode ser alterado pelo endpoint de settings. A API nunca retorna o token puro.

## Seed inicial

Ao iniciar, a API cria automaticamente:

- token inicial, se não existir
- `Faculdade XPTO`
- `Loja Alpha`
- `Clínica Beta`
- scripts de exemplo
- relacionamento `client_scripts` controlado e explícito:
  - `Faculdade XPTO`: `provisionar`, `docker_status`, `cleanup_logs`
  - `Loja Alpha`: `docker_status`, `backup`
  - `Clínica Beta`: `cleanup_logs`, `backup`

O seed não libera todos os scripts para todos os clientes. Cada vínculo precisa ser definido de forma explícita para reduzir risco operacional e refletir um controle mais próximo do cenário real.

## Endpoints

### Saúde
- `GET /health`

### Scripts
- `GET /api/v1/scripts`
- `POST /api/v1/scripts`
- `GET /api/v1/scripts/{script_id}`
- `PUT /api/v1/scripts/{script_id}`
- `PATCH /api/v1/scripts/{script_id}/activate`
- `PATCH /api/v1/scripts/{script_id}/deactivate`
- `POST /api/v1/scripts/{script_id}/execute`

### Clientes
- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PUT /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}/activate`
- `PATCH /api/v1/clients/{client_id}/deactivate`

### Vínculo cliente-script
- `GET /api/v1/clients/{client_id}/scripts`
- `POST /api/v1/clients/{client_id}/scripts/{script_id}`
- `DELETE /api/v1/clients/{client_id}/scripts/{script_id}`
- `PATCH /api/v1/clients/{client_id}/scripts/{script_id}/activate`
- `PATCH /api/v1/clients/{client_id}/scripts/{script_id}/deactivate`

### Logs e métricas
- `GET /api/v1/logs`
- `GET /api/v1/logs/{log_id}`
- `GET /api/v1/metrics`

### Token
- `GET /api/v1/settings/token`
- `PUT /api/v1/settings/token`

## Como cadastrar cliente

```bash
curl -X POST http://localhost:8000/api/v1/clients \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: change-me-token" \
  -d '{
    "name": "Novo Cliente",
    "domain": "novo.exemplo.com",
    "active": true
  }'
```

## Como cadastrar script

```bash
curl -X POST http://localhost:8000/api/v1/scripts \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: change-me-token" \
  -d '{
    "name": "provisionar",
    "filename": "provisionar.sh",
    "description": "Provisionamento simulado",
    "allowed_params_schema": {
      "type": "array",
      "items": [
        {"name": "cliente", "pattern": "^[a-zA-Z0-9_-]{1,32}$"},
        {"name": "dominio", "pattern": "^[a-zA-Z0-9.-]{1,253}$"},
        {"name": "porta", "pattern": "^[0-9]{2,5}$"}
      ]
    },
    "active": true
  }'
```

## Como liberar script para cliente

Listar vínculos do cliente:

```bash
curl -H "X-Isy-Token: change-me-token" \
  http://localhost:8000/api/v1/clients/1/scripts
```

Liberar um script para um cliente:

```bash
curl -X POST http://localhost:8000/api/v1/clients/1/scripts/3 \
  -H "X-Isy-Token: change-me-token"
```

Remover o vínculo do script com o cliente:

```bash
curl -X DELETE http://localhost:8000/api/v1/clients/1/scripts/3 \
  -H "X-Isy-Token: change-me-token"
```

Ativar vínculo existente:

```bash
curl -X PATCH http://localhost:8000/api/v1/clients/1/scripts/3/activate \
  -H "X-Isy-Token: change-me-token"
```

## Como executar script

```bash
curl -X POST http://localhost:8000/api/v1/scripts/3/execute \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: change-me-token" \
  -d '{
    "client_id": 1,
    "params": ["cliente01", "cliente01.isy.one", "8155"]
  }'
```

Resposta de sucesso:

```json
{
  "success": true,
  "status": "success",
  "script": "provisionar",
  "client": "Faculdade XPTO",
  "return_code": 0,
  "stdout": "...",
  "stderr": "",
  "duration_ms": 350,
  "log_id": 1
}
```

Resposta de erro:

```json
{
  "success": false,
  "status": "failed",
  "message": "Script execution failed",
  "return_code": 1,
  "stdout": "...",
  "stderr": "...",
  "log_id": 2
}
```

## Como consultar logs

```bash
curl -H "X-Isy-Token: change-me-token" http://localhost:8000/api/v1/logs
```

## Como alterar token

```bash
curl -X PUT http://localhost:8000/api/v1/settings/token \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: change-me-token" \
  -d '{
    "value": "novo-token-seguro"
  }'
```

## Segurança contra `command injection`

- O usuário nunca envia caminho de script
- Só executa scripts cadastrados e ativos
- O cliente precisa estar ativo
- O vínculo `client_scripts` precisa estar ativo
- O `filename` é validado e resolvido apenas dentro de `/opt/isyone/scripts`
- O comando é montado com lista de argumentos
- `subprocess.run([...], shell=False)` é obrigatório
- Parâmetros passam por regex/lista permitida
- Caracteres de controle são bloqueados
- Timeouts são obrigatórios
- Cada execução gera auditoria em banco
- `stdout` e `stderr` passam por redaction simples antes de persistir
  - `password=...`
  - `passwd=...`
  - `token=...`
  - `secret=...`
  - `api_key=...`
  - `key=...`
- O token não é exposto em respostas
- O log armazena apenas fingerprint do token

## Diferenciais para o hackathon

- Auditoria completa de sucesso, falha, timeout e bloqueios
- Métricas operacionais prontas para dashboard
- Token dinâmico no banco
- Controle por cliente e por script
- Timeout configurável
- Seeds automáticos para demo
- Swagger disponível
- Estrutura em camadas
- Resposta JSON padronizada

## Roteiro de pitch

1. Mostrar o problema: acesso manual via SSH e falta de rastreabilidade.
2. Apresentar a solução: API segura para execução controlada de scripts.
3. Abrir o Swagger e mostrar a lista de scripts e clientes.
4. Executar um script real com parâmetro válido.
5. Abrir os logs e mostrar stdout, stderr, retorno e fingerprint do token.
6. Apontar as métricas e o controle por cliente.
7. Encerrar com os ganhos: segurança, governança e escala para mais de 30 clientes.
