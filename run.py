"""
Punto de entrada principal.
Orquesta FastAPI + Discord Bot + APScheduler en un solo event loop.
"""

import asyncio
import sys
from pathlib import Path

import discord
import uvicorn
from loguru import logger

# Configurar loguru
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - {message}")
logger.add(
    "logs/app.log",
    rotation="5 MB",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}",
)

from app.config import settings
from app.core.database import init_engine
from app.core.scheduler import init_scheduler, shutdown as shutdown_scheduler, start as start_scheduler
from app.services.data_pipeline import run_initial_setup, run_pipeline


async def run_api():
    """Arranca FastAPI como tarea async."""
    config = uvicorn.Config(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    """Arranca el bot de Discord."""
    if not settings.discord_token:
        logger.warning("DISCORD_TOKEN no configurado, bot deshabilitado")
        # Mantener vivo para que no cancele el gather
        while True:
            await asyncio.sleep(3600)

    from app.bot.client import create_bot

    bot = create_bot()
    try:
        await bot.start(settings.discord_token)
    except discord.PrivilegedIntentsRequired:
        logger.error(
            "Bot Discord requiere Message Content Intent. "
            "Habilitalo en https://discord.com/developers/applications/ -> Bot -> Privileged Gateway Intents"
        )
    except Exception as e:
        logger.error("Error en bot Discord: {}", e)

    # Mantener vivo para que la API siga corriendo
    while True:
        await asyncio.sleep(3600)


async def main():
    """Orquesta todos los componentes."""
    logger.info("=" * 50)
    logger.info("Manoli Bot Database - Iniciando...")
    logger.info("=" * 50)

    # Asegurar directorios
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Setup inicial: generar DB si hay JSON
    run_initial_setup()

    # Inicializar engine SQLAlchemy
    if settings.db_path.exists():
        init_engine()
        logger.info("Database engine inicializado")
    else:
        logger.warning("No hay DB disponible, ejecutando pipeline inicial...")
        result = await run_pipeline()
        if result and settings.db_path.exists():
            init_engine()
            logger.info("Database engine inicializado tras pipeline inicial")
        else:
            logger.warning("Pipeline inicial no obtuvo datos, esperando al scheduler")

    # Configurar scheduler
    init_scheduler(run_pipeline, settings.gmail_check_interval_minutes)
    start_scheduler()

    logger.info("Iniciando componentes...")
    logger.info("  API: http://{}:{}", settings.api_host, settings.api_port)
    logger.info("  Bot Discord: {}", "habilitado" if settings.discord_token else "deshabilitado")
    logger.info("  Scheduler: cada {} min", settings.gmail_check_interval_minutes)

    try:
        await asyncio.gather(
            run_api(),
            run_bot(),
        )
    except KeyboardInterrupt:
        logger.info("Interrupcion recibida, cerrando...")
    finally:
        shutdown_scheduler()
        logger.info("Sistema detenido")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
