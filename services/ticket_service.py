import os
from datetime import date, datetime

from db.connection import db_cursor


INACTIVE_STATUSES = ("Resolvido", "Fechado", "Confirmado")


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
            solicitante_id = _find_user_id(cursor, data.get("solicitanteEmail"))

        cursor.execute(
            """
            SELECT sla_horas, departamento_padrao_id
            FROM categorias
            WHERE id = %s
            """,
            (data["idCategoria"],),
        )
        categoria = cursor.fetchone()

        departamento_id = data.get("departamentoId") or categoria["departamento_padrao_id"]
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
                data["idCategoria"],
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

    return get_ticket(ticket_id)


def assign_ticket(ticket_id, responsavel_id, actor_email=None):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            return None

        actor_id = _find_user_id(cursor, actor_email)
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

    return get_ticket(ticket_id)


def transfer_department(ticket_id, departamento_id, actor_email=None):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT departamento_id FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return None

        old_department_id = ticket["departamento_id"]
        actor_id = _find_user_id(cursor, actor_email)

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

    return get_ticket(ticket_id)


def add_public_reply(ticket_id, mensagem, actor_email=None, resolver=False):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT status FROM tickets WHERE id = %s", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return None

        actor_id = _find_user_id(cursor, actor_email)
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="comment",
            titulo="Resposta enviada ao usuario",
            descricao=mensagem,
            ator_id=actor_id,
            publico=True,
        )

        if resolver:
            cursor.execute(
                "UPDATE tickets SET status = %s, fechado_em = NOW() WHERE id = %s",
                ("Resolvido", ticket_id),
            )
            _insert_history(
                cursor,
                ticket_id=ticket_id,
                tipo="status",
                titulo="Status alterado",
                descricao="Solucao enviada aguardando validacao do cliente.",
                ator_id=actor_id,
                status_de=ticket["status"],
                status_para="Resolvido",
            )

    return get_ticket(ticket_id)


def add_internal_note(ticket_id, nota, actor_email=None):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            return None

        actor_id = _find_user_id(cursor, actor_email)
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="internal_note",
            titulo="Nota interna adicionada",
            descricao=nota,
            ator_id=actor_id,
            publico=False,
        )

    return get_ticket(ticket_id)


def add_attachment(ticket_id, data):
    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM tickets WHERE id = %s", (ticket_id,))
        if not cursor.fetchone():
            return None

        actor_id = _find_user_id(cursor, data.get("actorEmail"))
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
                data["name"],
                data.get("path"),
                data.get("sizeBytes"),
                data.get("type"),
                actor_id,
            ),
        )
        _insert_history(
            cursor,
            ticket_id=ticket_id,
            tipo="attachment",
            titulo="Anexo adicionado",
            descricao=f"Arquivo anexado: {data['name']}",
            ator_id=actor_id,
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
