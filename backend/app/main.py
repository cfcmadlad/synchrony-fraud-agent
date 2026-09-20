from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import scoring, transactions

settings = get_settings()

app = FastAPI(title="Synchrony Fraud Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(scoring.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
