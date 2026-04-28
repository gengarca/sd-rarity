import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.rarity")

async def setup(bot: "BallsDexBot"):
    log.info("Loading Rarity package...")
    from .cog import Rarity
    cog = Rarity(bot)
    await bot.add_cog(cog)
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        command_group = balls_cog.app_command
        command_group.command(name="rarity")(cog.rarity)

    log.info("Rarity package loaded successfully!")


async def teardown(bot: "BallsDexBot"):
    balls_cog = bot.cogs.get("Balls")
    if balls_cog is not None:
        command_group = balls_cog.app_command
        command_group.remove_command("rarity")
