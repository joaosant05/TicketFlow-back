from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import references, tickets


app = FastAPI(
    title="TicketFlow API",
    description="API FastAPI para gerenciamento de tickets do TicketFlow.",
    version="1.0.0",
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


@app.get("/")
def health_check():
    return {
        "app": "TicketFlow API",
        "status": "online",
        "docs": "/docs",
    }
