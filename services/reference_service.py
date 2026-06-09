import logging

from db.connection import db_cursor


logger = logging.getLogger("ticketflow.users")

ROLE_TO_DB = {
    "user": "solicitante",
    "tech": "tecnico",
    "admin": "admin",
    "solicitante": "solicitante",
    "tecnico": "tecnico",
}

ROLE_FROM_DB = {
    "solicitante": "user",
    "tecnico": "tech",
    "admin": "admin",
}


def _normalize_user(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "papel": row["papel"],
        "role": ROLE_FROM_DB.get(row["papel"], row["papel"]),
        "departamento": row["departamento"],
    }


def _find_department_id(cursor, departamento_id=None, departamento=None):
    if departamento_id:
        return departamento_id
    if not departamento:
        return None

    normalized = departamento.replace("_", " ").strip().lower()
    aliases = {
        "financeiro": "Financeiro",
        "produto": "Produto",
        "suporte n1": "Suporte N1",
        "infraestrutura": "Infraestrutura",
        "rh": "RH",
    }

    cursor.execute(
        """
        SELECT id
        FROM departamentos
        WHERE LOWER(nome) = LOWER(%s)
        LIMIT 1
        """,
        (aliases.get(normalized, departamento),),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


def list_departments():
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nome
            FROM departamentos
            WHERE ativo = TRUE
            ORDER BY nome
            """
        )
        return cursor.fetchall()


def list_categories():
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              c.id,
              c.nome,
              c.prioridade,
              c.sla_horas AS slaHoras,
              d.nome AS departamentoPadrao
            FROM categorias c
            LEFT JOIN departamentos d ON d.id = c.departamento_padrao_id
            WHERE c.ativo = TRUE
            ORDER BY c.id
            """
        )
        return cursor.fetchall()


def list_users(role=None):
    params = []
    where = ["u.ativo = TRUE"]

    if role:
        where.append("u.papel = %s")
        params.append(ROLE_TO_DB.get(role, role))

    with db_cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              u.id,
              u.nome,
              u.email,
              u.papel,
              d.nome AS departamento
            FROM usuarios u
            LEFT JOIN departamentos d ON d.id = u.departamento_id
            WHERE {' AND '.join(where)}
            ORDER BY u.nome
            """,
            tuple(params),
        )
        return [_normalize_user(row) for row in cursor.fetchall()]


def get_user(user_id):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT
              u.id,
              u.nome,
              u.email,
              u.papel,
              d.nome AS departamento
            FROM usuarios u
            LEFT JOIN departamentos d ON d.id = u.departamento_id
            WHERE u.id = %s AND u.ativo = TRUE
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return _normalize_user(row) if row else None


def create_user(data):
    role = data.get("role") or data.get("papel") or "user"
    papel = ROLE_TO_DB.get(role)
    if not papel:
        raise ValueError("Papel de usuario invalido")

    with db_cursor(commit=True) as cursor:
        departamento_id = _find_department_id(
            cursor,
            departamento_id=data.get("departamentoId"),
            departamento=data.get("departamento"),
        )
        cursor.execute(
            """
            INSERT INTO usuarios (
              auth0_id, nome, email, papel, departamento_id
            )
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              auth0_id = COALESCE(VALUES(auth0_id), auth0_id),
              nome = VALUES(nome),
              papel = VALUES(papel),
              departamento_id = VALUES(departamento_id),
              ativo = TRUE
            """,
            (
                data.get("auth0Id"),
                data["nome"],
                data["email"],
                papel,
                departamento_id,
            ),
        )

        cursor.execute(
            "SELECT id FROM usuarios WHERE email = %s LIMIT 1",
            (data["email"],),
        )
        user_id = cursor.fetchone()["id"]

    logger.info(
        "user.upserted | user_id=%s | email=%s | role=%s | departamento_id=%s",
        user_id,
        data["email"],
        papel,
        departamento_id,
    )
    return get_user(user_id)


def update_user_roles(roles_by_user_id):
    updated_ids = []

    if "roles" in roles_by_user_id and isinstance(roles_by_user_id["roles"], dict):
        roles_by_user_id = roles_by_user_id["roles"]

    with db_cursor(commit=True) as cursor:
        for raw_user_id, raw_role in roles_by_user_id.items():
            papel = ROLE_TO_DB.get(raw_role)
            if not papel:
                continue

            cursor.execute(
                """
                UPDATE usuarios
                SET papel = %s
                WHERE id = %s AND ativo = TRUE
                """,
                (papel, int(raw_user_id)),
            )
            if cursor.rowcount:
                updated_ids.append(int(raw_user_id))

    logger.info(
        "users.roles_updated | updated=%s | user_ids=%s",
        len(updated_ids),
        updated_ids,
    )
    return {
        "updated": len(updated_ids),
        "userIds": updated_ids,
    }
