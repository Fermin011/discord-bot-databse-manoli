"""
Router de ventas: /api/ventas/
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.database import get_table

router = APIRouter()


def _ventas_table():
    t = get_table("ventas_registro")
    if t is None:
        raise RuntimeError("Tabla 'ventas_registro' no disponible")
    return t


def _detalle_table():
    t = get_table("ventas_detalle")
    if t is None:
        raise RuntimeError("Tabla 'ventas_detalle' no disponible")
    return t


def _productos_table():
    t = get_table("productos")
    if t is None:
        raise RuntimeError("Tabla 'productos' no disponible")
    return t


@router.get("/")
def listar_ventas(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    estado: str = Query(None),
    db: Session = Depends(get_db),
):
    """Lista ventas con paginacion."""
    t = _ventas_table()
    q = t.select()
    if estado:
        q = q.where(t.c.estado == estado)
    rows = db.execute(q.order_by(t.c.fecha.desc()).limit(limit).offset(offset)).fetchall()
    total = db.execute(t.select().with_only_columns(func.count())).scalar()
    return {
        "data": [dict(r._mapping) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/hoy")
def ventas_hoy(db: Session = Depends(get_db)):
    """Ventas del dia actual."""
    t = _ventas_table()
    hoy = date.today().isoformat()
    rows = db.execute(t.select().where(t.c.fecha.like(f"{hoy}%"))).fetchall()
    datos = [dict(r._mapping) for r in rows]
    total_monto = sum(float(d.get("total", 0) or 0) for d in datos)
    return {
        "fecha": hoy,
        "cantidad": len(datos),
        "total_monto": round(total_monto, 2),
        "data": datos,
    }


@router.get("/resumen/diario")
def resumen_diario(
    fecha: str = Query(None, description="Fecha YYYY-MM-DD (default: hoy)"),
    db: Session = Depends(get_db),
):
    """Resumen de ventas de un dia especifico."""
    t = _ventas_table()
    fecha = fecha or date.today().isoformat()

    rows = db.execute(t.select().where(t.c.fecha.like(f"{fecha}%"))).fetchall()
    datos = [dict(r._mapping) for r in rows]

    total_monto = sum(float(d.get("total", 0) or 0) for d in datos)

    # Desglose por metodo de pago
    metodos = {}
    for d in datos:
        metodo = d.get("metodo_pago", "desconocido") or "desconocido"
        metodos[metodo] = metodos.get(metodo, 0) + float(d.get("total", 0) or 0)

    return {
        "fecha": fecha,
        "cantidad_ventas": len(datos),
        "total_monto": round(total_monto, 2),
        "por_metodo_pago": {k: round(v, 2) for k, v in metodos.items()},
    }


@router.get("/top-productos")
def top_productos(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top productos mas vendidos."""
    vd = _detalle_table()
    p = _productos_table()

    # Join ventas_detalle con productos
    q = (
        vd.join(p, vd.c.producto_id == p.c.id)
        .select()
        .with_only_columns(
            p.c.id,
            p.c.nombre,
            func.sum(vd.c.cantidad).label("total_vendido"),
            func.sum(vd.c.subtotal).label("total_ingresos"),
            func.count(vd.c.id).label("num_ventas"),
        )
        .group_by(p.c.id, p.c.nombre)
        .order_by(func.sum(vd.c.cantidad).desc())
        .limit(limit)
    )

    rows = db.execute(q).fetchall()
    return {
        "data": [dict(r._mapping) for r in rows],
        "limit": limit,
    }


@router.get("/mes")
def ventas_mes(
    mes: int = Query(None, ge=1, le=12),
    anio: int = Query(None),
    db: Session = Depends(get_db),
):
    """Ventas del mes."""
    hoy = date.today()
    mes = mes or hoy.month
    anio = anio or hoy.year

    t = _ventas_table()
    prefijo = f"{anio:04d}-{mes:02d}"
    rows = db.execute(t.select().where(t.c.fecha.like(f"{prefijo}%")).order_by(t.c.fecha.desc())).fetchall()

    datos = [dict(r._mapping) for r in rows]
    total_monto = sum(float(d.get("total", 0) or 0) for d in datos)

    return {
        "mes": mes,
        "anio": anio,
        "cantidad_ventas": len(datos),
        "total_monto": round(total_monto, 2),
        "data": datos,
    }
