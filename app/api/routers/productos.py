"""
Router de productos: /api/productos/
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.database import get_table

router = APIRouter()


def _productos_table():
    t = get_table("productos")
    if t is None:
        raise RuntimeError("Tabla 'productos' no disponible")
    return t


def _stock_table():
    t = get_table("stock_unidades")
    if t is None:
        raise RuntimeError("Tabla 'stock_unidades' no disponible")
    return t


@router.get("/")
def buscar_productos(
    q: str = Query(None, description="Buscar por nombre"),
    categoria_id: int = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Buscar productos con filtros."""
    t = _productos_table()
    query = t.select()

    if q:
        query = query.where(t.c.nombre.like(f"%{q}%"))
    if categoria_id:
        query = query.where(t.c.categoria_id == categoria_id)

    total = db.execute(
        t.select().with_only_columns(func.count()).where(
            t.c.nombre.like(f"%{q}%") if q else True
        )
    ).scalar()

    rows = db.execute(query.order_by(t.c.nombre).limit(limit).offset(offset)).fetchall()
    return {
        "data": [dict(r._mapping) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/info/{producto_id}")
def info_producto(producto_id: int, db: Session = Depends(get_db)):
    """Informacion detallada de un producto."""
    t = _productos_table()
    row = db.execute(t.select().where(t.c.id == producto_id)).fetchone()
    if not row:
        return {"error": "Producto no encontrado", "producto_id": producto_id}

    producto = dict(row._mapping)

    # Contar stock disponible
    st = _stock_table()
    stock_total = db.execute(
        st.select().with_only_columns(func.count()).where(
            st.c.producto_id == producto_id
        )
    ).scalar()
    stock_disponible = db.execute(
        st.select().with_only_columns(func.count()).where(
            st.c.producto_id == producto_id,
            st.c.estado == "disponible",
        )
    ).scalar()

    producto["stock_total"] = stock_total
    producto["stock_disponible"] = stock_disponible

    return {"data": producto}


@router.get("/bajo-stock")
def bajo_stock(
    umbral: int = Query(5, ge=0, description="Umbral minimo de stock"),
    db: Session = Depends(get_db),
):
    """Productos con stock bajo."""
    p = _productos_table()
    st = _stock_table()

    # Subquery: contar stock disponible por producto
    stock_count = (
        st.select()
        .with_only_columns(
            st.c.producto_id,
            func.count(st.c.id).label("stock_disponible"),
        )
        .where(st.c.estado == "disponible")
        .group_by(st.c.producto_id)
        .subquery()
    )

    # Productos con stock <= umbral o sin stock
    q = (
        p.outerjoin(stock_count, p.c.id == stock_count.c.producto_id)
        .select()
        .with_only_columns(
            p.c.id,
            p.c.nombre,
            p.c.cantidad,
            p.c.precio_venta,
            func.coalesce(stock_count.c.stock_disponible, 0).label("stock_disponible"),
        )
        .where(
            or_(
                stock_count.c.stock_disponible <= umbral,
                stock_count.c.stock_disponible.is_(None),
            )
        )
        .order_by(func.coalesce(stock_count.c.stock_disponible, 0))
    )

    rows = db.execute(q).fetchall()
    return {
        "umbral": umbral,
        "data": [dict(r._mapping) for r in rows],
        "count": len(rows),
    }
