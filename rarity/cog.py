import logging
from typing import TYPE_CHECKING, List

import discord
from discord import app_commands
from discord.ext import commands
from django.utils import timezone

from ballsdex.core.utils.transformers import BallEnabledTransform, SpecialEnabledTransform
from bd_models.models import balls, specials as special_cache

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.rarity")

# Configuration constants
ITEMS_PER_PAGE = 2 # How many tiers are shown on a page
# INTEGER

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

    @staticmethod
    def _is_special_active(special) -> bool:
        return (
            (special.start_date or timezone.datetime.min.replace(tzinfo=timezone.get_current_timezone()))
            <= timezone.now()
            <= (special.end_date or timezone.datetime.max.replace(tzinfo=timezone.get_current_timezone()))
        )

    @staticmethod
    def _format_percentage(value: float) -> str:
        percentage = value * 100
        if percentage == 0:
            return "0%"
        if percentage >= 1:
            return f"{percentage:.2f}".rstrip("0").rstrip(".") + "%"
        return f"{percentage:.4f}".rstrip("0").rstrip(".") + "%"

    def _format_special_emoji(self, special) -> str:
        if not special.emoji:
            return "N/A"

        try:
            emoji = self.bot.get_emoji(int(special.emoji))
        except (TypeError, ValueError):
            return special.emoji

        return str(emoji) if emoji else "N/A"

    def _get_special_line(self, special) -> str:
        return f"\u200b ⋄ {self._format_special_emoji(special)} {special.name}"

    def _is_special_spawnable(self, special) -> bool:
        return not special.hidden and special.rarity > 0 and self._is_special_active(special)

    @app_commands.describe(
        specials="Show the enabled specials list",
        special="Specific special event to show spawn chance for",
    )
    @app_commands.checks.cooldown(1, 20, key=lambda i: i.user.id)
    async def rarity(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        countryball: BallEnabledTransform | None = None,
        special: SpecialEnabledTransform | None = None,
        tier: int | None = None,
        specials: bool = False,
        reverse: bool = False,
    ):
        """
        Show the rarity list of the collectibles
        
        Parameters
        ----------
        countryball: BallEnabledTransform
            Specific countryball to show rarity for
        special: SpecialEnabledTransform
            Specific special event to show spawn chance for
        tier: int
            Specific tier to show
        specials: bool
            Whether to show the special event spawn chance list
        reverse: bool
            Whether to reverse the rarity list
        """
        try:
            await interaction.response.defer(thinking=True)
            
            from settings.models import settings

            balls_rarity_list_title = f"{settings.plural_collectible_name.title()} Rarity List"
            specials_rarity_list_title = "Specials Rarity List"
            
            if sum(parameter is not None for parameter in (countryball, special, tier)) + int(specials) > 1:
                await interaction.followup.send(
                    "You can only use one of countryball, special, tier, or specials at a time.",
                    ephemeral=True,
                )
                return

            active_specials = [x for x in special_cache.values() if self._is_special_active(x)]

            if special:
                if not self._is_special_spawnable(special):
                    await interaction.followup.send(
                        "That special is not currently spawnable.",
                        ephemeral=True,
                    )
                    return

                embed = discord.Embed(
                    title=specials_rarity_list_title,
                    color=discord.Color.blurple(),
                )
                embed.add_field(
                    name=f"∥ {self._format_percentage(special.rarity)}",
                    value=self._get_special_line(special),
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
                return

            if specials:
                visible_specials = [x for x in active_specials if self._is_special_spawnable(x)]

                if not visible_specials:
                    await interaction.followup.send("No active specials are available.", ephemeral=True)
                    return

                sorted_specials = sorted(
                    visible_specials,
                    key=lambda x: x.rarity,
                    reverse=reverse,
                )

                all_entries = []
                percentage_to_specials = {}
                for event in sorted_specials:
                    percentage = self._format_percentage(event.rarity)
                    percentage_to_specials.setdefault(percentage, []).append(event)

                for percentage, events in percentage_to_specials.items():
                    names = "\n".join(self._get_special_line(event) for event in events)

                    if len(names) > 1024:
                        current_chunk = []
                        current_length = 0

                        for event in events:
                            line = f"{self._get_special_line(event)}\n"
                            line_length = len(line)

                            if current_length + line_length > 1024:
                                all_entries.append((f"∥ {percentage}", "".join(current_chunk)))
                                current_chunk = [line]
                                current_length = line_length
                            else:
                                current_chunk.append(line)
                                current_length += line_length

                        if current_chunk:
                            all_entries.append((f"∥ {percentage}", "".join(current_chunk)))
                    else:
                        all_entries.append((f"∥ {percentage}", names))

                pages = []
                page_groups = []
                current_page = []

                for entry in all_entries:
                    name, _ = entry
                    if current_page and (
                        len(current_page) >= ITEMS_PER_PAGE or name == current_page[-1][0]
                    ):
                        page_groups.append(current_page)
                        current_page = []
                    current_page.append(entry)

                if current_page:
                    page_groups.append(current_page)

                for page_number, page_entries in enumerate(page_groups, start=1):
                    embed = discord.Embed(
                        title=specials_rarity_list_title,
                        color=discord.Color.blurple(),
                    )
                    for name, value in page_entries:
                        embed.add_field(name=name, value=value, inline=False)
                    embed.set_footer(text=f"Page {page_number}/{len(page_groups)}")
                    pages.append(embed)

                if len(pages) == 1:
                    await interaction.followup.send(embed=pages[0])
                else:
                    view = EmbedPaginator(pages, interaction.user.id, compact=True)
                    view.message = await interaction.followup.send(embed=pages[0], view=view)
                return

            enabled_collectibles = [x for x in balls.values() if x.enabled and x.rarity > 0]

            if not enabled_collectibles:
                await interaction.followup.send(
                    f"There are no {settings.plural_collectible_name} registered in {settings.bot_name} yet.",
                    ephemeral=True,
                )
                return

            rarities = [c.rarity for c in enabled_collectibles]
            min_rarity = min(rarities) if rarities else 1.0
            max_rarity = max(rarities) if rarities else 1.0

            if max_rarity > min_rarity:
                multiplier = 99.0 / (max_rarity - min_rarity)
            else:
                multiplier = 1.0

            rarity_to_collectibles = {}
            for c in enabled_collectibles:
                if max_rarity > min_rarity:
                    tier_num = int((c.rarity - min_rarity) * multiplier + 1.5)
                else:
                    tier_num = 1
                tier_num = max(1, tier_num)
                rarity_to_collectibles.setdefault(tier_num, []).append(c)

            if countryball:
                target_ball = countryball
                if target_ball.rarity <= 0:
                    await interaction.followup.send(
                        f"That {settings.collectible_name} is not included in the rarity list.",
                        ephemeral=True,
                    )
                    return

                if max_rarity > min_rarity:
                    tier_num = int((target_ball.rarity - min_rarity) * multiplier + 1.5)
                else:
                    tier_num = 1
                tier_num = max(1, tier_num)
                collectible_name = f"\u200b ⋄ {self.bot.get_emoji(target_ball.emoji_id) or 'N/A'} {target_ball.country}"

                embed = discord.Embed(title=balls_rarity_list_title, color=discord.Color.blurple())
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
                        title=balls_rarity_list_title,
                        color=discord.Color.blurple(),
                    )
                    embed.add_field(name=f"∥ T{tier}", value=chunks[0], inline=False)
                    await interaction.followup.send(embed=embed)
                else:
                    embeds = []
                    for i, chunk in enumerate(chunks):
                        embed = discord.Embed(
                            title=f"{balls_rarity_list_title} - T{tier}",
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
            page_groups = []
            current_page = []

            for entry in all_entries:
                name, _ = entry
                if current_page and (
                    len(current_page) >= ITEMS_PER_PAGE or name == current_page[-1][0]
                ):
                    page_groups.append(current_page)
                    current_page = []
                current_page.append(entry)

            if current_page:
                page_groups.append(current_page)

            for page_number, page_entries in enumerate(page_groups, start=1):
                embed = discord.Embed(
                    title=balls_rarity_list_title,
                    color=discord.Color.blurple()
                )
                for name, value in page_entries:
                    embed.add_field(name=name, value=value, inline=False)
                embed.set_footer(text=f"Page {page_number}/{len(page_groups)}")
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
