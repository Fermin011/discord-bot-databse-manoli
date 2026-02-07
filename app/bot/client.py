"""
ManoliBot: Discord bot que consume la API REST.
"""

import discord
from discord.ext import commands
from loguru import logger

from app.config import settings


class ManoliBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=settings.discord_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(no_category="Otros"),
        )
        self.api_base = settings.api_base_url

    async def setup_hook(self):
        """Carga los cogs al iniciar."""
        cog_modules = [
            "app.bot.cogs.ganancias",
            "app.bot.cogs.ventas",
            "app.bot.cogs.productos",
            "app.bot.cogs.finanzas",
            "app.bot.cogs.consultas",
        ]
        for module in cog_modules:
            try:
                await self.load_extension(module)
                logger.info("Cog cargado: {}", module)
            except Exception as e:
                logger.error("Error cargando cog {}: {}", module, e)

    async def on_ready(self):
        logger.info("Bot conectado como: {} (ID: {})", self.user.name, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{settings.discord_prefix}help | {settings.discord_prefix}comandos",
            )
        )

    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Falta argumento: `{error.param.name}`. Usa `{settings.discord_prefix}help {ctx.command}` para ver el uso.")
            return
        logger.error("Error en comando {}: {}", ctx.command, error)
        await ctx.send(f"Error: {error}")


def create_bot() -> ManoliBot:
    return ManoliBot()
