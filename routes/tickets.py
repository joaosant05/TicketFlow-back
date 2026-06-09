import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services import ticket_service


router = APIRouter(prefix="/api", tags=["tickets"])
logger = logging.getLogger("ticketflow.controller")


class TicketCreate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    idCategoria: Optional[int] = None
    categoriaId: Optional[int] = None
    solicitanteId: Optional[int] = None
    solicitanteEmail: Optional[str] = None
    solicitanteNome: Optional[str] = None
    departamentoId: Optional[int] = None
    departamento: Optional[str] = None
    prioridade: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=60)
    actorEmail: Optional[str] = None
    note: Optional[str] = None


class AssignTicket(BaseModel):
    responsavelId: Optional[int] = None
    responsavelEmail: Optional[str] = None
    responsavelNome: Optional[str] = None
    actorEmail: Optional[str] = None


class DepartmentTransfer(BaseModel):
    departamentoId: Optional[int] = None
    departamento: Optional[str] = None
    actorEmail: Optional[str] = None


class PublicReply(BaseModel):
    mensagem: Optional[str] = Field(default=None, max_length=2000)
    resposta: Optional[str] = Field(default=None, max_length=2000)
    comentario: Optional[str] = Field(default=None, max_length=2000)
    actorEmail: Optional[str] = None
    actorName: Optional[str] = None
    actorRole: Optional[str] = None
    resolver: bool = False
    statusAfter: Optional[str] = None


class InternalNote(BaseModel):
    nota: Optional[str] = Field(default=None, max_length=1000)
    mensagem: Optional[str] = Field(default=None, max_length=1000)
    comentario: Optional[str] = Field(default=None, max_length=1000)
    actorEmail: Optional[str] = None
    actorName: Optional[str] = None


class AttachmentCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    nomeArquivo: Optional[str] = Field(default=None, max_length=255)
    filename: Optional[str] = Field(default=None, max_length=255)
    type: Optional[str] = Field(default=None, max_length=40)
    tipoArquivo: Optional[str] = Field(default=None, max_length=40)
    path: Optional[str] = Field(default=None, max_length=500)
    caminhoArquivo: Optional[str] = Field(default=None, max_length=500)
    sizeBytes: Optional[int] = Field(default=None, ge=0)
    tamanhoBytes: Optional[int] = Field(default=None, ge=0)
    contentBase64: Optional[str] = None
    dataUrl: Optional[str] = None
    mimeType: Optional[str] = Field(default=None, max_length=120)
    actorEmail: Optional[str] = None
    actorName: Optional[str] = None


@router.get("/tickets")
def list_tickets(
    queue: str = Query(default="department"),
    currentUser: Optional[str] = Query(default=None),
):
    return ticket_service.list_tickets(queue=queue, current_user=currentUser)


@router.get("/meus-chamados")
def list_my_requests(
    currentUser: Optional[str] = Query(default=None),
    email: Optional[str] = Query(default=None),
):
    current_user = currentUser or email
    if not current_user:
        raise HTTPException(status_code=400, detail="Informe currentUser ou email")
    return ticket_service.list_user_tickets(current_user=current_user)


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nao encontrado",
        )
    return ticket


@router.get("/tickets/{ticket_id}/sla")
def get_ticket_sla(ticket_id: int):
    sla = ticket_service.get_ticket_sla(ticket_id)
    if not sla:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket nao encontrado",
        )
    return sla


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate):
    logger.info("")
    logger.info("============================================================")
    logger.info("FLUXO: ABERTURA DE TICKET")
    logger.info("Ator: %s", payload.solicitanteEmail or "usuario nao informado")
    logger.info("1. Interface Web -> TicketController | POST /api/tickets")
    logger.info("2. TicketController -> TicketService | processarAbertura(FormDTO)")
    try:
        ticket = ticket_service.create_ticket(payload.dict(exclude_none=True))
        logger.info(
            "9. TicketController -> Interface Web | Response 201 | Protocolo %s/%s",
            ticket["protocolo"],
            ticket["ano"],
        )
        logger.info("FIM DO FLUXO: ticket criado com sucesso")
        logger.info("============================================================")
        logger.info("")
        return ticket
    except ValueError as exc:
        logger.info("3. TicketService -> TicketController | Erro de validacao")
        logger.info("4. TicketController -> Interface Web | Response 400 | %s", exc)
        logger.info("FIM DO FLUXO: abertura recusada")
        logger.info("============================================================")
        logger.info("")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    try:
        ticket = ticket_service.assign_ticket(
            ticket_id=ticket_id,
            responsavel_id=payload.responsavelId,
            responsavel_email=payload.responsavelEmail,
            responsavel_nome=payload.responsavelNome,
            actor_email=payload.actorEmail,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.patch("/tickets/{ticket_id}/departamento")
def transfer_department(ticket_id: int, payload: DepartmentTransfer):
    try:
        ticket = ticket_service.transfer_department(
            ticket_id=ticket_id,
            departamento_id=payload.departamentoId,
            departamento=payload.departamento,
            actor_email=payload.actorEmail,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.post("/tickets/{ticket_id}/respostas")
def add_public_reply(ticket_id: int, payload: PublicReply):
    data = payload.dict(exclude_none=True)
    try:
        ticket = ticket_service.add_public_reply(
            ticket_id=ticket_id,
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.post("/tickets/{ticket_id}/comentarios")
def add_comment(ticket_id: int, payload: PublicReply):
    return add_public_reply(ticket_id, payload)


@router.post("/tickets/{ticket_id}/notas")
def add_internal_note(ticket_id: int, payload: InternalNote):
    data = payload.dict(exclude_none=True)
    try:
        ticket = ticket_service.add_internal_note(
            ticket_id=ticket_id,
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.post("/tickets/{ticket_id}/anexos")
def add_attachment(ticket_id: int, payload: AttachmentCreate):
    try:
        ticket = ticket_service.add_attachment(
            ticket_id=ticket_id,
            data=payload.dict(exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket nao encontrado")
    return ticket


@router.get("/dashboard")
def get_dashboard_summary():
    return ticket_service.get_dashboard_summary()
