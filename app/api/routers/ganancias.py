"""
Router de ganancias: /api/ganancias/

Tipos de ganancia:
- Bruta: total de ventas (ganancia_bruta en DB)
- Simple: bruta - costo de stock (ganancia_neta en DB)
- Neta: simple - costos operativos diarios (costos_mensuales / 30)
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.database import get_table

router = APIRouter()


def _ganancia_table():
    t = get_table("ganancias")
    if t is None:
        raise RuntimeError("Tabla 'ganancias' no disponible")
    return t


def _costos_diarios(db: Session) -> float:
    """Calcula costos operativos diarios: suma de costos mensuales activos / 30."""
    ct = get_table("costos_operativos")
    if ct is None:
        return 0.0
    rows = db.execute(ct.select().where(ct.c.activo == 1)).fetchall()
    total_mensual = sum(float(dict(r._mapping).get("monto", 0) or 0) for r in rows)
    return total_mensual / 30


def _enriquecer(dato: dict, costo_diario: float) -> dict:
    """Agrega ganancia_simple y ganancia_neta calculada a un registro."""
    bruta = float(dato.get("ganancia_bruta", 0) or 0)
    simple = float(dato.get("ganancia_neta", 0) or 0)  # en DB es bruta - stock
    neta = simple - costo_diario
    dato["ganancia_simple"] = round(simple, 2)
    dato["ganancia_neta"] = round(neta, 2)
    dato["ganancia_bruta"] = round(bruta, 2)
    return dato


@router.get("/")
def listar_ganancias(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lista ganancias con paginacion."""
    t = _ganancia_table()
    costo_d = _costos_diarios(db)

    rows = db.execute(t.select().order_by(t.c.fecha.desc()).limit(limit).offset(offset)).fetchall()
    total = db.execute(t.select().with_only_columns(func.count())).scalar()

    return {
        "data": [_enriquecer(dict(r._mapping), costo_d) for r in rows],
        "costos_diarios": round(costo_d, 2),
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/hoy")
def ganancias_hoy(db: Session = Depends(get_db)):
    """Ganancia del dia actual."""
    t = _ganancia_table()
    costo_d = _costos_diarios(db)
    hoy = date.today().isoformat()

    row = db.execute(t.select().where(t.c.fecha == hoy)).fetchone()
    if row:
        return {"data": _enriquecer(dict(row._mapping), costo_d), "fecha": hoy, "costos_diarios": round(costo_d, 2)}
    return {"data": None, "fecha": hoy, "mensaje": "Sin datos para hoy"}


@router.get("/resumen")
def resumen_ganancias(
    desde: str = Query(None, description="Fecha inicio YYYY-MM-DD"),
    hasta: str = Query(None, description="Fecha fin YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Resumen de ganancias con totales y promedios."""
    t = _ganancia_table()
    costo_d = _costos_diarios(db)

    q = t.select()
    if desde:
        q = q.where(t.c.fecha >= desde)
    if hasta:
        q = q.where(t.c.fecha <= hasta)

    rows = db.execute(q.order_by(t.c.fecha.desc())).fetchall()

    if not rows:
        return {"data": [], "resumen": None}

    datos = [_enriquecer(dict(r._mapping), costo_d) for r in rows]
    brutas = [d["ganancia_bruta"] for d in datos]
    simples = [d["ganancia_simple"] for d in datos]
    netas = [d["ganancia_neta"] for d in datos]
    n = len(datos)

    return {
        "data": datos,
        "costos_diarios": round(costo_d, 2),
        "resumen": {
            "dias": n,
            "total_bruta": round(sum(brutas), 2),
            "total_simple": round(sum(simples), 2),
            "total_neta": round(sum(netas), 2),
            "promedio_bruta": round(sum(brutas) / n, 2),
            "promedio_simple": round(sum(simples) / n, 2),
            "promedio_neta": round(sum(netas) / n, 2),
            "max_bruta": round(max(brutas), 2),
            "min_bruta": round(min(brutas), 2),
        },
    }


@router.get("/mes")
def ganancias_mes(
    mes: int = Query(None, ge=1, le=12, description="Mes (1-12)"),
    anio: int = Query(None, description="Ano (ej: 2026)"),
    db: Session = Depends(get_db),
):
    """Ganancias filtradas por mes."""
    hoy = date.today()
    mes = mes or hoy.month
    anio = anio or hoy.year
    costo_d = _costos_diarios(db)

    desde = f"{anio:04d}-{mes:02d}-01"
    if mes == 12:
        hasta = f"{anio + 1:04d}-01-01"
    else:
        hasta = f"{anio:04d}-{mes + 1:02d}-01"

    t = _ganancia_table()
    rows = db.execute(
        t.select().where(t.c.fecha >= desde, t.c.fecha < hasta).order_by(t.c.fecha.desc())
    ).fetchall()

    datos = [_enriquecer(dict(r._mapping), costo_d) for r in rows]
    brutas = [d["ganancia_bruta"] for d in datos]
    simples = [d["ganancia_simple"] for d in datos]
    netas = [d["ganancia_neta"] for d in datos]

    return {
        "mes": mes,
        "anio": anio,
        "data": datos,
        "costos_diarios": round(costo_d, 2),
        "total_bruta": round(sum(brutas), 2),
        "total_simple": round(sum(simples), 2),
        "total_neta": round(sum(netas), 2),
        "dias_con_datos": len(datos),
    }
