# LaranBot 🍊 — Boilerplate / Template

Um ponto de partida pronto para criar um chatbot pessoal no Telegram, rodando em **Cloudflare Workers (Python) + FastAPI**.

> **O que isto é, com precisão:** este repositório é um **boilerplate/template**, não um framework. A diferença importa: você não vai *importar* este código como dependência — você vai **clonar, ler, editar diretamente** o arquivo `src/entry.py`, injetando seu token e sua lógica de comando ali dentro.
>
> **Para quem é:** para quem quer aprender ou utilizar Cloudflare Workers, Python serverless e integração com a API do Telegram lendo e mexendo em um exemplo funcional completo — sozinho ou com apoio de uma IA guiando a leitura — sem precisar entender conceitos de arquitetura de frameworks (roteadores, injeção de dependência, pacotes instaláveis) antes de começar.

Este README é um tutorial completo: se você nunca tocou nesse repositório, seguindo ele do início ao fim você sai com o bot rodando na sua máquina.

---

## Índice

1. [O que é este projeto](#o-que-é-este-projeto)
2. [Pré-requisitos](#pré-requisitos)
3. [Primeiros passos (clonar e instalar)](#primeiros-passos-clonar-e-instalar)
4. [Configurando os segredos (.dev.vars)](#configurando-os-segredos-devvars)
5. [Rodando localmente (npm run dev)](#rodando-localmente-npm-run-dev)
6. [Testando localmente com Invoke-RestMethod](#testando-localmente-com-invoke-restmethod)
7. [Banco de dados D1 (local vs. remoto)](#banco-de-dados-d1-local-vs-remoto)
8. [npm run dev vs. npm run deploy](#npm-run-dev-vs-npm-run-deploy)
9. [Deploy em produção](#deploy-em-produção)
10. [Comandos disponíveis no bot](#comandos-disponíveis-no-bot)
11. [Endpoints HTTP disponíveis](#endpoints-http-disponíveis)
12. [Estrutura do projeto](#estrutura-do-projeto)
13. [Decisões de design](#decisões-de-design)
14. [Problemas comuns](#problemas-comuns)
15. [Próximos passos](#próximos-passos)

---

## O que é este projeto

O LaranBot reúne, num só lugar, ferramentas úteis no dia a dia, acessíveis a qualquer momento diretamente pelo chat do Telegram. A arquitetura — Cloudflare Workers rodando Python, FastAPI embutido via ponte ASGI, persistência via Cloudflare D1 — está inteira dentro de um único arquivo, `src/entry.py`, de propósito: o objetivo é que você consiga ler o bot inteiro de cima a baixo, sem pular entre módulos.

Hoje o projeto já tem, funcionando de ponta a ponta:
- Recebimento de mensagens do Telegram via webhook
- Comandos de chat (`/start`, `/myid`, `/ia`, `/todo`)
- Botões inline (teclado de clique) no `/start`, com tratamento do clique via `callback_query`
- Um recurso de IA rodando direto na infraestrutura da Cloudflare (Workers AI), sem chave de API externa
- Um banco de dados D1 configurado, testado, e ligado ao comando de chat `/todo`

---

## Pré-requisitos

| Ferramenta | Para que serve | Como instalar (Windows/PowerShell) |
|---|---|---|
| **Git** | Clonar o repositório | `winget install --id Git.Git -e` |
| **Node.js** (LTS) | Necessário para o `wrangler`, a CLI oficial da Cloudflare | `winget install OpenJS.NodeJS.LTS` |
| **uv** | Gerencia o Python, o ambiente virtual, e instala o `pywrangler` automaticamente | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

Você **não** precisa instalar Python manualmente — o `uv` resolve a versão certa (3.12, conforme `.python-version`) sozinho. Feche e reabra o terminal depois de instalar os três.

---

## Primeiros passos (clonar e instalar)

```powershell
git clone https://github.com/laranjodupy/LaranBotDev_Telegram.git
cd LaranBot_Telegram
npm install   # baixa o wrangler (CLI da Cloudflare)
uv sync       # instala fastapi, workers-py, workers-runtime-sdk; cria .venv/
```

> **Dica de editor:** aponte a extensão Python do seu editor (ex.: VS Code) para a pasta `.venv` criada pelo `uv sync`, para ter autocomplete funcionando.

---

## Configurando os segredos (.dev.vars)

O projeto usa um `BOT_TOKEN` (gerado pelo [@BotFather](https://t.me/BotFather)) para se autenticar na API do Telegram. **Nunca** deve ir para o Git.

```powershell
Copy-Item .dev.vars.example .dev.vars
```

Abra o `.dev.vars` e cole seu token:
```
BOT_TOKEN=seu_token_aqui
```

Onde conseguir: fale com o [@BotFather](https://t.me/BotFather), use `/newbot` (bot novo) ou `/mybots` → seu bot → **API Token** (bot existente).

⚠️ **Se o token vazar**, trate como comprometido: `/revoke` no BotFather, gere um novo, atualize o `.dev.vars`. Não existe "desfazer" — só revogar.

---

## Rodando localmente (npm run dev)

```powershell
npm run dev
```

Você deve ver:
```
Using secrets defined in .dev.vars
Your Worker has access to the following bindings:
Binding              Resource            Mode
env.DB (laranbot-db) D1 Database         local
env.AI               AI                  ...
env.BOT_TOKEN        Environment Variable local

○ Starting local server...
[wrangler:info] Ready on http://127.0.0.1:8787
```

**Deixe esse terminal aberto** — é nele que aparecem os `print()` do seu código e qualquer erro/traceback.

---

## Testando localmente com Invoke-RestMethod

Com `npm run dev` rodando (Terminal 1), abra um **segundo terminal**.

**⚠️ Sintaxe de aspas importa no PowerShell:** aspas simples por fora do JSON, duplas por dentro, sem `\"` — evita um bug clássico de corrupção do corpo da requisição.

```powershell
# Health check
Invoke-RestMethod -Uri http://localhost:8787/

# Simular uma mensagem do Telegram
Invoke-RestMethod -Uri http://localhost:8787/webhook -Method Post -ContentType "application/json" -Body '{"update_id": 1, "message": {"chat": {"id": SEU_CHAT_ID}, "text": "/start"}}'
```

Troque `"text"` por `/myid`, `/ia sua pergunta`, `/todo`, `/todo add Comprar café`, `/todo done 1` ou `/todo del 1` para testar os outros comandos.

Para simular o **clique num botão** (callback_query), o formato é diferente de uma mensagem de texto:
```powershell
Invoke-RestMethod -Uri http://localhost:8787/webhook -Method Post -ContentType "application/json" -Body '{"update_id": 2, "callback_query": {"id": "1", "data": "myid", "message": {"chat": {"id": SEU_CHAT_ID}}}}'
```

### Rotas de tarefas (`/todos`)

> ⚠️ `concluir`/`remover` exigem `?chat_id=` — sem isso, qualquer pessoa que soubesse o `id` de uma tarefa poderia alterar a de outro usuário. Ver [Decisões de design](#decisões-de-design).

```powershell
Invoke-RestMethod -Uri http://localhost:8787/todos -Method Post -ContentType "application/json" -Body '{"chat_id": SEU_CHAT_ID, "texto": "Comprar cafe"}'
Invoke-RestMethod -Uri "http://localhost:8787/todos?chat_id=SEU_CHAT_ID"
Invoke-RestMethod -Uri "http://localhost:8787/todos/1/concluir?chat_id=SEU_CHAT_ID" -Method Post
Invoke-RestMethod -Uri "http://localhost:8787/todos/1?chat_id=SEU_CHAT_ID" -Method Delete
```

> Essas rotas HTTP existem **além** do comando `/todo` no chat, para testar o banco isoladamente. O SQL está escrito duas vezes no projeto (rotas + comando) — decisão intencional, ver seção seguinte.

---

## Banco de dados D1 (local vs. remoto)

**Local e remoto são bancos completamente separados**, mesmo com o mesmo binding.

```powershell
uv run pywrangler d1 migrations apply laranbot-db --local
uv run pywrangler d1 execute laranbot-db --local --command "SELECT * FROM todos;"
```

Sem `--local`, os comandos afetam o banco **remoto** (produção) — use com atenção. Numa máquina nova, rode `migrations apply --local` de novo (a pasta `.wrangler/` é ignorada pelo Git de propósito).

---

## npm run dev vs. npm run deploy

| | `npm run dev` | `npm run deploy` |
|---|---|---|
| **O que faz** | Servidor local | Publica na Cloudflare de verdade |
| **URL** | `http://localhost:8787` | `https://laranbot.SEU-SUBDOMINIO.workers.dev` |
| **Banco D1** | Local | Remoto (produção) |
| **Telegram chama?** | Não (precisa HTTPS público) | Sim |
| **Comando real** | `uv run pywrangler dev` | `uv run pywrangler deploy` |

---

## Deploy em produção

```powershell
uv run pywrangler login                                  # 1. autentica a máquina
uv run pywrangler secret put BOT_TOKEN                    # 2. secret de produção
uv run pywrangler d1 migrations apply laranbot-db --remote  # 3. migration remota
npm run deploy                                             # 4. publica, mostra a URL
```

**5. Configure o webhook:**
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<SEU_TOKEN>/setWebhook?url=https://SEU-WORKER.workers.dev/webhook"
```

**6. Confirme:**
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<SEU_TOKEN>/getWebhookInfo"
```

---

## Comandos disponíveis no bot

| Comando | O que faz |
|---|---|
| `/start` | Boas-vindas + botão inline "Meu Id" |
| `/myid` | Retorna o `chat_id` de quem enviou (via comando **ou** clique no botão) |
| `/ia [pergunta]` | Envia à Cloudflare Workers AI e responde |
| `/todo` | Lista as tarefas do chat |
| `/todo add <texto>` | Cria uma tarefa |
| `/todo done <id>` | Marca como concluída |
| `/todo del <id>` | Remove |

---

## Endpoints HTTP disponíveis

| Rota | Método | O que faz |
|---|---|---|
| `/` | GET | Health check |
| `/webhook` | POST | Recebe updates do Telegram (mensagens **e** cliques de botão) |
| `/todos` | POST | Cria tarefa (`chat_id`, `texto`) |
| `/todos?chat_id=` | GET | Lista tarefas |
| `/todos/{id}/concluir?chat_id=` | POST | Conclui (exige dono) |
| `/todos/{id}?chat_id=` | DELETE | Remove (exige dono) |

---

## Estrutura do projeto

```
LaranBot_Telegram/
├── src/
│   └── entry.py              # TUDO: Worker + FastAPI + rotas + lógica de todos os comandos
├── migrations/                 # Schema versionado do banco D1
├── wrangler.jsonc               # Bindings: DB, AI; nome; compatibility
├── pyproject.toml               # Dependências Python
├── package.json                 # Dependências Node e scripts
├── .dev.vars.example             # Modelo de variáveis (versionado)
├── .dev.vars                     # Variáveis reais (NÃO versionado)
├── .python-version               # Fixa Python 3.12
├── AGENTS.md                      # Instruções para IAs que editarem este repo
└── LaranBot_Documentacao.docx       # Raciocínio, decisões, histórico
```

---

## Decisões de design

**1. Tudo inline, sem função separada por comando.** Cada comando é um bloco `if` dentro de `telegram_webhook`, de propósito — você lê o arquivo inteiro sem pular entre funções. Exceção: `send_message`, `perguntar_ia` (chamadas de API externa, reaproveitadas por vários comandos).

**2. SQL duplicado entre `/todos` (HTTP) e `/todo` (chat).** As rotas HTTP existem para testar o D1 isolado, sem depender do Telegram. Custo assumido: mudar o schema exige editar em dois lugares.

**3. Botões e comandos convivem no mesmo `if`/`if callback:`.** `message` e `callback_query` nunca vêm juntos no mesmo update do Telegram — por isso são dois blocos separados, não uma extensão um do outro.

---

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Invoke-RestMethod : Impossível conectar-se ao servidor remoto` | `npm run dev` não está rodando | Confira o Terminal 1, rode de novo |
| `405 Method Not Allowed` no navegador | Normal — rota só aceita POST | Teste com `Invoke-RestMethod` |
| `401 Unauthorized` | Token desatualizado no `.dev.vars` | Atualize e **reinicie** `npm run dev` |
| `AiError: ... deprecated` | Modelo saiu do catálogo | Troque a string do modelo em `entry.py` |
| Erro de parsing no `wrangler.jsonc` | Falta vírgula entre blocos | Revise `}`/`]` seguidos de `"chave"` sem vírgula |
| Botão fica "carregando" travado | `answerCallbackQuery` não foi chamado a tempo | Confira se `responder_callback` está sendo chamado no bloco `if callback:` |
| `/todos/{id}/concluir` não muda nada | Faltou `?chat_id=`, ou não é o dono | Não gera erro nesse caso — confira o `chat_id` |

---

## Próximos passos

- Confirmar deploy final e `setWebhook` em produção
- Consulte `LaranBot_Documentacao.docx` para o raciocínio completo por trás de cada decisão
