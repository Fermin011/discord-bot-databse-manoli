"""
Router de finanzas: /api/finanzas/
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.database import get_table

router = APIRouter()


def _costos_mensuales(db: Session) -> tuple[float, list[dict]]:
    """Retorna (total_mensual, lista_costos)."""
    ct = get_table("costos_operativos")
    if ct is None:
        return 0.0, []
    rows = db.execute(ct.select().where(ct.c.activo == 1)).fetchall()
    datos = [dict(r._mapping) for r in rows]
    total = sum(float(d.get("monto", 0) or 0) for d in datos)
    return total, datos


@router.get("/costos")
def costos_operativos(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Lista costos operativos."""
    t = get_table("costos_operativos")
    if t is None:
        return {"error": "Tabla no disponible"}

    q = t.select()
    if solo_activos:
        q = q.where(t.c.activo == 1)

    rows = db.execute(q).fetchall()
    datos = [dict(r._mapping) for r in rows]
    total = sum(float(d.get("monto", 0) or 0) for d in datos)

    return {
        "data": datos,
        "total_mensual": round(total, 2),
        "costo_diario": round(total / 30, 2),
        "count": len(datos),
    }


@router.get("/impuestos")
def impuestos(
    solo_activos: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Lista impuestos configurados."""
    t = get_table("impuestos")
    if t is None:
        return {"error": "Tabla no disponible"}

    q = t.select()
    if solo_activos:
        q = q.where(t.c.activo == 1)

    rows = db.execute(q).fetchall()
    return {
        "data": [dict(r._mapping) for r in rows],
        "count": len(rows),
    }


@router.get("/balance")
def balance(
    desde: str = Query(None, description="Fecha inicio YYYY-MM-DD"),
    hasta: str = Query(None, description="Fecha fin YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Balance financiero con los 3 tipos de ganancia."""
    gt = get_table("ganancias")
    if gt is None:
        return {"error": "Tabla ganancias no disponible"}

    gq = gt.select()
    if desde:
        gq = gq.where(gt.c.fecha >= desde)
    if hasta:
        gq = gq.where(gt.c.fecha <= hasta)

    g_rows = db.execute(gq).fetchall()
    g_datos = [dict(r._mapping) for r in g_rows]
    dias = len(g_datos)

    total_bruta = sum(float(d.get("ganancia_bruta", 0) or 0) for d in g_datos)
    total_simple = sum(float(d.get("ganancia_neta", 0) or 0) for d in g_datos)

    costos_mes, _ = _costos_mensuales(db)
    costo_diario = costos_mes / 30
    total_costos_periodo = costo_diario * dias
    total_neta = total_simple - total_costos_periodo

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "dias_con_datos": dias,
        "ganancia_bruta": round(total_bruta, 2),
        "ganancia_simple": round(total_simple, 2),
        "ganancia_neta": round(total_neta, 2),
        "costos_mensuales": round(costos_mes, 2),
        "costo_diario": round(costo_diario, 2),
        "costos_periodo": round(total_costos_periodo, 2),
    }


@router.get("/caja")
def cierre_caja(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Historial de cierres de caja."""
    t = get_table("cierre_caja")
    if t is None:
        return {"error": "Tabla no disponible"}

    rows = db.execute(t.select().order_by(t.c.fecha.desc()).limit(limit)).fetchall()
    return {
        "data": [dict(r._mapping) for r in rows],
        "count": len(rows),
    }


@router.get("/resumen")
def resumen_financiero(db: Session = Depends(get_db)):
    """Resumen financiero general."""
    result = {}

    gt = get_table("ganancias")
    if gt:
        g_rows = db.execute(gt.select()).fetchall()
        g_datos = [dict(r._mapping) for r in g_rows]
        dias = len(g_datos)

        total_bruta = sum(float(d.get("ganancia_bruta", 0) or 0) for d in g_datos)
        total_simple = sum(float(d.get("ganancia_neta", 0) or 0) for d in g_datos)

        costos_mes, _ = _costos_mensuales(db)
        costo_diario = costos_mes / 30
        total_neta = total_simple - (costo_diario * dias)

        result["total_bruta"] = round(total_bruta, 2)
        result["total_simple"] = round(total_simple, 2)
        result["total_neta"] = round(total_neta, 2)
        result["dias_registrados"] = dias
        result["costos_mensuales"] = round(costos_mes, 2)
        result["costo_diario"] = round(costo_diario, 2)

    vt = get_table("ventas_registro")
    if vt:
        result["total_ventas"] = db.execute(vt.select().with_only_columns(func.count())).scalar()

    pt = get_table("productos")
    if pt:
        result["total_productos"] = db.execute(pt.select().with_only_columns(func.count())).scalar()

    return result
