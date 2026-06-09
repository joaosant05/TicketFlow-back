from contextlib import asynccontextmanager
import logging
from pathlib import Path
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.connection import initialize_database
from routes import references, tickets


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logger = logging.getLogger("ticketflow.api")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando TicketFlow API e validando schema MySQL")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    initialize_database()
    logger.info("Schema MySQL pronto. API online")
    yield
    logger.info("Encerrando TicketFlow API")


app = FastAPI(
    title="TicketFlow API",
    description="API FastAPI para gerenciamento de tickets do TicketFlow.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
app.include_router(references.router)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path.endswith("/sla"):
        return await call_next(request)

    started_at = time.perf_counter()
    actor = (
        request.headers.get("x-actor-email")
        or request.query_params.get("currentUser")
        or request.query_params.get("email")
        or "anonimo"
    )
    client = request.client.host if request.client else "desconhecido"

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.exception(
            "HTTP ERROR | %s %s | actor=%s | client=%s | %.0fms",
            request.method,
            request.url.path,
            actor,
            client,
            elapsed_ms,
        )
        raise

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "HTTP %s %s | actor=%s | status=%s | %.0fms",
        request.method,
        request.url.path,
        actor,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
def health_check():
    return {
        "app": "TicketFlow API",
        "status": "online",
        "docs": "/docs",
    }
