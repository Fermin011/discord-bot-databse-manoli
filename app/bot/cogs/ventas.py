"""
Cog de ventas: !ventas hoy|dia|mes|top
"""

import httpx
from discord.ext import commands

from app.bot.formatters import embed_info, embed_ok, format_money, format_number


class VentasCog(commands.Cog, name="Ventas"):
    """Comandos para consultar ventas."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base = f"{bot.api_base}/api/ventas"

    async def _get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base}{path}", params=params, timeout=15)
            return r.json()

    @commands.group(name="ventas", invoke_without_command=True)
    async def ventas(self, ctx: commands.Context):
        """Consulta ventas. Subcomandos: hoy, dia, mes, top"""
        await ctx.send_help(ctx.command)

    @ventas.command(name="hoy")
    async def ventas_hoy(self, ctx: commands.Context):
        """Ventas del dia actual."""
        data = await self._get("/hoy")

        em = embed_ok(f"Ventas - {data.get('fecha', 'Hoy')}")
        em.add_field(name="Cantidad", value=format_number(data.get("cantidad")), inline=True)
        em.add_field(name="Total", value=format_money(data.get("total_monto")), inline=True)
        await ctx.send(embed=em)

    @ventas.command(name="dia")
    async def ventas_dia(self, ctx: commands.Context, fecha: str):
        """Ventas de un dia. Uso: !ventas dia 2026-01-15"""
        data = await self._get("/resumen/diario", {"fecha": fecha})

        em = embed_ok(f"Ventas - {data.get('fecha', fecha)}")
        em.add_field(name="Cantidad", value=format_number(data.get("cantidad_ventas")), inline=True)
        em.add_field(name="Total", value=format_money(data.get("total_monto")), inline=True)

        metodos = data.get("por_metodo_pago", {})
        if metodos:
            desglose = "\n".join(f"**{k}**: {format_money(v)}" for k, v in metodos.items())
            em.add_field(name="Por metodo de pago", value=desglose, inline=False)

        await ctx.send(embed=em)

    @ventas.command(name="mes")
    async def ventas_mes(self, ctx: commands.Context, mes: str = None, anio: str = None):
        """Ventas del mes. Uso: !ventas mes 1 2026"""
        params = {}
        if mes:
            params["mes"] = int(mes.strip("[]"))
        if anio:
            params["anio"] = int(anio.strip("[]"))

        data = await self._get("/mes", params)

        em = embed_ok(f"Ventas - {data.get('mes', '?')}/{data.get('anio', '?')}")
        em.add_field(name="Cantidad", value=format_number(data.get("cantidad_ventas")), inline=True)
        em.add_field(name="Total", value=format_money(data.get("total_monto")), inline=True)
        await ctx.send(embed=em)

    @ventas.command(name="top")
    async def ventas_top(self, ctx: commands.Context, limit: str = "10"):
        """Top productos mas vendidos. Uso: !ventas top 10"""
        data = await self._get("/top-productos", {"limit": min(int(limit.strip("[]")), 20)})

        items = data.get("data", [])
        if not items:
            await ctx.send(embed=embed_info("Top Productos", "Sin datos"))
            return

        em = embed_ok(f"Top {len(items)} Productos Mas Vendidos")
        lines = []
        for i, item in enumerate(items, 1):
            nombre = item.get("nombre", "?")
            vendido = format_number(item.get("total_vendido"))
            ingresos = format_money(item.get("total_ingresos"))
            lines.append(f"**{i}.** {nombre} - {vendido} uds ({ingresos})")

        em.description = "\n".join(lines)
        await ctx.send(embed=em)


async def setup(bot: commands.Bot):
    await bot.add_cog(VentasCog(bot))
