import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error


def get_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "ticketflow"),
            autocommit=False,
        )
    except Error as exc:
        raise RuntimeError(f"Erro ao conectar no MySQL: {exc}") from exc


@contextmanager
def db_cursor(commit=False):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
