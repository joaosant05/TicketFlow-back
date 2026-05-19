from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services import ticket_service


router = APIRouter(prefix="/api", tags=["tickets"])


class TicketCreate(BaseModel):
    titulo: str = Field(min_length=3, max_length=180)
    descricao: str = Field(min_length=5)
    idCategoria: int
    solicitanteId: Optional[int] = None
    solicitanteEmail: Optional[str] = None
    departamentoId: Optional[int] = None


class StatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=60)
    actorEmail: Optional[str] = None
    note: Optional[str] = None


class AssignTicket(BaseModel):
    responsavelId: int
    actorEmail: Optional[str] = None


class DepartmentTransfer(BaseModel):
    departamentoId: int
    actorEmail: Optional[str] = None


class PublicReply(BaseModel):
    mensagem: str = Field(min_length=1, max_length=2000)
    actorEmail: Optional[str] = None
    resolver: bool = False


class InternalNote(BaseModel):
    nota: str = Field(min_length=1, max_length=1000)
    actorEmail: Optional[str] = None


class AttachmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: Optional[str] = Field(default=None, max_length=40)
    path: Optional[str] = Field(default=None, max_length=500)
    sizeBytes: Optional[int] = Field(default=None, ge=0)
    actorEmail: Optional[str] = None


@router.get("/tickets")
def list_tickets(
    queue: str = Query(default="department"),
    currentUser: Optional[str] = Query(default=None),
):
    return ticket_service.list_tickets(queue=queue, current_user=currentUser)


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nao encontrado",
        )
    return ticket


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate):
    return ticket_service.create_ticket(payload.dict(exclude_none=True))


@router.patch("/tickets/{ticket_id}/status")
def update_status(ticket_id: int, payload: StatusUpdate):
    ticket = ticket_service.update_status(
        ticket_id=ticket_id,
        status=payload.status,
        actor_email=payload.actorEmail,
        note=payload.note,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.patch("/tickets/{ticket_id}/responsavel")
def assign_ticket(ticket_id: int, payload: AssignTicket):
    ticket = ticket_service.assign_ticket(
        ticket_id=ticket_id,
        responsavel_id=payload.responsavelId,
        actor_email=payload.actorEmail,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.patch("/tickets/{ticket_id}/departamento")
def transfer_department(ticket_id: int, payload: DepartmentTransfer):
    ticket = ticket_service.transfer_department(
        ticket_id=ticket_id,
        departamento_id=payload.departamentoId,
        actor_email=payload.actorEmail,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.post("/tickets/{ticket_id}/respostas")
def add_public_reply(ticket_id: int, payload: PublicReply):
    ticket = ticket_service.add_public_reply(
        ticket_id=ticket_id,
        mensagem=payload.mensagem,
        actor_email=payload.actorEmail,
        resolver=payload.resolver,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.post("/tickets/{ticket_id}/notas")
def add_internal_note(ticket_id: int, payload: InternalNote):
    ticket = ticket_service.add_internal_note(
        ticket_id=ticket_id,
        nota=payload.nota,
        actor_email=payload.actorEmail,
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.post("/tickets/{ticket_id}/anexos")
def add_attachment(ticket_id: int, payload: AttachmentCreate):
    ticket = ticket_service.add_attachment(
        ticket_id=ticket_id,
        data=payload.dict(exclude_none=True),
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.get("/dashboard")
def get_dashboard_summary():
    return ticket_service.get_dashboard_summary()
