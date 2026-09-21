import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import get_settings
from app.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.routers import analytics, decision_log, feedback, me, pipeline, scoring, transactions
from ml.embedder import get_embedder
from ml.scoring import get_risk_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(title="Synchrony Fraud Agent API", version="0.1.0")
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(scoring.router)
app.include_router(pipeline.router)
app.include_router(decision_log.router)
app.include_router(analytics.router)
app.include_router(me.router)
app.include_router(feedback.router)


@app.on_event("startup")
def warm_model_caches() -> None:
    get_risk_model()
    get_embedder()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
