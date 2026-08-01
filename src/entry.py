"""entry.py — LaranBot (boilerplate / template)

Ponto de entrada único do Worker. Este é um boilerplate: um ponto de
partida funcional para clonar e editar diretamente — não um framework
(não há separação entre "núcleo" e "código do usuário", é tudo este
arquivo). Toda a lógica (rotas HTTP, comandos do bot, acesso ao D1,
chamadas à API do Telegram e à Workers AI) mora aqui, de propósito: o
objetivo é que alguém consiga clonar o repositório, ler um arquivo só, e
entender o fluxo completo sem precisar navegar entre módulos.

Arquitetura, em uma frase: o Telegram manda um POST para /webhook -> o
FastAPI processa a rota certa -> a função correspondente chama a API do
Telegram de volta (sendMessage) e/ou consulta o banco D1.
"""

from workers import WorkerEntrypoint, fetch
from fastapi import FastAPI, Request
from pydantic import BaseModel
import json


app = FastAPI()


class Default(WorkerEntrypoint):
    """Classe de entrada exigida pelo runtime dos Cloudflare Workers.

    O nome "Default" e a herança de `WorkerEntrypoint` não são opcionais —
    é assim que o `workerd` (o runtime da Cloudflare) identifica qual
    classe deste arquivo deve tratar as requisições recebidas pelo Worker.
    """

    async def fetch(self, request):
        """Ponto de entrada de TODA requisição HTTP recebida pelo Worker.

        Não contém lógica própria: delega tudo para o FastAPI através da
        ponte ASGI (`asgi.fetch`), que traduz o `Request` nativo do Worker
        para o formato que o FastAPI entende (e vice-versa na resposta).

        Args:
            request: objeto `Request` nativo do runtime da Cloudflare —
                representa a requisição HTTP recebida (headers, corpo,
                método, URL).

        Returns:
            Response: objeto `Response` nativo do Worker, já traduzido a
                partir do que a rota do FastAPI correspondente devolveu.
        """
        import asgi
        return await asgi.fetch(app, request, self.env)


class TodoCreate(BaseModel):
    """Formato esperado no corpo (body) de um POST em /todos.

    O FastAPI usa esta classe para validar automaticamente a requisição
    antes de a rota `criar_todo` ser executada — se `chat_id` não for um
    inteiro, ou se `texto` não vier preenchido, o FastAPI já responde com
    erro 422 sozinho, sem a rota precisar validar nada manualmente.

    Attributes:
        chat_id (int): identificador do chat do Telegram, dono da tarefa.
        texto (str): descrição da tarefa a ser criada.
    """
    chat_id: int
    texto: str


@app.get("/")
async def root() -> dict:
    """Rota de health check (verificação simples de que o Worker está no ar).

    Aceita apenas GET — é a rota que responde normalmente se você abrir a
    URL do Worker direto no navegador.

    Returns:
        dict: mensagem fixa de confirmação, ex.: {"message": "Hello, World!"}.
    """
    return {"message": "Hello, World!"}


@app.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Recebe TODO update que o Telegram envia para este bot.

    É o Telegram quem chama esta rota — nunca o usuário final diretamente.
    A cada mensagem enviada ao bot (ou clique em botão, ver nota abaixo),
    o Telegram faz um POST aqui com um JSON no formato "Update".

    Fluxo:
        1. Lê e faz o parse do corpo JSON da requisição.
        2. Verifica se o update é uma mensagem de texto (`message`) e,
           se for, checa qual comando foi enviado (`/start`, `/myid`, `/ia`).
        3. Chama `send_message` (ou `perguntar_ia` + `send_message`) para
           responder ao usuário.
        4. Sempre devolve {"ok": True} — o Telegram espera uma resposta
           HTTP 200 rápida confirmando o recebimento; se não vier, ele
           reenvia o mesmo update depois.

    Nota importante sobre o objeto `Update` do Telegram: um update tem, no
    máximo, um dos campos opcionais preenchido por vez — ou vem `message`
    (mensagem de texto), ou vem `callback_query` (clique num botão
    inline), nunca os dois juntos. Por isso os dois são capturados
    separadamente logo no início da função.

    Botões inline: o bloco `if message.get("text") == "/start"` envia um
    teclado inline (via `send_message_com_botoes`), e o bloco `if callback:`
    no fim da função trata o clique correspondente (`callback_query`),
    sempre confirmando o recebimento com `responder_callback` antes de
    decidir a resposta — ver a docstring de `responder_callback` para o
    porquê dessa confirmação ser obrigatória.

    Comando /todo: aceita quatro formas de uso, todas tratadas no mesmo
    bloco `if`, direto com acesso ao D1 (sem função auxiliar separada, de
    propósito, para manter esta versão simples num único arquivo):
        - "/todo"              -> lista as tarefas do chat que enviou
        - "/todo add <texto>"  -> cria uma nova tarefa
        - "/todo done <id>"    -> marca a tarefa <id> como concluída
        - "/todo del <id>"     -> remove a tarefa <id>
    Em todos os casos, as operações são restritas ao `chat_id` de quem
    enviou a mensagem — mesma lógica de segurança das rotas HTTP
    `concluir_todo`/`remover_todo` (ver docstrings delas).

    Args:
        request (Request): requisição HTTP recebida, com o "Update" do
            Telegram no corpo, em formato JSON.

    Returns:
        dict: sempre {"ok": True}, confirmando o recebimento ao Telegram.
    """
    update = await request.json()  # O update recebe o json do request e depois disso é possível tratar os dados
    print(update)

    message = update.get("message")
    callback = update.get("callback_query")
    if message and message.get("text") == "/start":
        chat_id = message["chat"]["id"]
        env = request.scope["env"]
        botoes = [
            [{"text": "Meu Id", "callback_data": "myid"}],
            [{"text": "laranjodev eh oq?", "callback_data": "myid"}]
        ]
        await send_message_com_botoes(env, chat_id, "Eae mofiu, esse é o LaranBot. \n -> Os nossos comandos são: /myid, /ia [seu_texto], /todo", botoes)  # /start simples do bot, padrão — agora chamando a função certa, com os botões de verdade

    if message and message.get("text") == "/myid":  # ainda não fui muito a fundo para saber se o message.get() serve apenas para text
        chat_id = message["chat"]["id"]
        env = request.scope["env"]
        await send_message(env, chat_id, f"Seu chat_id é: {chat_id}")  # Adicionando essa função para facilitar quando o dev precisar saber o chat_id

    if message and message.get("text", "").startswith("/ia"):
        chat_id = message["chat"]["id"]
        pergunta = message["text"][len("/ia"):].strip()  # o strip apaga apenas os espaços que não estão entre as palavras/caracteres, assim conseguimos tratar a pergunta e fazer a IA ler apenas o que vem após o /ia utilizando o slicing de string.
        env = request.scope["env"]
        if not pergunta:  # se não houver nada na pergunta
            await send_message(env, chat_id, "Não mandou nada? Para utilizar o comando, utilize assim: /ia sua pergunta aqui")
        else:
            resposta = await perguntar_ia(env, pergunta)
            resultado_envio = await send_message(env, chat_id, resposta)
            print("Resultado do envio para fins de teste: ", resultado_envio)

    if message and message.get("text", "").startswith("/todo"):
        chat_id = message["chat"]["id"]
        env = request.scope["env"]

        # Tudo depois de "/todo" vira o "comando + argumento", ex.:
        # "/todo add Comprar café" -> subcomando="add", argumento="Comprar café"
        texto_comando = message["text"][len("/todo"):].strip()
        partes = texto_comando.split(maxsplit=1)
        subcomando = partes[0] if partes else ""
        argumento = partes[1] if len(partes) > 1 else ""

        if subcomando == "":
            # "/todo" sozinho -> lista as tarefas do chat
            resultado = await env.DB.prepare(
                "SELECT id, texto, feito FROM todos WHERE chat_id = ? ORDER BY id"
            ).bind(chat_id).all()
            # Ajuste .results conforme o atributo exato da sua versão do binding D1
            tarefas = resultado.results if hasattr(resultado, "results") else resultado
            if not tarefas:
                await send_message(env, chat_id, "Você não tem tarefas ainda. Use /todo add <texto>.")
            else:
                linhas = [f"{'✅' if t['feito'] else '⬜'} {t['id']}. {t['texto']}" for t in tarefas]
                await send_message(env, chat_id, "\n".join(linhas))

        elif subcomando == "add" and argumento:
            await env.DB.prepare(
                "INSERT INTO todos (chat_id, texto) VALUES (?, ?)"
            ).bind(chat_id, argumento).run()
            await send_message(env, chat_id, f"Adicionado: {argumento}")

        elif subcomando == "done" and argumento.isdigit():
            # AND chat_id garante que só o dono da tarefa consegue concluí-la
            await env.DB.prepare(
                "UPDATE todos SET feito = 1 WHERE id = ? AND chat_id = ?"
            ).bind(int(argumento), chat_id).run()
            await send_message(env, chat_id, "Marcado como feito.")

        elif subcomando == "del" and argumento.isdigit():
            await env.DB.prepare(
                "DELETE FROM todos WHERE id = ? AND chat_id = ?"
            ).bind(int(argumento), chat_id).run()
            await send_message(env, chat_id, "Removido.")

        else:
            await send_message(
                env, chat_id,
                "Uso: /todo | /todo add <texto> | /todo done <id> | /todo del <id>"
            )

    if callback:
        # message e callback_query nunca vêm preenchidos juntos no mesmo update
        # (regra da própria API do Telegram) — por isso este é um "if" separado,
        # não uma continuação do bloco de texto acima.
        env = request.scope["env"]

        # Sempre responde a query primeiro — evita o botão ficar "carregando"
        # travado no app do usuário (limite documentado: poucos segundos).
        await responder_callback(env, callback["id"])

        chat_id = callback["message"]["chat"]["id"]
        data = callback.get("data")  # valor de "callback_data" definido ao criar o botão

        if data == "myid":
            await send_message(env, chat_id, f"Seu chat_id é: {chat_id}")
        elif data == "laranjo":
            # Exemplo de segundo botão — troque por qualquer lógica sua.
            await send_message(env, chat_id, "Lindu")

    return {"ok": True}


@app.post("/todos")
async def criar_todo(todo: TodoCreate, request: Request) -> dict:
    """Cria uma nova tarefa (to-do) associada a um chat do Telegram.

    Args:
        todo (TodoCreate): corpo da requisição já validado pelo FastAPI —
            contém `chat_id` (int) e `texto` (str). Ver classe `TodoCreate`.
        request (Request): usado só para acessar `request.scope["env"]`,
            de onde vem o binding `DB` do Cloudflare D1.

    Returns:
        dict: {"ok": True} confirmando a criação.
    """
    env = request.scope["env"]
    await env.DB.prepare(
        "INSERT INTO todos (chat_id, texto) VALUES (?, ?)"
    ).bind(todo.chat_id, todo.texto).run()
    return {"ok": True}


@app.get("/todos")
async def listar_todos(chat_id: int, request: Request):
    """Lista todas as tarefas de um chat específico.

    Args:
        chat_id (int): query parameter obrigatório (`?chat_id=123`) —
            identifica de quem são as tarefas a listar.
        request (Request): usado para acessar `request.scope["env"]`.

    Returns:
        O resultado bruto de `.all()` do binding D1 — um objeto contendo,
        entre outros campos, a lista de linhas encontradas (cada linha com
        `id`, `texto` e `feito`). Ordenado por `id` crescente.
    """
    env = request.scope["env"]
    resultado = await env.DB.prepare(
        "SELECT id, texto, feito FROM todos WHERE chat_id = ? ORDER BY id"
    ).bind(chat_id).all()
    return resultado


@app.post("/todos/{todo_id}/concluir")
async def concluir_todo(todo_id: int, chat_id: int, request: Request) -> dict:
    """Marca uma tarefa como concluída (feito = 1).

    Nota de segurança: a query exige `id` E `chat_id` corretos ao mesmo
    tempo (`WHERE id = ? AND chat_id = ?`). Sem o `chat_id`, qualquer
    pessoa que soubesse (ou chutasse) um `todo_id` conseguiria concluir a
    tarefa de outro usuário — por isso `chat_id` é obrigatório aqui,
    mesmo essa rota "só" alterando um registro existente.

    Args:
        todo_id (int): vem da URL (path parameter), ex.: /todos/5/concluir.
        chat_id (int): query parameter obrigatório (`?chat_id=123`) — dono
            esperado da tarefa; a operação só tem efeito se bater com o
            `chat_id` real gravado no banco.
        request (Request): usado para acessar `request.scope["env"]`.

    Returns:
        dict: {"ok": True}. Atenção: retorna {"ok": True} mesmo se nenhuma
        linha for alterada (ex.: id/chat_id não batem) — o UPDATE não
        gera erro nesse caso, só não afeta nenhuma linha.
    """
    env = request.scope["env"]
    await env.DB.prepare(
        "UPDATE todos SET feito = 1 WHERE id = ? AND chat_id = ?"
    ).bind(todo_id, chat_id).run()
    return {"ok": True}


@app.delete("/todos/{todo_id}")
async def remover_todo(todo_id: int, chat_id: int, request: Request) -> dict:
    """Remove uma tarefa permanentemente.

    Mesma lógica de segurança de `concluir_todo`: exige `id` e `chat_id`
    corretos juntos, para impedir que um usuário apague a tarefa de outro.

    Args:
        todo_id (int): vem da URL (path parameter), ex.: /todos/5.
        chat_id (int): query parameter obrigatório (`?chat_id=123`) — dono
            esperado da tarefa.
        request (Request): usado para acessar `request.scope["env"]`.

    Returns:
        dict: {"ok": True}.
    """
    env = request.scope["env"]
    await env.DB.prepare(
        "DELETE FROM todos WHERE id = ? AND chat_id = ?"
    ).bind(todo_id, chat_id).run()
    return {"ok": True}


async def send_message(env, chat_id: int, text: str) -> dict:
    """Envia uma mensagem de texto simples para um chat do Telegram.

    Usa o `fetch` nativo do módulo `workers` (não `requests`/`httpx` —
    essas libs não funcionam no ambiente Pyodide dos Python Workers).

    Args:
        env: objeto de bindings do Worker (`self.env` ou
            `request.scope["env"]`) — precisa expor `env.BOT_TOKEN`.
        chat_id (int): identificador do chat de destino no Telegram.
        text (str): conteúdo da mensagem a enviar.

    Returns:
        dict: corpo JSON da resposta da API do Telegram, já decodificado
            (contém, entre outros campos, `"ok"` e, se sucesso, o objeto
            da mensagem enviada em `"result"`).
    """
    url = f"https://api.telegram.org/bot{env.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    response = await fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
        body=json.dumps(payload),
    )
    return await response.json()


async def perguntar_ia(env, pergunta: str) -> str:
    """Envia uma pergunta para a Cloudflare Workers AI e devolve a resposta em texto.

    Usa o modelo `@cf/meta/llama-4-scout-17b-16e-instruct`, rodando direto
    na infraestrutura da Cloudflare — sem necessidade de chave de API
    externa (ex.: OpenAI). O "system prompt" abaixo define a persona do
    bot; altere o texto ali se quiser mudar o tom das respostas.

    Args:
        env: objeto de bindings do Worker — precisa expor `env.AI`
            (binding da Workers AI, configurado no wrangler.jsonc).
        pergunta (str): pergunta do usuário, já sem o prefixo "/ia".

    Returns:
        str: texto da resposta gerada pelo modelo. Se a chamada não
            devolver um campo "response" utilizável, retorna a mensagem
            de fallback "Não consegui pensar em uma resposta agora.".
    """
    resultado = await env.AI.run(
        "@cf/meta/llama-4-scout-17b-16e-instruct", {
            "messages": [
                {"role": "system", "content": "Você é o LaranBot, assistente pessoal via Telegram. Responda curto, direto, em português."},  # aqui é a persona que você vai alterar a persona da IA, caso queira
                {"role": "user", "content": pergunta}  # aqui é onde a pergunta vai entrar
            ]
        },
    )
    return resultado.get("response", "Não consegui pensar em uma resposta agora.")  # Não se confunda, ele retorna o response (resposta), mas se der ruim ele retorna o texto "Não consegui pensar em uma resposta agora."


async def send_message_com_botoes(env, chat_id: int, text: str, botoes: list) -> dict:
    """Envia uma mensagem de texto acompanhada de um teclado inline (botões).

    Diferente de um teclado normal, um teclado inline aparece dentro da
    própria mensagem no chat. Quando o usuário clica num botão, o
    Telegram NÃO manda uma nova mensagem — ele manda um `callback_query`
    para a rota /webhook (ver `telegram_webhook` e `responder_callback`).

    Args:
        env: objeto de bindings do Worker — precisa expor `env.BOT_TOKEN`.
        chat_id (int): identificador do chat de destino.
        text (str): texto da mensagem que acompanha os botões.
        botoes (list[list[dict]]): matriz de botões — cada item da lista
            externa é uma LINHA do teclado; cada item da linha é um botão,
            no formato {"text": "Rótulo visível", "callback_data": "valor"}.
            Exemplo: [[{"text": "Meu Id", "callback_data": "myid"}]]
            cria uma única linha com um único botão.

    Returns:
        dict: corpo JSON da resposta da API do Telegram.
    """
    url = f"https://api.telegram.org/bot{env.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": botoes},
    }
    response = await fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
        body=json.dumps(payload),
    )
    return await response.json()


async def responder_callback(env, callback_query_id: str) -> None:
    """Confirma ao Telegram que o clique num botão inline foi recebido.

    Ponto importante: o callback_query não envia uma message, então você
    precisa chamar o endpoint answerCallbackQuery para confirmar o
    recebimento do clique — senão o botão fica visualmente "carregando",
    travado, na tela do usuário. A própria API do Telegram espera essa
    confirmação em até poucos segundos após o clique.

    Args:
        env: objeto de bindings do Worker — precisa expor `env.BOT_TOKEN`.
        callback_query_id (str): identificador do callback_query recebido
            (vem em `update["callback_query"]["id"]`, dentro do webhook).

    Returns:
        None. Esta função não repassa nem usa o corpo da resposta da API
        do Telegram — só dispara a confirmação.
    """
    url = f"https://api.telegram.org/bot{env.BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    await fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
        body=json.dumps(payload),
    )