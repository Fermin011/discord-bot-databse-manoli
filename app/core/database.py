"""
Engine SQLAlchemy con automap para reflexion dinamica de tablas.
"""

import threading

from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_lock = threading.Lock()

engine = None
SessionLocal = None
Base = None
_table_names: list[str] = []


def _set_wal_mode(dbapi_conn, connection_record):
    """Activa WAL mode y busy_timeout para lecturas concurrentes."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def init_engine():
    """Inicializa el engine SQLAlchemy y refleja las tablas."""
    global engine, SessionLocal, Base, _table_names

    db_path = settings.db_path
    if not db_path.exists():
        logger.warning("DB no existe aun: {}", db_path)
        return False

    db_url = f"sqlite:///{db_path}"

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    event.listen(engine, "connect", _set_wal_mode)

    Base = automap_base()
    Base.prepare(autoload_with=engine)

    _table_names = list(Base.metadata.tables.keys())
    logger.info("Automap: {} tablas reflejadas: {}", len(_table_names), _table_names)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    return True


def refresh():
    """Re-refleja las tablas despues de un rebuild de la DB."""
    with _lock:
        logger.info("Refrescando automap...")
        init_engine()


def get_session() -> Session:
    """Retorna una nueva session. Caller debe cerrarla."""
    if SessionLocal is None:
        raise RuntimeError("Database no inicializada. Ejecutar init_engine() primero.")
    return SessionLocal()


def get_table_names() -> list[str]:
    """Retorna nombres de tablas reflejadas."""
    return list(_table_names)


def get_table(name: str):
    """Retorna un objeto Table por nombre."""
    if Base is None:
        return None
    return Base.metadata.tables.get(name)


def execute_raw_sql(query: str, max_rows: int | None = None) -> dict:
    """
    Ejecuta una consulta SELECT y retorna resultados como dict.
    Solo permite SELECT. Valida palabras peligrosas.
    """
    query_stripped = query.strip().rstrip(";")
    query_upper = query_stripped.upper()

    if not query_upper.startswith("SELECT"):
        raise ValueError("Solo se permiten consultas SELECT")

    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE", "ATTACH"]
    for word in forbidden:
        if word in query_upper.split():
            raise ValueError(f"Palabra prohibida en consulta: {word}")

    # Bloquear acceso a tabla usuarios
    if "USUARIOS" in query_upper:
        raise ValueError("Acceso a tabla 'usuarios' no permitido")

    limit = max_rows or settings.sql_max_rows
    if "LIMIT" not in query_upper:
        query_stripped += f" LIMIT {limit}"

    session = get_session()
    try:
        result = session.execute(text(query_stripped))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "count": len(rows)}
    finally:
        session.close()
