from db.connection import db_cursor


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
        params.append(role)

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
        return cursor.fetchall()
