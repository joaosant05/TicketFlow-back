from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from db.connection import initialize_database
from routes import references, tickets


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ticketflow.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando TicketFlow API e validando schema MySQL")
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = time.perf_counter()
    actor = (
        request.headers.get("x-actor-email")
        or request.query_params.get("currentUser")
        or request.query_params.get("email")
        or "anonimo"
    )
    client = request.client.host if request.client else "desconhecido"

    logger.info(
        "REQ start | actor=%s | client=%s | method=%s | path=%s | query=%s",
        actor,
        client,
        request.method,
        request.url.path,
        request.url.query or "-",
    )

    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.exception(
            "REQ error | actor=%s | method=%s | path=%s | elapsed=%.2fms",
            actor,
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "REQ done | actor=%s | method=%s | path=%s | status=%s | elapsed=%.2fms",
        actor,
        request.method,
        request.url.path,
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
