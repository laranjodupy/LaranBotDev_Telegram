# LaranBot 🍊

Chatbot pessoal para Telegram, construído como framework reaproveitável em **Cloudflare Workers (Python) + FastAPI**.

> Este projeto tem duas camadas: **LaranBotDev**, o framework genérico que qualquer pessoa pode usar como base para o próprio bot, e **LaranBot**, a instância pessoal do autor, construída em cima do Dev. Hoje os dois ainda são o mesmo código — a documentação completa dessa divisão está em `LaranBot_Documentacao.docx`, na raiz do repositório.

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
13. [Problemas comuns](#problemas-comuns)
14. [Próximos passos](#próximos-passos)

---

## O que é este projeto

O LaranBot reúne, num só lugar, ferramentas que o desenvolvedor considera úteis no dia a dia, acessíveis a qualquer momento diretamente pelo chat do Telegram. A arquitetura escolhida — Cloudflare Workers rodando Python, com FastAPI embutido via ponte ASGI, e persistência via Cloudflare D1 — funciona tanto para esse uso pessoal quanto como base genérica para outros bots.

Hoje o projeto já tem, funcionando de ponta a ponta:
- Recebimento de mensagens do Telegram via webhook
- Comandos de chat (`/start`, `/myid`, `/ia`)
- Um recurso de IA rodando direto na infraestrutura da Cloudflare (Workers AI), sem chave de API externa
- Um banco de dados D1 configurado e testado (persistência de tarefas), ainda não ligado a um comando de chat

Para o raciocínio completo por trás de cada decisão técnica, veja `LaranBot_Documentacao.docx`. Este README foca só em como rodar e testar o projeto na prática.

---

## Pré-requisitos

Você precisa de três ferramentas instaladas antes de tocar no projeto:

| Ferramenta | Para que serve | Como instalar (Windows/PowerShell) |
|---|---|---|
| **Git** | Clonar o repositório | `winget install --id Git.Git -e` |
| **Node.js** (LTS) | Necessário para o `wrangler`, a CLI oficial da Cloudflare | `winget install OpenJS.NodeJS.LTS` |
| **uv** | Gerencia o Python, o ambiente virtual, e instala o `pywrangler` automaticamente | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

Você **não** precisa instalar Python manualmente — o `uv` resolve a versão certa (3.12, conforme o arquivo `.python-version`) sozinho.

Feche e reabra o terminal depois de instalar os três, para o PATH atualizar.

---

## Primeiros passos (clonar e instalar)

```powershell
git clone <URL_DO_SEU_REPOSITORIO>
cd LaranBot_Telegram
```

Instale as duas metades do projeto — uma em Node, outra em Python:

```powershell
npm install
```
Lê o `package.json` e baixa o `wrangler` (a CLI da Cloudflare) como dependência local.

```powershell
uv sync
```
Lê o `pyproject.toml` e instala tudo que o projeto precisa do lado Python: `fastapi` (dependência de produção) e `workers-py` + `workers-runtime-sdk` (grupo de desenvolvimento — o primeiro fornece o comando `pywrangler`, o segundo dá autocomplete/type hints no editor). Isso também cria a pasta `.venv/` local.

> **Dica de editor:** aponte a extensão Python do seu editor (ex.: VS Code) para a pasta `.venv` criada pelo `uv sync`, para ter autocomplete funcionando.

---

## Configurando os segredos (.dev.vars)

O projeto usa um `BOT_TOKEN` (o token do seu bot, gerado pelo [@BotFather](https://t.me/BotFather) no Telegram) para se autenticar na API do Telegram. Esse valor é sensível — **nunca** deve ir para o Git.

Por isso existem dois arquivos:

- **`.dev.vars.example`** — o modelo, sem valores reais, **este sim é versionado**. Mostra quais variáveis o projeto espera.
- **`.dev.vars`** — o arquivo real, com o token de verdade, **ignorado pelo Git** (confira no `.gitignore` — já está coberto por `.dev.vars*` com exceção explícita pro `.example`).

Crie o seu a partir do modelo:

```powershell
Copy-Item .dev.vars.example .dev.vars
```

Abra o `.dev.vars` e cole seu token:

```
BOT_TOKEN=seu_token_aqui
```

Onde conseguir o token: fale com o [@BotFather](https://t.me/BotFather) no Telegram, use `/newbot` (para criar um bot novo) ou `/mybots` → seu bot → **API Token** (para recuperar o token de um bot existente).

⚠️ **Se esse token vazar** (ex.: aparecer em print, log ou mensagem por engano), trate como comprometido: vá no BotFather, use `/revoke` no bot afetado, gere um novo, e atualize o `.dev.vars`. Não existe "desfazer" um vazamento — só revogar.

---

## Rodando localmente (npm run dev)

```powershell
npm run dev
```

Por baixo dos panos, isso roda `uv run pywrangler dev`. Você deve ver algo assim no terminal:

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

Isso confirma que os três bindings do projeto (`DB`, `AI`, `BOT_TOKEN`) foram reconhecidos. **Deixe esse terminal aberto** — é nele que aparecem os `print()` do seu código Python e qualquer erro/traceback, enquanto você testa em outro terminal.

---

## Testando localmente com Invoke-RestMethod

Com o `npm run dev` rodando (Terminal 1), abra um **segundo terminal** para disparar requisições de teste.

**⚠️ Sintaxe de aspas importa no PowerShell:** sempre aspas simples por fora do JSON, duplas por dentro, sem `\"`. Isso evita um bug clássico onde o PowerShell corrompe o corpo da requisição.

### Testar a rota raiz (health check)
```powershell
Invoke-RestMethod -Uri http://localhost:8787/
```

### Simular uma mensagem do Telegram (`/webhook`)
Primeiro, descubra seu `chat_id` de teste (veja a seção de comandos do bot, ou use `/myid` depois que o bot estiver no ar). Depois:

```powershell
Invoke-RestMethod -Uri http://localhost:8787/webhook -Method Post -ContentType "application/json" -Body '{"update_id": 1, "message": {"chat": {"id": SEU_CHAT_ID}, "text": "/start"}}'
```

Troque `"text": "/start"` por `/myid` ou `/ia sua pergunta aqui` para testar os outros comandos. Se tudo estiver certo, a resposta chega de verdade no seu Telegram — mesmo sem deploy, porque a chamada de **saída** para a API do Telegram não depende de URL pública, só o recebimento via webhook depende.

### Testar as rotas de tarefas (`/todos`)
```powershell
# Criar uma tarefa
Invoke-RestMethod -Uri http://localhost:8787/todos -Method Post -ContentType "application/json" -Body '{"chat_id": SEU_CHAT_ID, "texto": "Comprar cafe"}'

# Listar tarefas de um chat
Invoke-RestMethod -Uri "http://localhost:8787/todos?chat_id=SEU_CHAT_ID"

# Marcar uma tarefa como concluída (troque 1 pelo id real)
Invoke-RestMethod -Uri http://localhost:8787/todos/1/concluir -Method Post

# Remover uma tarefa
Invoke-RestMethod -Uri http://localhost:8787/todos/1 -Method Delete
```

> Essas rotas ainda não estão ligadas a um comando de chat — hoje só são acessíveis via chamada HTTP direta, como nos exemplos acima.

---

## Banco de dados D1 (local vs. remoto)

Uma regra fixa vale para **todo** comando de D1: **local e remoto são bancos completamente separados**, mesmo usando o mesmo binding. O que você cria/insere localmente não aparece em produção, e vice-versa.

O sinal disso na prática é a flag `--local`:

```powershell
# Aplicar o schema (migration) no banco local, usado pelo npm run dev
uv run pywrangler d1 migrations apply laranbot-db --local

# Rodar uma query direta no banco local, para inspecionar dados
uv run pywrangler d1 execute laranbot-db --local --command "SELECT * FROM todos;"
```

Sem `--local`, esses comandos afetam o banco **remoto** (produção) — use com atenção.

Se você clonou o projeto numa máquina nova, o banco local ainda não existe (a pasta `.wrangler/`, onde ele vive, é ignorada pelo Git de propósito). É só rodar o `migrations apply --local` de novo para recriá-lo.

---

## npm run dev vs. npm run deploy

Essa é a distinção mais importante do projeto — misturar os dois é a causa mais comum de confusão:

| | `npm run dev` | `npm run deploy` |
|---|---|---|
| **O que faz** | Sobe um servidor local na sua máquina | Publica o Worker de verdade na Cloudflare |
| **URL** | `http://localhost:8787` (só sua máquina acessa) | URL pública `https://laranbot.SEU-SUBDOMINIO.workers.dev` |
| **Banco D1 usado** | Local (`--local`) | Remoto (produção) |
| **Telegram consegue chamar?** | Não — Telegram precisa de HTTPS público | Sim |
| **Comando por baixo dos panos** | `uv run pywrangler dev` | `uv run pywrangler deploy` |
| **Quando usar** | Desenvolvendo e testando | Quando quiser que o bot funcione de verdade, no Telegram |

Ou seja: você desenvolve e testa tudo com `npm run dev` (rápido, sem afetar produção), e só roda `npm run deploy` quando estiver pronto para o mundo real.

---

## Deploy em produção

Quando estiver pronto para publicar de verdade:

**1. Autentique esta máquina na sua conta Cloudflare** (uma vez por máquina):
```powershell
uv run pywrangler login
```

**2. Configure o secret de produção** (separado do `.dev.vars`, que é só local):
```powershell
uv run pywrangler secret put BOT_TOKEN
```

**3. Aplique as migrations no banco remoto:**
```powershell
uv run pywrangler d1 migrations apply laranbot-db --remote
```

**4. Publique o Worker:**
```powershell
npm run deploy
```
O terminal mostra a URL pública gerada.

**5. Configure o webhook do Telegram, apontando para essa URL:**
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<SEU_TOKEN>/setWebhook?url=https://SEU-WORKER.workers.dev/webhook"
```

**6. Confirme que ficou registrado:**
```powershell
Invoke-RestMethod -Uri "https://api.telegram.org/bot<SEU_TOKEN>/getWebhookInfo"
```

A partir daqui, o bot responde de verdade, para qualquer pessoa que fale com ele no Telegram.

---

## Comandos disponíveis no bot

| Comando | O que faz |
|---|---|
| `/start` | Mensagem de boas-vindas, lista os comandos disponíveis |
| `/myid` | Retorna o `chat_id` de quem enviou — útil para montar testes |
| `/ia [pergunta]` | Envia a pergunta para a Cloudflare Workers AI e responde com o resultado |

---

## Endpoints HTTP disponíveis

Uso interno/desenvolvimento — ainda não ligados a um comando de chat:

| Rota | Método | O que faz |
|---|---|---|
| `/` | GET | Health check |
| `/webhook` | POST | Recebe updates do Telegram (não chame manualmente em produção — é o Telegram quem chama) |
| `/todos` | POST | Cria uma tarefa (`chat_id`, `texto`) |
| `/todos?chat_id=` | GET | Lista as tarefas de um chat |
| `/todos/{id}/concluir` | POST | Marca uma tarefa como concluída |
| `/todos/{id}` | DELETE | Remove uma tarefa |

---

## Estrutura do projeto

```
LaranBot_Telegram/
├── src/
│   ├── entry.py           # Ponto de entrada: Worker + FastAPI + todas as rotas
│   └── funcs.py            # Reservado para futuras funções auxiliares (ainda vazio)
├── migrations/              # Schema versionado do banco D1
│   └── 0001_*.sql
├── wrangler.jsonc           # Configuração do Worker (bindings: DB, AI, nome, compatibility)
├── pyproject.toml           # Dependências Python (fastapi, workers-py, workers-runtime-sdk)
├── package.json             # Dependências Node (wrangler) e scripts (dev, deploy)
├── .dev.vars.example        # Modelo de variáveis de ambiente (versionado)
├── .dev.vars                # Variáveis reais (NÃO versionado — você cria localmente)
├── .python-version          # Fixa a versão do Python (3.12)
├── AGENTS.md                 # Instruções para assistentes de IA que forem editar este repositório
└── LaranBot_Documentacao.docx  # Arquitetura, decisões, escopo e histórico de construção
```

---

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Invoke-RestMethod : Impossível conectar-se ao servidor remoto` | O `npm run dev` não está rodando (ou caiu por erro de config) | Confira o Terminal 1; corrija o erro exibido e rode `npm run dev` de novo |
| `405 Method Not Allowed` ao abrir uma rota no navegador | Normal — a rota só aceita POST, navegador sempre manda GET | Não é bug; teste com `Invoke-RestMethod` |
| `{"ok": false, "error_code": 401, "description": "Unauthorized"}` | Token no `.dev.vars` desatualizado (ex.: após uma rotação) | Confira o token no BotFather, atualize o `.dev.vars`, **reinicie o `npm run dev`** (ele não recarrega o arquivo sozinho) |
| `AiError: ... deprecated` | O modelo de IA usado no código saiu do catálogo da Cloudflare | Veja a lista atual de modelos no dashboard da Cloudflare e troque a string do modelo em `entry.py` |
| Erro de parsing no `wrangler.jsonc` | Falta vírgula entre blocos (JSONC exige vírgula entre "irmãos" de um objeto) | Revise o arquivo procurando por `}` ou `]` seguido diretamente de `"chave"` sem vírgula |
| `getUpdates` retorna resultado vazio | Não há mensagem pendente | Envie uma mensagem para o bot antes de consultar |

---

## Próximos passos

- Ligar as rotas `/todos` a um comando real de chat (ex.: `/todo`)
- Implementar botões inline do Telegram (já especificados na documentação)
- Confirmar deploy final e `setWebhook` em produção
- Consulte `LaranBot_Documentacao.docx` para o roadmap completo, o raciocínio por trás de cada decisão, e o guia de reprodução do processo de construção (seção 4 do documento)