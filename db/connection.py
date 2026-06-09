import os
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
from mysql.connector import Error


MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Joao1700556#")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ticketflow")


def _connection_config(include_database=True):
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "autocommit": False,
    }
    if include_database:
        config["database"] = MYSQL_DATABASE
    return config


def get_server_connection():
    try:
        return mysql.connector.connect(**_connection_config(include_database=False))
    except Error as exc:
        raise RuntimeError(f"Erro ao conectar no servidor MySQL: {exc}") from exc


def get_connection():
    try:
        return mysql.connector.connect(**_connection_config(include_database=True))
    except Error as exc:
        raise RuntimeError(f"Erro ao conectar no MySQL: {exc}") from exc


def initialize_database():
    schema_path = Path(__file__).with_name("schema.sql")
    statements = [
        statement.strip()
        for statement in schema_path.read_text(encoding="utf-8").split(";")
        if statement.strip()
    ]

    connection = get_server_connection()
    cursor = connection.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


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
