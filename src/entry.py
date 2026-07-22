from workers import WorkerEntrypoint, fetch
from fastapi import FastAPI, Request
import json

app = FastAPI()

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        return await asgi.fetch(app, request, self.env)

@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    print(update)

    message = update.get("message")
    if message and message.get("text") == "/ping":
        chat_id = message["chat"]["id"]
        env = request.scope["env"] #aqui recebe o env 
        result = await send_message(env, chat_id, "pong")
        print("Resposta do Telegram:", result)  # <- visibilidade do que aconteceu

    return {"ok": True}


async def send_message(env, chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{env.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    response = await fetch(
        url,
        method="POST",
        headers={"Content-Type": "application/json"},
        body=json.dumps(payload),
    )
    return await response.json()