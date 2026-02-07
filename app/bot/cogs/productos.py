"""
Cog de productos: !producto buscar|info|stock
"""

import httpx
from discord.ext import commands

from app.bot.formatters import embed_error, embed_info, embed_ok, format_money, format_number


class ProductosCog(commands.Cog, name="Productos"):
    """Comandos para consultar productos."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base = f"{bot.api_base}/api/productos"

    async def _get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base}{path}", params=params, timeout=15)
            return r.json()

    @commands.group(name="producto", invoke_without_command=True)
    async def producto(self, ctx: commands.Context):
        """Consulta productos. Subcomandos: buscar, info, stock"""
        await ctx.send_help(ctx.command)

    @producto.command(name="buscar")
    async def producto_buscar(self, ctx: commands.Context, *, nombre: str):
        """Buscar producto por nombre. Uso: !producto buscar leche"""
        data = await self._get("/", {"q": nombre, "limit": 15})
        items = data.get("data", [])

        if not items:
            await ctx.send(embed=embed_info("Busqueda", f"No se encontraron productos para: `{nombre}`"))
            return

        em = embed_ok(f"Productos: '{nombre}' ({data.get('total', len(items))} resultados)")
        lines = []
        for p in items[:15]:
            precio = format_money(p.get("precio_venta"))
            stock = format_number(p.get("cantidad"))
            lines.append(f"**{p.get('nombre', '?')}** | {precio} | Stock: {stock}")

        em.description = "\n".join(lines)
        await ctx.send(embed=em)

    @producto.command(name="info")
    async def producto_info(self, ctx: commands.Context, producto_id: int):
        """Info detallada de un producto. Uso: !producto info 42"""
        data = await self._get(f"/info/{producto_id}")

        if "error" in data:
            await ctx.send(embed=embed_error(data["error"]))
            return

        p = data.get("data", {})
        em = embed_ok(f"Producto: {p.get('nombre', '?')}")
        em.add_field(name="ID", value=str(p.get("id", "?")), inline=True)
        em.add_field(name="Precio Venta", value=format_money(p.get("precio_venta")), inline=True)
        em.add_field(name="Costo Unitario", value=format_money(p.get("costo_unitario")), inline=True)
        em.add_field(name="Margen", value=f"{p.get('margen_ganancia', '?')}%", inline=True)
        em.add_field(name="Unidad", value=str(p.get("unidad_medida", "?")), inline=True)
        em.add_field(name="Cantidad", value=format_number(p.get("cantidad")), inline=True)
        em.add_field(name="Stock Total", value=format_number(p.get("stock_total")), inline=True)
        em.add_field(name="Stock Disponible", value=format_number(p.get("stock_disponible")), inline=True)

        if p.get("es_divisible"):
            em.add_field(name="Divisible", value=f"Si ({p.get('unidad_base', '')} x{p.get('unidad_factor', '')})", inline=True)

        await ctx.send(embed=em)

    @producto.command(name="stock")
    async def producto_stock(self, ctx: commands.Context, umbral: str = "5"):
        """Productos con bajo stock. Uso: !producto stock 5"""
        data = await self._get("/bajo-stock", {"umbral": int(umbral.strip("[]"))})
        items = data.get("data", [])

        if not items:
            await ctx.send(embed=embed_info("Stock", f"No hay productos con stock <= {umbral}"))
            return

        em = embed_ok(f"Bajo Stock (umbral: {umbral}) - {data.get('count', len(items))} productos")
        lines = []
        for p in items[:20]:
            nombre = p.get("nombre", "?")
            stock = p.get("stock_disponible", 0)
            precio = format_money(p.get("precio_venta"))
            lines.append(f"**{nombre}** | Stock: {stock} | {precio}")

        em.description = "\n".join(lines)
        await ctx.send(embed=em)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProductosCog(bot))
