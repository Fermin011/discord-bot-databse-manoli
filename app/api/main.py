"""
Aplicacion FastAPI con lifespan.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.routers import consultas, finanzas, ganancias, productos, sistema, ventas
from app.core.database import init_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI iniciando...")
    init_engine()
    yield
    logger.info("FastAPI cerrando...")


app = FastAPI(
    title="Manoli Database API",
    description="API REST para consultar la base de datos Manoli",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Captura errores cuando la DB no esta lista."""
    return JSONResponse(
        status_code=503,
        content={"error": str(exc), "mensaje": "Base de datos no disponible. Esperando primer sync desde Gmail."},
    )


app.include_router(ganancias.router, prefix="/api/ganancias", tags=["Ganancias"])
app.include_router(ventas.router, prefix="/api/ventas", tags=["Ventas"])
app.include_router(productos.router, prefix="/api/productos", tags=["Productos"])
app.include_router(finanzas.router, prefix="/api/finanzas", tags=["Finanzas"])
app.include_router(consultas.router, prefix="/api/sql", tags=["SQL"])
app.include_router(sistema.router, prefix="/api/sistema", tags=["Sistema"])
