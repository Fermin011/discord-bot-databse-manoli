"""
Cog de consultas: !sql, !tablas, !estado
"""

import httpx
from discord.ext import commands

from app.bot.formatters import embed_error, embed_info, embed_ok, table_to_text
from app.config import settings

p = settings.discord_prefix


class ConsultasCog(commands.Cog, name="Consultas"):
    """Comandos de consulta SQL generica y sistema."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_base = bot.api_base

    @commands.command(name="comandos")
    async def comandos(self, ctx: commands.Context):
        """Muestra todos los comandos disponibles."""
        em = embed_ok("Comandos de Manoli Bot")
        em.description = "**Tipos de ganancia:** Bruta (total ventas) | Simple (bruta - stock) | Neta (simple - costos diarios)"

        em.add_field(
            name="Ganancias (bruta/simple/neta)",
            value=(
                f"`{p}ganancia hoy` - Ganancia del dia\n"
                f"`{p}ganancia mes [mes] [anio]` - Ganancia del mes\n"
                f"`{p}ganancia rango <desde> [hasta]` - Rango de fechas\n"
                f"`{p}ganancia promedio` - Promedio general"
            ),
            inline=False,
        )
        em.add_field(
            name="Ventas",
            value=(
                f"`{p}ventas hoy` - Ventas del dia\n"
                f"`{p}ventas dia <fecha>` - Ventas de un dia\n"
                f"`{p}ventas mes [mes] [anio]` - Ventas del mes\n"
                f"`{p}ventas top [cantidad]` - Top productos vendidos"
            ),
            inline=False,
        )
        em.add_field(
            name="Productos",
            value=(
                f"`{p}producto buscar <nombre>` - Buscar producto\n"
                f"`{p}producto info <id>` - Info detallada\n"
                f"`{p}producto stock [umbral]` - Bajo stock"
            ),
            inline=False,
        )
        em.add_field(
            name="Finanzas",
            value=(
                f"`{p}finanzas costos` - Costos operativos\n"
                f"`{p}finanzas impuestos` - Impuestos\n"
                f"`{p}finanzas balance [desde] [hasta]` - Balance\n"
                f"`{p}finanzas resumen` - Resumen general\n"
                f"`{p}finanzas caja` - Cierres de caja"
            ),
            inline=False,
        )
        em.add_field(
            name="Sistema y SQL",
            value=(
                f"`{p}sql <SELECT ...>` - SQL generico\n"
                f"`{p}tablas` - Lista tablas de la DB\n"
                f"`{p}estado` - Estado del sistema\n"
                f"`{p}comandos` - Esta lista"
            ),
            inline=False,
        )

        await ctx.send(embed=em)

    @commands.command(name="sql")
    async def sql_query(self, ctx: commands.Context, *, query: str):
        """Ejecuta SQL generico (solo SELECT). Uso: !sql SELECT * FROM productos LIMIT 5"""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.api_base}/api/sql/query",
                json={"query": query},
                timeout=15,
            )
            data = r.json()

        if "error" in data:
            await ctx.send(embed=embed_error(data["error"]))
            return

        columns = data.get("columns", [])
        rows = data.get("rows", [])
        count = data.get("count", 0)

        if not rows:
            await ctx.send(embed=embed_info("SQL", "Sin resultados"))
            return

        table_text = table_to_text(columns, rows)
        em = embed_ok(f"Resultado SQL ({count} filas)")
        em.description = f"```\n{table_text}\n```"
        await ctx.send(embed=em)

    @commands.command(name="tablas")
    async def listar_tablas(self, ctx: commands.Context):
        """Lista todas las tablas de la base de datos."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.api_base}/api/sistema/tablas", timeout=15)
            data = r.json()

        tablas = data.get("tablas", [])
        if not tablas:
            await ctx.send(embed=embed_info("Tablas", "No hay tablas disponibles"))
            return

        em = embed_ok(f"Tablas ({data.get('total', len(tablas))})")
        lines = []
        for t in tablas:
            nombre = t.get("nombre", "?")
            registros = t.get("registros", 0)
            lines.append(f"`{nombre}` - {registros:,} registros")

        em.description = "\n".join(lines)
        await ctx.send(embed=em)

    @commands.command(name="estado")
    async def estado(self, ctx: commands.Context):
        """Estado del sistema (health check)."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.api_base}/api/sistema/health", timeout=10)
            data = r.json()

        em = embed_ok("Estado del Sistema")
        em.add_field(name="Status", value=data.get("status", "?"), inline=True)

        uptime = data.get("uptime_seconds", 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        em.add_field(name="Uptime", value=f"{hours}h {minutes}m", inline=True)

        em.add_field(name="Tablas", value=str(data.get("tablas_disponibles", 0)), inline=True)
        await ctx.send(embed=em)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConsultasCog(bot))
