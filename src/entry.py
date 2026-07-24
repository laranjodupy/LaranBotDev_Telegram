from workers import WorkerEntrypoint, fetch
from fastapi import FastAPI, Request
from pydantic import BaseModel
import json


app = FastAPI()

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        return await asgi.fetch(app, request, self.env)
    
class TodoCreate(BaseModel):
    chat_id: int
    texto: str


@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json() #O update recebe o json do request e depois disso é possível tratar os dados
    print(update)

    message = update.get("message")
    callback = update.get("callback_query")
    if message and message.get("text") == "/start":
        chat_id = message["chat"]["id"]
        env = request.scope["env"]
        botoes = [
            [{"text": "Meu Id", "callback_data": "myid"}],
            [{"text": "Vitor eh?", "callback_data": "vitu"}]
        ]
        await send_message(env, chat_id, "Eae mofiu, esse é o LaranBot. \n -> Os nossos comandos são: /myid, /ia [seu_texto]") #/start simples do bot, padrão
        
    if message and message.get("text") == "/myid": #ainda não fui muito a fundo para saber se o message.get() serve apenas para text
        chat_id = message["chat"]["id"]
        env = request.scope["env"]
        await send_message(env, chat_id, f"Seu chat_id é: {chat_id}") #Adicionando essa função para facilitar quando o dev precisar saber o chat_id
        
    if message and message.get("text", "").startswith("/ia"):
        chat_id = message["chat"]["id"]
        pergunta = message["text"][len("/ia"):].strip() #o strip apaga apenas os espaços que não estão entre as palavras/caracteres, assim conseguimos tratar a pergunta e fazer a IA ler apenas o que vem após o /ia utilizando o slicing de string.
        env = request.scope["env"]
        if not pergunta: # se não houver nada na pergunta
            await send_message(env, chat_id, "Não mandou nada? Para utilizar o comando, utilize assim: /ia sua pergunta aqui")
        else: 
            resposta = await perguntar_ia(env, pergunta)
            resultado_envio = await send_message(env, chat_id, resposta)
            print("Resultado do envio para fins de teste: ", resultado_envio)
            
    return {"ok": True}

@app.post("/todos")
async def criar_todo(todo: TodoCreate, request: Request):
    env = request.scope["env"]
    await env.DB.prepare(
        "INSERT INTO todos (chat_id, texto) VALUES (?, ?)"
    ).bind(todo.chat_id, todo.texto).run()
    return {"ok": True}

@app.get("/todos")
async def listar_todos(chat_id: int, request: Request):
    env = request.scope["env"]
    resultado = await env.DB.prepare(
        "SELECT id, texto, feito FROM todos WHERE chat_id = ? ORDER BY id"
    ).bind(chat_id).all()
    return resultado

@app.post("/todos/{todo_id}/concluir")
async def concluir_todo(todo_id: int, request: Request):
    env = request.scope["env"]
    await env.DB.prepare(
        "UPDATE todos SET feito = 1 WHERE id = ?"
    ).bind(todo_id).run()
    return {"ok":True}


@app.delete("/todos/{todo_id}")
async def remover_todo(todo_id: int, request: Request):
    env = request.scope["env"]
    await env.DB.prepare(
        "DELETE FROM todos WHERE id = ?"
    ).bind(todo_id).run()

    return {"ok":True}

async def send_message(env, chat_id: int, text: str):
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
    resultado = await env.AI.run(
        "@cf/meta/llama-4-scout-17b-16e-instruct", {
        "messages": [
            {"role": "system", "content": "Você é o LaranBot, assistente pessoal via Telegram. Responda curto, direto, em português."}, #aqui é a persona que você vai alterar a persona da IA, caso queira
            {"role": "user", "content": pergunta} #aqui é onde a pergunta vai entrar
        ]
    },
    ) 
    return resultado.get("response", "Não consegui pensar em uma resposta agora.") #Não se confunda, ele retorna o response (resposta), mas se der ruim ele retorna o texto "Não consegui pensar em uma resposta agora."


async def send_message_com_botoes(env, chat_id: int, text: str, botoes: list): #aqui é onde vamos colocar botões de clique para o nosso bot e facilitar a ux.
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

#Ponto importante: o callbackquery não envia uma message, então você precisa utilizar o endpoint /answerCallbackQuery para obter a resposta do clique do botão, senão fica todo bugado com um carregando na tela do usuario
async def responder_callback(env, callback_query_id: str):
    url = f"https://api.telegram.org/bot{env.BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    await fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
        body=json.dumps(payload),
    )