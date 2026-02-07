"""
Cog de finanzas: !finanzas costos|impuestos|balance|resumen|caja
"""

import httpx
from discord.ext import commands

from app.bot.formatters import embed_info, embed_ok, format_money


class FinanzasCog(commands.Cog, name="Finanzas"):
    """Comandos para consultas financieras."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base = f"{bot.api_base}/api/finanzas"

    async def _get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base}{path}", params=params, timeout=15)
            return r.json()

    @commands.group(name="finanzas", invoke_without_command=True)
    async def finanzas(self, ctx: commands.Context):
        """Consultas financieras. Subcomandos: costos, impuestos, balance, resumen, caja"""
        await ctx.send_help(ctx.command)

    @finanzas.command(name="costos")
    async def finanzas_costos(self, ctx: commands.Context):
        """Lista costos operativos activos."""
        data = await self._get("/costos")

        items = data.get("data", [])
        em = embed_ok(f"Costos Operativos ({data.get('count', 0)})")

        if items:
            lines = []
            for c in items:
                nombre = c.get("nombre", "?")
                monto = format_money(c.get("monto"))
                recurrente = "Recurrente" if c.get("recurrente") else "Unico"
                lines.append(f"**{nombre}** | {monto} | {recurrente}")
            em.description = "\n".join(lines)
            em.add_field(name="Total Mensual", value=format_money(data.get("total_mensual")), inline=True)
            em.add_field(name="Costo Diario (/30)", value=format_money(data.get("costo_diario")), inline=True)
        else:
            em.description = "Sin costos operativos registrados"

        await ctx.send(embed=em)

    @finanzas.command(name="impuestos")
    async def finanzas_impuestos(self, ctx: commands.Context):
        """Lista impuestos configurados."""
        data = await self._get("/impuestos")

        items = data.get("data", [])
        em = embed_ok(f"Impuestos ({data.get('count', 0)})")

        if items:
            lines = []
            for imp in items:
                nombre = imp.get("nombre", "?")
                tipo = imp.get("tipo", "?")
                valor = imp.get("valor", "?")
                lines.append(f"**{nombre}** | Tipo: {tipo} | Valor: {valor}")
            em.description = "\n".join(lines)
        else:
            em.description = "Sin impuestos configurados"

        await ctx.send(embed=em)

    @finanzas.command(name="balance")
    async def finanzas_balance(self, ctx: commands.Context, desde: str = None, hasta: str = None):
        """Balance financiero. Uso: !finanzas balance [desde] [hasta]"""
        params = {}
        if desde:
            params["desde"] = desde
        if hasta:
            params["hasta"] = hasta

        data = await self._get("/balance", params)

        if "error" in data:
            await ctx.send(embed=embed_info("Balance", data["error"]))
            return

        periodo = data.get("periodo", {})
        titulo = "Balance Financiero"
        if periodo.get("desde") or periodo.get("hasta"):
            titulo += f" ({periodo.get('desde', '?')} a {periodo.get('hasta', '?')})"

        em = embed_ok(titulo)
        em.add_field(name="Bruta", value=format_money(data.get("ganancia_bruta")), inline=True)
        em.add_field(name="Simple", value=format_money(data.get("ganancia_simple")), inline=True)
        em.add_field(name="Neta", value=format_money(data.get("ganancia_neta")), inline=True)
        em.add_field(name="Costos Mensuales", value=format_money(data.get("costos_mensuales")), inline=True)
        em.add_field(name="Costo Diario", value=format_money(data.get("costo_diario")), inline=True)
        em.add_field(name="Dias", value=str(data.get("dias_con_datos", 0)), inline=True)
        await ctx.send(embed=em)

    @finanzas.command(name="resumen")
    async def finanzas_resumen(self, ctx: commands.Context):
        """Resumen financiero general."""
        data = await self._get("/resumen")

        em = embed_ok("Resumen Financiero General")
        em.add_field(name="Bruta Total", value=format_money(data.get("total_bruta")), inline=True)
        em.add_field(name="Simple Total", value=format_money(data.get("total_simple")), inline=True)
        em.add_field(name="Neta Total", value=format_money(data.get("total_neta")), inline=True)
        em.add_field(name="Dias Registrados", value=str(data.get("dias_registrados", 0)), inline=True)
        em.add_field(name="Total Ventas", value=str(data.get("total_ventas", 0)), inline=True)
        em.add_field(name="Total Productos", value=str(data.get("total_productos", 0)), inline=True)
        em.add_field(name="Costos Mensuales", value=format_money(data.get("costos_mensuales")), inline=True)
        em.add_field(name="Costo Diario", value=format_money(data.get("costo_diario")), inline=True)
        await ctx.send(embed=em)

    @finanzas.command(name="caja")
    async def finanzas_caja(self, ctx: commands.Context):
        """Ultimo cierre de caja."""
        data = await self._get("/caja", {"limit": 5})

        items = data.get("data", [])
        if not items:
            await ctx.send(embed=embed_info("Cierre de Caja", "Sin registros"))
            return

        em = embed_ok(f"Cierres de Caja (ultimos {len(items)})")
        for c in items:
            fecha = c.get("fecha", "?")
            total = format_money(c.get("monto_total"))
            efectivo = format_money(c.get("monto_efectivo"))
            transferencia = format_money(c.get("monto_transferencia"))
            em.add_field(
                name=f"{fecha}",
                value=f"Total: {total}\nEfectivo: {efectivo}\nTransferencia: {transferencia}",
                inline=True,
            )

        await ctx.send(embed=em)


async def setup(bot: commands.Bot):
    await bot.add_cog(FinanzasCog(bot))
