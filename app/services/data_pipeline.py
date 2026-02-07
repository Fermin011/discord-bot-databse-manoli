"""
Pipeline de datos: email -> descomprimir -> JSON -> SQLite -> refresh automap.
"""

import asyncio
from pathlib import Path

from loguru import logger

from app.config import settings
from app.core.converter import SQLiteGenerator
from app.core.database import refresh as refresh_db
from app.services.gmail import fetch_latest_backup


def _run_pipeline_sync() -> bool:
    """
    Ejecuta el pipeline completo de forma sincrona.
    Retorna True si se proceso un nuevo archivo.
    """
    logger.info("Pipeline iniciado")

    # 1. Buscar email nuevo
    json_path = fetch_latest_backup()

    if json_path is None:
        logger.info("Sin datos nuevos, verificando JSON existente...")
        json_path = settings.json_file_path
        if not json_path.exists():
            logger.info("No hay JSON disponible, pipeline finalizado")
            return False

        # Si la DB ya existe y no hay email nuevo, no rebuildeamos
        if settings.db_path.exists():
            logger.info("DB ya existe y no hay email nuevo, saltando rebuild")
            return False

    # 2. Rebuild SQLite
    logger.info("Rebuilding DB desde: {}", json_path.name)
    generator = SQLiteGenerator(json_path, settings.db_path)
    success = generator.rebuild()

    if not success:
        logger.warning("Rebuild no completado (posiblemente ya en progreso)")
        return False

    # 3. Refrescar automap
    refresh_db()
    logger.info("Pipeline completado exitosamente")
    return True


async def run_pipeline():
    """Ejecuta el pipeline en un thread separado (para no bloquear el event loop)."""
    try:
        result = await asyncio.to_thread(_run_pipeline_sync)
        return result
    except Exception as e:
        logger.error("Error en pipeline: {}", e)
        return False


def run_initial_setup():
    """
    Setup inicial sincrono: si hay JSON pero no DB, genera la DB.
    Llamar antes de iniciar el event loop.
    """
    json_path = settings.json_file_path
    db_path = settings.db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)

    if json_path.exists() and not db_path.exists():
        logger.info("Setup inicial: generando DB desde JSON existente")
        generator = SQLiteGenerator(json_path, db_path)
        generator.rebuild()
    elif not json_path.exists():
        logger.warning("No hay JSON disponible para setup inicial")
