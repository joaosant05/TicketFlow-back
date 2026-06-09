import logging
import os
import unicodedata
from datetime import date, datetime

from db.connection import db_cursor


logger = logging.getLogger("ticketflow.tickets")

INACTIVE_STATUSES = ("Resolvido", "Fechado", "Confirmado")

DEFAULT_CATEGORY_BY_PRIORITY = {
    "alta": 2,
    "media": 4,
    "baixa": 5,
}


def _format_sla(deadline):
    if not deadline:
        return None

    remaining_seconds = int((deadline - datetime.now()).total_seconds())
    if remaining_seconds <= 0:
        return "Expirado"

    hours = remaining_seconds // 3600
    minutes = (remaining_seconds % 3600) // 60

    if hours >= 24:
        return f"{hours // 24}d"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}m"


def _format_file_size(size_bytes):
    if size_bytes is None:
        return ""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def _normalize_ticket(row):
    if not row:
        return None

    return {
        "id": row["id"],
        "protocolo": row["protocolo"],
        "ano": int(row["ano"]),
        "titulo": row["titulo"],
        "descricao": row["descricao"],
        "status": row["status"],
        "idCategoria": row["categoria_id"],
        "prioridade": row.get("prioridade"),
        "tempoRestanteSLA": _format_sla(row.get("sla_deadline")),
        "responsavel": row.get("responsavel"),
        "solicitante": row.get("solicitante"),
        "departamento": row.get("departamento"),
        "criadoEm": row.get("criado_em"),
        "slaTipo": row.get("sla_tipo"),
        "slaDeadline": row.get("sla_deadline"),
    }


def _find_user_id(cursor, email=None):
    if not email:
        return None
    cursor.execute("SELECT id FROM usuarios WHERE email = %s LIMIT 1", (email,))
    user = cursor.fetchone()
    return user["id"] if user else None


def _get_or_create_user(cursor, email=None, name=None, papel="solicitante"):
    user_id = _find_user_id(cursor, email)
    if user_id or not email:
        return user_id

    display_name = name or email.split("@", 1)[0].replace(".", " ").title()
    cursor.execute(
        """
        INSERT INTO usuarios (nome, email, papel)
        VALUES (%s, %s, %s)
        """,
        (display_name, email, papel),
    )
    return cursor.lastrowid


def _find_department_id(cursor, department):
    if not department:
        return None

    normalized = department.replace("_", " ").strip().lower()
    aliases = {
        "suporte n1": "Suporte N1",
        "infraestrutura": "Infraestrutura",
        "financeiro": "Financeiro",
        "produto": "Produto",
        "rh": "RH",
    }
    department_name = aliases.get(normalized, department)

    cursor.execute(
        """
        SELECT id
        FROM departamentos
        WHERE LOWER(nome) = LOWER(%s)
        LIMIT 1
        """,
        (department_name,),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


def _resolve_category_id(data):
    category_id = data.get("idCategoria") or data.get("categoriaId")
    if category_id:
        return category_id

    priority = _normalize_key(data.get("prioridade") or "")
    return DEFAULT_CATEGORY_BY_PRIORITY.get(priority, 5)


def _normalize_key(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.strip().lower()


def _first_text(data, *keys):
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _role_to_db(role):
    return {
        "user": "solicitante",
        "tech": "tecnico",
        "admin": "admin",
        "solicitante": "solicitante",
        "tecnico": "tecnico",
    }.get((role or "").strip().lower(), "solicitante")


def _insert_history(
    cursor,
    ticket_id,
    tipo,
    titulo,
    descricao=None,
    ator_id=None,
    status_de=None,
    status_para=None,
    departamento_de_id=None,
    departamento_para_id=None,
    publico=True,
):
    cursor.execute(
        """
        INSERT INTO ticket_historico (
          ticket_id, tipo, titulo, descricao, ator_id, status_de, status_para,
          departamento_de_id, departamento_para_id, publico
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            ticket_id,
            tipo,
            titulo,
            descricao,
            ator_id,
            status_de,
            status_para,
            departamento_de_id,
            departamento_para_id,
            publico,
        ),
    )


def list_tickets(queue="department", current_user=None):
    where = []
    params = []
    current_user = current_user or os.getenv("DEFAULT_CURRENT_USER", "demo@demo.com.br")

    if queue == "department":
        where.append("t.status NOT IN (%s, %s, %s)")
        params.extend(INACTIVE_STATUSES)
    elif queue == "unassigned":
        where.append("t.responsavel_id IS NULL")
    elif queue == "mine":
        where.append("(responsavel.email = %s OR responsavel.nome = %s)")
        params.extend([current_user or "", current_user or ""])
    elif queue == "waiting":
        where.append("t.status = %s")
        params.append("Aguardando Cliente")
    elif queue == "resolved":
        where.append("t.status = %s")
        params.append("Resolvido")
    elif queue == "confirmed":
        where.append("t.status IN (%s, %s)")
        params.extend(["Fechado", "Confirmado"])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with db_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              t.id, t.protocolo, t.ano, t.titulo, t.descricao, t.status,
              t.categoria_id, t.sla_tipo, t.sla_deadline, t.criado_em,
              c.prioridade,
              responsavel.nome AS responsavel,
              solicitante.nome AS solicitante,
              d.nome AS departamento
            FROM tickets t
            INNER JOIN categorias c ON c.id = t.categoria_id
            LEFT JOIN usuarios responsavel ON responsavel.id = t.responsavel_id
            LEFT JOIN usuarios solicitante ON solicitante.id = t.solicitante_id
            LEFT JOIN departamentos d ON d.id = t.departamento_id
            {where_sql}
            ORDER BY t.criado_em DESC
            """,
            tuple(params),
        )
        return [_normalize_ticket(row) for row in cursor.fetchall()]


def list_user_tickets(current_user):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              t.id, t.protocolo, t.ano, t.titulo, t.descricao, t.status,
              t.categoria_id, t.sla_tipo, t.sla_deadline, t.criado_em,
              c.prioridade,
              responsavel.nome AS responsavel,
              solicitante.nome AS solicitante,
              d.nome AS departamento
            FROM tickets t
            INNER JOIN categorias c ON c.id = t.categoria_id
            LEFT JOIN usuarios responsavel ON responsavel.id = t.responsavel_id
            LEFT JOIN usuarios solicitante ON solicitante.id = t.solicitante_id
            LEFT JOIN departamentos d ON d.id = t.departamento_id
            WHERE solicitante.email = %s OR solicitante.nome = %s
            ORDER BY t.criado_em DESC
            """,
            (current_user, current_user),
        )
        return [_normalize_ticket(row) for row in cursor.fetchall()]


def get_ticket(ticket_id):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              t.id, t.protocolo, t.ano, t.titulo, t.descricao, t.status,
              t.categoria_id, t.sla_tipo, t.sla_deadline, t.criado_em,
              c.prioridade,
              responsavel.nome AS responsavel,
              solicitante.nome AS solicitante,
              d.nome AS departamento
            FROM tickets t
            INNER JOIN categorias c ON c.id = t.categoria_id
            LEFT JOIN usuarios responsavel ON responsavel.id = t.responsavel_id
            LEFT JOIN usuarios solicitante ON solicitante.id = t.solicitante_id
            LEFT JOIN departamentos d ON d.id = t.departamento_id
            WHERE t.id = %s
            """,
            (ticket_id,),
        )
        ticket = _normalize_ticket(cursor.fetchone())
        if not ticket:
            return None

        cursor.execute(
            """
            SELECT nome_arquivo, tamanho_bytes, tipo_arquivo
            FROM ticket_anexos
            WHERE ticket_id = %s
            ORDER BY criado_em ASC
            """,
            (ticket_id,),
        )
        ticket["anexos"] = [
            {
                "name": row["nome_arquivo"],
                "size": _format_file_size(row["tamanho_bytes"]),
                "type": row["tipo_arquivo"],
            }
            for row in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT
              h.id, h.tipo, h.titulo, h.descricao, h.status_de, h.status_para,
              h.criado_em, u.nome AS ator
            FROM ticket_historico h
            LEFT JOIN usuarios u ON u.id = h.ator_id
            WHERE h.ticket_id = %s
            ORDER BY h.criado_em ASC
            """,
            (ticket_id,),
        )
        ticket["history"] = [_normalize_history(row) for row in cursor.fetchall()]

        return ticket


def _normalize_history(row):
    tags = []
    status_arrow = False

    if row.get("status_de"):
        tags.append(row["status_de"])
    if row.get("status_para"):
        tags.append(row["status_para"])
        status_arrow = True

    return {
        "id": f"h{row['id']}",
        "type": row["tipo"],
        "title": row["titulo"],
        "tags": tags,
        "actor": row.get("ator"),
        "timestamp": row["criado_em"].strftime("%Y-%m-%d %H:%M"),
        "note": row.get("descricao"),
        "statusArrow": status_arrow,
    }


def create_ticket(data):
    current_year = date.today().year
    category_id = _resolve_category_id(data)

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT COALESCE(MAX(protocolo), 0) + 1 AS next_protocolo
            FROM tickets
            WHERE ano = %s
            FOR UPDATE
            """,
            (current_year,),
        )
        protocolo = cursor.fetchone()["next_protocolo"]

        solicitante_id = data.get("solicitanteId")
        if not solicitante_id:
            solicitante_id = _get_or_create_user(
                cursor,
                email=data.get("solicitanteEmail"),
                name=data.get("solicitanteNome"),
                papel="solicitante",
            )

        cursor.execute(
            """
            SELECT sla_horas, departamento_padrao_id
            FROM categorias
            WHERE id = %s
            """,
            (category_id,),
        )
        categoria = cursor.fetchone()
        if not categoria:
            raise ValueError("Categoria nao encontrada")

        departamento_id = (
            data.get("departamentoId")
            or _find_department_id(cursor, data.get("departamento"))
            or categoria["departamento_padrao_id"]
        )
        sla_horas = categoria["sla_horas"]

        cursor.execute(
            """
            INSERT INTO tickets (
              protocolo, ano, titulo, descricao, categoria_id, solicitante_id,
              departamento_id, sla_deadline
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL %s HOUR))
            """,
            (
                protocolo,
                current_year,
                data["titulo"],
                data["descricao"],
                category_id,
                solicitante_id,
                departamento_id,
                sla_horas,
            ),
        )
        ticket_id = cursor.lastrowid
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="created",
            titulo="Ticket criado",
            descricao=data["descricao"],
            ator_id=solicitante_id,
        )

    logger.info(
        "ticket.created | ticket_id=%s | protocolo=%s/%s | solicitante=%s | departamento_id=%s | categoria_id=%s",
        ticket_id,
        protocolo,
        current_year,
        data.get("solicitanteEmail") or solicitante_id or "anonimo",
        departamento_id,
        category_id,
    )
    return get_ticket(ticket_id)


def update_status(ticket_id, status, actor_email=None, note=None):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT status FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return None

        old_status = ticket["status"]
        actor_id = _find_user_id(cursor, actor_email)
        closed_at_sql = ", fechado_em = NOW()" if status in INACTIVE_STATUSES else ""

        cursor.execute(
            f"UPDATE tickets SET status = %s {closed_at_sql} WHERE id = %s",
            (status, ticket_id),
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="status",
            titulo="Status alterado",
            descricao=note,
            ator_id=actor_id,
            status_de=old_status,
            status_para=status,
        )

    logger.info(
        "ticket.status_updated | ticket_id=%s | actor=%s | from=%s | to=%s",
        ticket_id,
        actor_email or "anonimo",
        old_status,
        status,
    )
    return get_ticket(ticket_id)


def assign_ticket(
    ticket_id,
    responsavel_id=None,
    responsavel_email=None,
    responsavel_nome=None,
    actor_email=None,
):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            return None

        if not responsavel_id:
            responsavel_id = _get_or_create_user(
                cursor,
                email=responsavel_email,
                name=responsavel_nome,
                papel="tecnico",
            )
        if not responsavel_id:
            raise ValueError("Responsavel nao informado")

        actor_id = _get_or_create_user(cursor, email=actor_email)
        cursor.execute(
            "UPDATE tickets SET responsavel_id = %s WHERE id = %s",
            (responsavel_id, ticket_id),
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="assigned",
            titulo="Ticket atribuido",
            ator_id=actor_id,
        )

    logger.info(
        "ticket.assigned | ticket_id=%s | actor=%s | responsavel_id=%s | responsavel_email=%s",
        ticket_id,
        actor_email or "anonimo",
        responsavel_id,
        responsavel_email or "-",
    )
    return get_ticket(ticket_id)


def transfer_department(ticket_id, departamento_id=None, departamento=None, actor_email=None):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT departamento_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return None

        departamento_id = departamento_id or _find_department_id(cursor, departamento)
        if not departamento_id:
            raise ValueError("Departamento nao encontrado")

        old_department_id = ticket["departamento_id"]
        actor_id = _get_or_create_user(cursor, email=actor_email)

        cursor.execute(
            "UPDATE tickets SET departamento_id = %s WHERE id = %s",
            (departamento_id, ticket_id),
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="department",
            titulo="Departamento alterado",
            ator_id=actor_id,
            departamento_de_id=old_department_id,
            departamento_para_id=departamento_id,
        )

    logger.info(
        "ticket.department_transferred | ticket_id=%s | actor=%s | from=%s | to=%s",
        ticket_id,
        actor_email or "anonimo",
        old_department_id,
        departamento_id,
    )
    return get_ticket(ticket_id)


def add_public_reply(ticket_id, data):
    mensagem = _first_text(data, "mensagem", "resposta", "comentario")
    if not mensagem:
        raise ValueError("Mensagem nao informada")

    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT status FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return None

        actor_id = _get_or_create_user(
            cursor,
            email=data.get("actorEmail"),
            name=data.get("actorName"),
            papel=_role_to_db(data.get("actorRole")),
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="comment",
            titulo="Resposta enviada ao usuario",
            descricao=mensagem,
            ator_id=actor_id,
            publico=True,
        )

        status_after = data.get("statusAfter")
        if data.get("resolver"):
            status_after = "Resolvido"

        if status_after:
            closed_at_sql = ", fechado_em = NOW()" if status_after in INACTIVE_STATUSES else ""
            cursor.execute(
                f"UPDATE tickets SET status = %s {closed_at_sql} WHERE id = %s",
                (status_after, ticket_id),
            )
            _insert_history(
                cursor,
                ticket_id=ticket_id,
                tipo="status",
                titulo="Status alterado",
                descricao="Status atualizado apos comentario.",
                ator_id=actor_id,
                status_de=ticket["status"],
                status_para=status_after,
            )

    logger.info(
        "ticket.reply_added | ticket_id=%s | actor=%s | status_after=%s",
        ticket_id,
        data.get("actorEmail") or "anonimo",
        status_after or "-",
    )
    return get_ticket(ticket_id)


def add_internal_note(ticket_id, data):
    nota = _first_text(data, "nota", "mensagem", "comentario")
    if not nota:
        raise ValueError("Nota nao informada")

    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            return None

        actor_id = _get_or_create_user(
            cursor,
            email=data.get("actorEmail"),
            name=data.get("actorName"),
            papel="tecnico",
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="internal_note",
            titulo="Nota interna adicionada",
            descricao=nota,
            ator_id=actor_id,
            publico=False,
        )

    logger.info(
        "ticket.internal_note_added | ticket_id=%s | actor=%s",
        ticket_id,
        data.get("actorEmail") or "anonimo",
    )
    return get_ticket(ticket_id)


def add_attachment(ticket_id, data):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            return None

        name = data.get("name") or data.get("nomeArquivo") or data.get("filename")
        if not name:
            raise ValueError("Nome do anexo nao informado")

        actor_id = _get_or_create_user(
            cursor,
            email=data.get("actorEmail"),
            name=data.get("actorName"),
        )
        cursor.execute(
            """
            INSERT INTO ticket_anexos (
              ticket_id, nome_arquivo, caminho_arquivo, tamanho_bytes,
              tipo_arquivo, enviado_por_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                ticket_id,
                name,
                data.get("path") or data.get("caminhoArquivo"),
                data.get("sizeBytes") or data.get("tamanhoBytes"),
                data.get("type") or data.get("tipoArquivo"),
                actor_id,
            ),
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="attachment",
            titulo="Anexo adicionado",
            descricao=f"Arquivo anexado: {name}",
            ator_id=actor_id,
        )

    logger.info(
        "ticket.attachment_added | ticket_id=%s | actor=%s | file=%s",
        ticket_id,
        data.get("actorEmail") or "anonimo",
        name,
    )
    return get_ticket(ticket_id)


def get_dashboard_summary():
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              SUM(CASE WHEN status NOT IN ('Resolvido', 'Fechado', 'Confirmado') THEN 1 ELSE 0 END) AS pendentes,
              SUM(CASE WHEN status = 'Resolvido' THEN 1 ELSE 0 END) AS resolvidos,
              COUNT(*) AS total
            FROM tickets
            """
        )
        summary = cursor.fetchone()

        cursor.execute(
            """
            SELECT
              t.id, t.protocolo, t.ano, t.titulo, t.descricao, t.status,
              t.categoria_id, t.sla_tipo, t.sla_deadline, t.criado_em,
              c.prioridade,
              responsavel.nome AS responsavel,
              solicitante.nome AS solicitante,
              d.nome AS departamento
            FROM tickets t
            INNER JOIN categorias c ON c.id = t.categoria_id
            LEFT JOIN usuarios responsavel ON responsavel.id = t.responsavel_id
            LEFT JOIN usuarios solicitante ON solicitante.id = t.solicitante_id
            LEFT JOIN departamentos d ON d.id = t.departamento_id
            WHERE c.prioridade = 'Alta'
              AND t.status NOT IN ('Resolvido', 'Fechado', 'Confirmado')
            ORDER BY t.sla_deadline ASC
            LIMIT 10
            """
        )
        urgent_tickets = [_normalize_ticket(row) for row in cursor.fetchall()]

    total = summary["total"] or 0
    resolvidos = summary["resolvidos"] or 0
    taxa = round((resolvidos / total) * 100) if total else 0

    return {
        "pendentes": summary["pendentes"] or 0,
        "resolvidos": resolvidos,
        "taxaResolucao": f"{taxa}%",
        "ticketsUrgentes": urgent_tickets,
    }
