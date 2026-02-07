"""
APScheduler configuracion para tarea periodica.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

scheduler = AsyncIOScheduler()


def init_scheduler(job_func, interval_minutes: int):
    """Configura el scheduler con la funcion de pipeline."""
    scheduler.add_job(
        job_func,
        "interval",
        minutes=interval_minutes,
        id="data_pipeline",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Scheduler configurado: cada {} minutos", interval_minutes)


def start():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler iniciado")


def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
