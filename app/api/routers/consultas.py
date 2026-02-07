"""
Router SQL generico: /api/sql/
"""

from fastapi import APIRouter, Body
from loguru import logger

from app.config import settings
from app.core.database import execute_raw_sql

router = APIRouter()


@router.post("/query")
def ejecutar_sql(
    query: str = Body(..., embed=True, description="Consulta SELECT SQL"),
):
    """
    Ejecuta una consulta SQL generica (solo SELECT).
    Bloquea acceso a tabla usuarios y palabras peligrosas.
    """
    try:
        result = execute_raw_sql(query, max_rows=settings.sql_max_rows)
        return result
    except ValueError as e:
        return {"error": str(e), "query": query}
    except Exception as e:
        logger.error("Error SQL: {} | Query: {}", e, query)
        return {"error": f"Error ejecutando consulta: {e}"}
