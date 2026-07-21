from workers import WorkerEntrypoint
from fastapi import FastAPI

app = FastAPI()

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi
        return await asgi.fetch(app, request, self.env)

@app.get("/")
async def root():
    return {"message": "Hello, World!"}