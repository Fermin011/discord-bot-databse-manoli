"""
Formateo de respuestas para Discord: Embeds y tablas.
"""

from datetime import datetime
from typing import Any

import discord


def embed_ok(title: str, description: str = None, color: int = 0x2ECC71) -> discord.Embed:
    """Crea un embed de exito."""
    em = discord.Embed(title=title, description=description, color=color)
    em.set_footer(text=f"Manoli Bot | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    return em


def embed_error(message: str) -> discord.Embed:
    """Crea un embed de error."""
    em = discord.Embed(title="Error", description=message, color=0xE74C3C)
    return em


def embed_info(title: str, description: str = None) -> discord.Embed:
    """Crea un embed informativo."""
    em = discord.Embed(title=title, description=description, color=0x3498DB)
    em.set_footer(text=f"Manoli Bot | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    return em


def format_money(value: Any) -> str:
    """Formatea un valor monetario."""
    try:
        v = float(value or 0)
        return f"${v:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def format_number(value: Any) -> str:
    """Formatea un numero."""
    try:
        v = int(float(value or 0))
        return f"{v:,}"
    except (ValueError, TypeError):
        return "0"


def table_to_text(columns: list[str], rows: list[dict], max_rows: int = 20) -> str:
    """
    Convierte resultados SQL a texto formateado para Discord.
    Usa formato de tabla simple compatible con bloques de codigo.
    """
    if not rows:
        return "Sin resultados"

    display_rows = rows[:max_rows]

    # Calcular anchos
    widths = {}
    for col in columns:
        widths[col] = len(col)
        for row in display_rows:
            val = str(row.get(col, ""))
            if len(val) > 25:
                val = val[:22] + "..."
            widths[col] = max(widths[col], len(val))

    # Header
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)

    # Rows
    lines = [header, separator]
    for row in display_rows:
        vals = []
        for col in columns:
            val = str(row.get(col, ""))
            if len(val) > 25:
                val = val[:22] + "..."
            vals.append(val.ljust(widths[col]))
        lines.append(" | ".join(vals))

    if len(rows) > max_rows:
        lines.append(f"... (+{len(rows) - max_rows} filas mas)")

    text = "\n".join(lines)

    # Discord tiene limite de 2000 chars por mensaje y 4096 por embed
    if len(text) > 3900:
        text = text[:3900] + "\n... (truncado)"

    return text
