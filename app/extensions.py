"""Shared Flask extensions, instantiated once and attached in the app factory."""
import os
import sqlite3

from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: object, connection_record: object) -> None:
    """WAL mode plus a busy timeout so threaded writers do not collide."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        if os.environ.get("PYTEST_CURRENT_TEST"):
            # Tests only: skip per-commit fsync (same SQL, same results,
            # no crash-safety needs). Production keeps FULL durability.
            cursor.execute("PRAGMA synchronous=OFF")
        cursor.close()
