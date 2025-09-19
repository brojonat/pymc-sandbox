import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from prometheus_fastapi_instrumentator import Instrumentator

from pymc_vibes.server.database import initialize_metadata
from pymc_vibes.server.routers import (
    ab_test,
    bernoulli,
    events,
    experiments,
    multi_armed_bandits,
    poisson_cohorts,
    ui,
)


# -------------------------
# Logging configuration
# -------------------------
def configure_logging() -> None:
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    json_logs = os.getenv("LOG_JSON", "false").lower() == "true"
    service_name = os.getenv("SERVICE_NAME", "fastapi-app")

    logging.basicConfig(level=log_level, stream=sys.stdout)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bind common fields
    structlog.contextvars.bind_contextvars(service=service_name)


configure_logging()
log = structlog.get_logger()


# -------------------------
# Auth configuration
# -------------------------
JWT_SECRET = os.getenv("AUTH_SECRET", "change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
security = HTTPBearer(auto_error=True)


def require_claims(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    token = credentials.credentials
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    return claims


# -------------------------
# App & instrumentation
# -------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("service.startup")
    initialize_metadata()
    try:
        yield
    finally:
        log.info("service.shutdown")


app = FastAPI(title=os.getenv("SERVICE_NAME", "fastapi-app"), lifespan=lifespan)

# API Routers
app.include_router(bernoulli.router)
app.include_router(ab_test.router)
app.include_router(multi_armed_bandits.router)
app.include_router(poisson_cohorts.router)
app.include_router(ui.router)
app.include_router(events.router)
app.include_router(experiments.router)

# Mount the static directory to serve JS, CSS, etc.
# This must be located in the same directory as this main.py file.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Prometheus: exposes /metrics by default
Instrumentator().instrument(app).expose(app)


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


@app.get("/whoami", tags=["auth"])
def whoami(claims: Dict = Depends(require_claims)):
    # claims is injected as the first parameter via Depends
    return {"claims": claims}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
