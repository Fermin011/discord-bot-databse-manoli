"""
Cog de ganancias: !ganancia hoy|mes|rango|promedio
"""

import httpx
from discord.ext import commands

from app.bot.formatters import embed_info, embed_ok, format_money


class GananciasCog(commands.Cog, name="Ganancias"):
    """Comandos para consultar ganancias."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base = f"{bot.api_base}/api/ganancias"

    async def _get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base}{path}", params=params, timeout=15)
            return r.json()

    @commands.group(name="ganancia", invoke_without_command=True)
    async def ganancia(self, ctx: commands.Context):
        """Consulta ganancias. Subcomandos: hoy, mes, rango, promedio"""
        await ctx.send_help(ctx.command)

    @ganancia.command(name="hoy")
    async def ganancia_hoy(self, ctx: commands.Context):
        """Ganancia del dia actual."""
        data = await self._get("/hoy")
        d = data.get("data")
        if d:
            em = embed_ok(f"Ganancia - {data['fecha']}")
            em.add_field(name="Bruta", value=format_money(d.get("ganancia_bruta")), inline=True)
            em.add_field(name="Simple", value=format_money(d.get("ganancia_simple")), inline=True)
            em.add_field(name="Neta", value=format_money(d.get("ganancia_neta")), inline=True)
            em.set_footer(text=f"Costos diarios: {format_money(data.get('costos_diarios'))}")
        else:
            em = embed_info("Ganancia - Hoy", data.get("mensaje", "Sin datos"))
        await ctx.send(embed=em)

    @ganancia.command(name="mes")
    async def ganancia_mes(self, ctx: commands.Context, mes: str = None, anio: str = None):
        """Ganancia del mes. Uso: !ganancia mes 1 2026"""
        params = {}
        if mes:
            params["mes"] = int(mes.strip("[]"))
        if anio:
            params["anio"] = int(anio.strip("[]"))

        data = await self._get("/mes", params)

        em = embed_ok(f"Ganancias - {data.get('mes', '?')}/{data.get('anio', '?')}")
        em.add_field(name="Bruta", value=format_money(data.get("total_bruta")), inline=True)
        em.add_field(name="Simple", value=format_money(data.get("total_simple")), inline=True)
        em.add_field(name="Neta", value=format_money(data.get("total_neta")), inline=True)
        em.add_field(name="Dias con datos", value=str(data.get("dias_con_datos", 0)), inline=True)
        em.set_footer(text=f"Costos diarios: {format_money(data.get('costos_diarios'))}")
        await ctx.send(embed=em)

    @ganancia.command(name="rango")
    async def ganancia_rango(self, ctx: commands.Context, desde: str, hasta: str = None):
        """Ganancias en rango. Uso: !ganancia rango 2026-01-01 2026-01-31"""
        params = {"desde": desde}
        if hasta:
            params["hasta"] = hasta

        data = await self._get("/resumen", params)
        r = data.get("resumen")

        if not r:
            await ctx.send(embed=embed_info("Sin datos", "No hay ganancias en ese rango"))
            return

        em = embed_ok(f"Ganancias: {desde} a {hasta or 'hoy'}")
        em.add_field(name="Dias", value=str(r["dias"]), inline=True)
        em.add_field(name="\u200b", value="\u200b", inline=True)
        em.add_field(name="\u200b", value="\u200b", inline=True)
        em.add_field(name="Total Bruta", value=format_money(r["total_bruta"]), inline=True)
        em.add_field(name="Total Simple", value=format_money(r["total_simple"]), inline=True)
        em.add_field(name="Total Neta", value=format_money(r["total_neta"]), inline=True)
        em.add_field(name="Prom. Bruta", value=format_money(r["promedio_bruta"]), inline=True)
        em.add_field(name="Prom. Simple", value=format_money(r["promedio_simple"]), inline=True)
        em.add_field(name="Prom. Neta", value=format_money(r["promedio_neta"]), inline=True)
        em.set_footer(text=f"Costos diarios: {format_money(data.get('costos_diarios'))}")
        await ctx.send(embed=em)

    @ganancia.command(name="promedio")
    async def ganancia_promedio(self, ctx: commands.Context):
        """Promedio general de ganancias."""
        data = await self._get("/resumen")
        r = data.get("resumen")

        if not r:
            await ctx.send(embed=embed_info("Sin datos", "No hay ganancias registradas"))
            return

        em = embed_ok("Promedio de Ganancias")
        em.add_field(name="Dias registrados", value=str(r["dias"]), inline=False)
        em.add_field(name="Prom. Bruta", value=format_money(r["promedio_bruta"]), inline=True)
        em.add_field(name="Prom. Simple", value=format_money(r["promedio_simple"]), inline=True)
        em.add_field(name="Prom. Neta", value=format_money(r["promedio_neta"]), inline=True)
        em.set_footer(text=f"Costos diarios: {format_money(data.get('costos_diarios'))}")
        await ctx.send(embed=em)


async def setup(bot: commands.Bot):
    await bot.add_cog(GananciasCog(bot))
