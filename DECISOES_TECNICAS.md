# Decisoes Tecnicas - isy-shell-api

## Problema Resolvido

Operacoes recorrentes ainda dependem de acesso manual via SSH aos servidores dos clientes. Isso aumenta risco operacional, reduz rastreabilidade e dificulta padronizacao.

O projeto resolve esse problema expondo uma API REST para executar apenas scripts previamente cadastrados, autorizados por cliente e auditados.

## Arquitetura

- `FastAPI` para API REST e Swagger.
- `SQLAlchemy` para persistencia.
- `PostgreSQL` em producao via Docker.
- `SQLite` apenas em desenvolvimento local Windows.
- `scripts/` como diretorio controlado de arquivos `.sh`.
- Camadas separadas para routers, schemas, servicos, modelos e configuracao.

## Decisoes de Seguranca

- Todos os endpoints administrativos usam `X-Isy-Token`.
- O Swagger expõe `Authorize` global para enviar o token sem repetir header manualmente.
- O token inicial vem do `.env` apenas no primeiro seed.
- Depois disso, o valor persistido fica em hash SHA-256.
- Respostas comuns nunca retornam token puro.
- A regeneracao retorna o token novo apenas uma vez.
- Logs armazenam apenas fingerprint do token.
- Execucao exige vinculo cliente-script ativo.
- Acoes criticas exigem confirmacao explicita no body.

## Por Que Nao Usa `shell=True`

`shell=True` permitiria interpretacao pelo shell e ampliaria o risco de command injection.

A API monta o comando como lista de argumentos e executa com `subprocess.run([...], shell=False)`. O usuario nunca envia um comando livre; ele envia apenas parametros validados por schema.

## Por Que Usa Token Hash

Guardar token puro no banco aumenta impacto em caso de leitura indevida da tabela `settings`.

Com hash, a API consegue validar o token recebido sem persistir o segredo original. O fingerprint ainda permite auditoria sem expor o valor sensivel.

## Por Que Usa Confirmacao em Acoes Criticas

Execucao de scripts, desativacao de recursos e regeneracao de token sao acoes com impacto operacional.

O campo `confirm` reduz acionamentos acidentais no Swagger e deixa clara a intencao do operador durante a demo e em uso administrativo.

## Limitacoes Conhecidas

- Nao ha controle de usuarios por perfil; a autenticacao e por token unico.
- Nao ha Alembic/migrations ainda.
- Nao ha fila de execucao ou controle de concorrencia avancado.
- Nao ha rate limit.
- O SQLite e apenas para desenvolvimento local.
- Os scripts de demo simulam operacoes reais.

## Proximos Passos Para Producao

- Adicionar Alembic para migracoes.
- Usar gerenciador de segredos para token inicial.
- Adicionar RBAC por usuario/equipe.
- Adicionar rate limit e auditoria por usuario.
- Integrar metricas com Prometheus/Grafana.
- Criar pipeline CI para testes.
- Revisar retencao e mascaramento de logs conforme politica interna.
