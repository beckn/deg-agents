from fastapi import FastAPI
from app.routers import health, chat
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DEG Endpoints",
    description="Endpoints for Consumer, Solarization, and Grid Agents",
    version="1.0.0",
)

origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
