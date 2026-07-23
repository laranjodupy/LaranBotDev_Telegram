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
    update = await request.json()
    print(update)

    message = update.get("message")
    if message and message.get("text") == "/start":
        chat_id = message["chat"]["id"]
        env = request.scope["env"]
        await send_message(env, chat_id, "Eae mofiu, esse é o LaranBot. \n -> No momento temos duas funções: /ping (retorna um pong), /myid (retorna o seu id de chat)") #/start simples do bot, padrão
        
    if message and message.get("text") == "/myid":
        chat_id = message["chat"]["id"]
        env = request.scope["env"]
        await send_message(env, chat_id, f"Seu chat_id é: {chat_id}") #Adicionando essa função para facilitar quando o dev precisar saber o chat_id

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