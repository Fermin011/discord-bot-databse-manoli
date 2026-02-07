"""
Router de sistema: /api/sistema/
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.config import settings
from app.core.database import get_table_names

router = APIRouter()

_start_time = datetime.now()


@router.get("/health")
def health():
    """Estado del sistema."""
    return {
        "status": "ok",
        "uptime_seconds": (datetime.now() - _start_time).total_seconds(),
        "database": str(settings.db_path),
        "tablas_disponibles": len(get_table_names()),
    }


@router.get("/tablas")
def listar_tablas(db: Session = Depends(get_db)):
    """Lista todas las tablas con conteo de registros."""
    tablas = []
    for name in get_table_names():
        try:
            count = db.execute(text(f'SELECT COUNT(*) FROM `{name}`')).scalar()
            tablas.append({"nombre": name, "registros": count})
        except Exception:
            tablas.append({"nombre": name, "registros": -1})

    return {
        "tablas": tablas,
        "total": len(tablas),
    }


@router.get("/info")
def info_sistema():
    """Informacion general del sistema."""
    return {
        "nombre": "Manoli Database API",
        "version": "1.0.0",
        "database_path": str(settings.db_path),
        "json_path": str(settings.json_file_path),
        "api_port": settings.api_port,
        "sql_max_rows": settings.sql_max_rows,
        "inicio": _start_time.isoformat(),
    }
