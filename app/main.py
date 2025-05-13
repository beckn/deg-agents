from fastapi import FastAPI
from app.routers import health, chat

app = FastAPI(
    title="DEG Endpoints",
    description="Endpoints for Consumer, Solarization, and Grid Agents",
    version="1.0.0",
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
