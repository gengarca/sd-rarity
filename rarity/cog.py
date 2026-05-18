import logging
from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from discord.ext import commands
from ballsdex.core.utils.transformers import BallEnabledTransform
from bd_models.models import balls

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.rarity")

class EmbedPaginator(discord.ui.View):
    """A simple embed paginator for Discord."""

    def __init__(self, embeds: List[discord.Embed], user_id: int, compact: bool = False):
        super().__init__(timeout=180)
        self.embeds = embeds
        self.user_id = user_id
        self.compact = compact
        self.page = 0
        self.message = None
        self.update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot use this button.", ephemeral=True)
            return False
        return True

    def update_buttons(self):
        """Update button states based on current page."""
        self.first_page.disabled = self.page == 0
        self.prev_page.disabled = self.page == 0
        self.next_page.disabled = self.page == len(self.embeds) - 1
        self.last_page.disabled = self.page == len(self.embeds) - 1

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    @discord.ui.button(label="≪", style=discord.ButtonStyle.grey)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.blurple)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = min(len(self.embeds) - 1, self.page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="≫", style=discord.ButtonStyle.grey)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = len(self.embeds) - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.page], view=self)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)


class Rarity(commands.Cog):
    """
    Rarity cog
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def rarity(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        countryball: BallEnabledTransform | None = None,
        tier: int | None = None,
        reverse: bool = False,
    ):
        """
        Show the rarity list of the collectibles
        
        Parameters
        ----------
        countryball: BallEnabledTransform
            Specific countryball to show rarity for
        tier: int
            Specific tier to show
        reverse: bool
            Whether to reverse the rarity list
        """
        try:
            await interaction.response.defer(thinking=True)
            
            from settings.models import settings
            
            enabled_collectibles = [x for x in balls.values() if x.enabled]

            if not enabled_collectibles:
                await interaction.followup.send(
                    f"There are no collectibles registered in {settings.bot_name} yet.",
                    ephemeral=True,
                )
                return

            if countryball and tier:
                await interaction.followup.send("You can't use both parameters at the same time.", ephemeral=True)
                return

            rarity_to_collectibles = {}
            for c in enabled_collectibles:
                rarity = int(round(c.rarity * 100))
                rarity_to_collectibles.setdefault(rarity, []).append(c)

            if countryball:
                target_ball = countryball
                tier_num = int(round(target_ball.rarity * 100))
                collectible_name = f"\u200b ⋄ {self.bot.get_emoji(target_ball.emoji_id) or 'N/A'} {target_ball.country}"

                embed = discord.Embed(title=f"{settings.bot_name} Rarity List", color=discord.Color.blurple())
                embed.add_field(name=f"∥ T{tier_num}", value=collectible_name, inline=False)
                await interaction.followup.send(embed=embed)
                return

            if tier:
                if tier not in rarity_to_collectibles:
                    await interaction.followup.send(f"T{tier} does not exist.", ephemeral=True)
                    return

                filtered_collectibles = rarity_to_collectibles[tier]

                chunks = []
                current_chunk = []
                current_length = 0

                for c in filtered_collectibles:
                    line = f"\u200b ⋄ {self.bot.get_emoji(c.emoji_id) or 'N/A'} {c.country}\n"
                    line_length = len(line)

                    if current_length + line_length > 1024:
                        chunks.append("".join(current_chunk))
                        current_chunk = [line]
                        current_length = line_length
                    else:
                        current_chunk.append(line)
                        current_length += line_length

                if current_chunk:
                    chunks.append("".join(current_chunk))

                if len(chunks) == 1:
                    embed = discord.Embed(
                        title=f"{settings.bot_name} Rarity List",
                        color=discord.Color.blurple(),
                    )
                    embed.add_field(name=f"∥ T{tier}", value=chunks[0], inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    embeds = []
                    for i, chunk in enumerate(chunks):
                        embed = discord.Embed(
                            title=f"{settings.bot_name} Rarity List - T{tier}",
                            color=discord.Color.blurple(),
                        )
                        embed.add_field(name=f"∥ T{tier}", value=chunk, inline=False)
                        embed.set_footer(text=f"Page {i+1}/{len(chunks)}")
                        embeds.append(embed)
                    view = EmbedPaginator(embeds, interaction.user.id, compact=True)
                    view.message = await interaction.followup.send(embed=embeds[0], view=view)
                return

            all_entries = []

            sorted_rarities = sorted(rarity_to_collectibles.keys())
            if reverse:
                sorted_rarities.reverse()

            for i in sorted_rarities:
                collectibles = rarity_to_collectibles[i]
                names = "\n".join(
                    f"\u200b ⋄ {self.bot.get_emoji(c.emoji_id) or 'N/A'} {c.country}" for c in collectibles
                )

                if len(names) > 1024:
                    current_chunk = []
                    current_length = 0

                    for c in collectibles:
                        line = f"\u200b ⋄ {self.bot.get_emoji(c.emoji_id) or 'N/A'} {c.country}\n"
                        line_length = len(line)

                        if current_length + line_length > 1024:
                            chunk_text = "".join(current_chunk)
                            all_entries.append((f"∥ T{i}", chunk_text))
                            current_chunk = [line]
                            current_length = line_length
                        else:
                            current_chunk.append(line)
                            current_length += line_length

                    if current_chunk:
                        chunk_text = "".join(current_chunk)
                        all_entries.append((f"∥ T{i}", chunk_text))
                else:
                    all_entries.append((f"∥ T{i}", names))

            pages = []
            for i in range(0, len(all_entries), 2):
                page_entries = all_entries[i:i+2]
                embed = discord.Embed(
                    title=f"{settings.bot_name} Rarity List",
                    color=discord.Color.blurple()
                )
                for name, value in page_entries:
                    embed.add_field(name=name, value=value, inline=False)
                embed.set_footer(text=f"Page {len(pages)+1}/{(len(all_entries)+1)//2}")
                pages.append(embed)

            if not pages:
                await interaction.followup.send("No rarity data available.", ephemeral=True)
                return

            if len(pages) == 1:
                await interaction.followup.send(embed=pages[0])
            else:
                view = EmbedPaginator(pages, interaction.user.id, compact=True)
                view.message = await interaction.followup.send(embed=pages[0], view=view)

        except Exception as e:
            log.error(f"Error in rarity command: {e}", exc_info=True)
            try:
                await interaction.followup.send(
                    "An error occurred while fetching the rarity list. Please try again later.",
                    ephemeral=True
                )
            except Exception as followup_error:
                log.error(f"Failed to send error message to user: {followup_error}")
