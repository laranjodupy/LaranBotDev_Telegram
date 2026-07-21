from workers import WorkerEntrypoint
from fastapi import FastAPI, Request

app = FastAPI()

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        return await asgi.fetch(app, request, self.env)

@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.post('/webhook')
async def telegram_webhook(request: Request):
    update = await request.json()
    print(update) #Simples, só para ver o que está chegando no terminal
    return {"ok": True}