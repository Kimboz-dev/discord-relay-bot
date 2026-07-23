import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import database

load_dotenv(r"C:\Users\Joelw\Downloads\Cross-server message\.env")
TOKEN = os.getenv("DISCORD_TOKEN")
# DEBUG – remove after it works
print("Token loaded:", repr(TOKEN[:10] + "...") if TOKEN else "None")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

WEBHOOK_NAME = "RelayBot"

# In-memory matchmaking queue for !ucall.
# Each entry: {"channel_id": int, "guild_id": int, "channel_name": str, "guild_name": str}
matchmaking_queue = []
queue_lock = asyncio.Lock()
QUEUE_TIMEOUT_SECONDS = 120  # auto-cancel a waiting channel after 2 minutes


async def get_or_create_webhook(channel: discord.TextChannel) -> discord.Webhook:
    """Fetch this channel's relay webhook, creating it if needed."""
    webhooks = await channel.webhooks()
    webhook = discord.utils.get(webhooks, name=WEBHOOK_NAME)
    if webhook is None:
        webhook = await channel.create_webhook(name=WEBHOOK_NAME)
    return webhook


@bot.event
async def on_ready():
    database.init_db()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Connected to {len(bot.guilds)} server(s):")
    for guild in bot.guilds:
        print(f" - {guild.name} ({guild.id})")
    print("Bot is ready.")


@bot.event
async def on_message(message: discord.Message):
    # Never relay messages sent by bots/webhooks -- this prevents infinite loops
    if message.author.bot:
        return

    linked_channel_ids = database.get_linked_channels(message.channel.id)

    for dest_id in linked_channel_ids:
        dest_channel = bot.get_channel(dest_id)
        if dest_channel is None:
            continue
        try:
            webhook = await get_or_create_webhook(dest_channel)
            files = [await a.to_file() for a in message.attachments] if message.attachments else []
            await webhook.send(
                content=message.content or None,
                username=f"{message.author.display_name} ({message.guild.name})",
                avatar_url=message.author.display_avatar.url,
                files=files,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            print(f"Missing permissions to relay into channel {dest_id}")
        except Exception as e:
            print(f"Failed to relay message to {dest_id}: {e}")

    await bot.process_commands(message)


@bot.command(name="link")
@commands.has_permissions(manage_guild=True)
async def link_channel(ctx: commands.Context, target_channel_id: int):
    """Link this channel to a channel in another server.
    Usage: !link <channel_id>
    """
    target_channel = bot.get_channel(target_channel_id)
    if target_channel is None:
        await ctx.send(
            "I can't see that channel. Make sure the bot has joined that "
            "server and the channel ID is correct."
        )
        return

    if target_channel.id == ctx.channel.id:
        await ctx.send("You can't link a channel to itself.")
        return

    database.add_link(ctx.channel.id, ctx.guild.id, target_channel.id, target_channel.guild.id)
    await ctx.send(
        f"✅ Linked **#{ctx.channel.name}** ({ctx.guild.name}) ↔ "
        f"**#{target_channel.name}** ({target_channel.guild.name})"
    )


@bot.command(name="unlink")
@commands.has_permissions(manage_guild=True)
async def unlink_channel(ctx: commands.Context):
    """Remove all permanent (!link) relay links for this channel.
    Use !hangup to end a random (!ucall) match instead."""
    database.remove_links_for_channel(ctx.channel.id, link_type="permanent")
    await ctx.send(f"🔌 Removed all permanent relay links for **#{ctx.channel.name}**")


@bot.command(name="links")
async def list_links(ctx: commands.Context):
    """List all relay links involving this server."""
    rows = database.get_links_for_guild(ctx.guild.id)
    if not rows:
        await ctx.send("No relay links configured for this server.")
        return

    lines = []
    for channel_a_id, _guild_a_id, channel_b_id, _guild_b_id, link_type in rows:
        chan_a = bot.get_channel(channel_a_id)
        chan_b = bot.get_channel(channel_b_id)
        name_a = f"#{chan_a.name}" if chan_a else str(channel_a_id)
        name_b = f"#{chan_b.name}" if chan_b else str(channel_b_id)
        lines.append(f"{name_a} ↔ {name_b} ({link_type})")

    await ctx.send("**Active relay links:**\n" + "\n".join(lines))


@bot.command(name="ucall")
async def ucall(ctx: commands.Context):
    """Randomly connect this channel to another server's channel that
    is also waiting via !ucall. Use !hangup to end the match later."""
    async with queue_lock:
        if any(e["channel_id"] == ctx.channel.id for e in matchmaking_queue):
            await ctx.send(
                "This channel is already waiting for a match. Use `!cancel` to stop waiting."
            )
            return

        # Look for a waiting channel from a DIFFERENT server
        match = next((e for e in matchmaking_queue if e["guild_id"] != ctx.guild.id), None)

        if match is None:
            matchmaking_queue.append({
                "channel_id": ctx.channel.id,
                "guild_id": ctx.guild.id,
                "channel_name": ctx.channel.name,
                "guild_name": ctx.guild.name,
            })
            await ctx.send(
                "🔎 Looking for another server... waiting for someone else to run `!ucall`. "
                f"(Times out in {QUEUE_TIMEOUT_SECONDS // 60} minutes. Use `!cancel` to stop waiting.)"
            )

            async def expire(channel_id, channel):
                await asyncio.sleep(QUEUE_TIMEOUT_SECONDS)
                async with queue_lock:
                    still_waiting = any(e["channel_id"] == channel_id for e in matchmaking_queue)
                    matchmaking_queue[:] = [e for e in matchmaking_queue if e["channel_id"] != channel_id]
                if still_waiting:
                    try:
                        await channel.send("⌛ No match found in time. Run `!ucall` again to retry.")
                    except discord.HTTPException:
                        pass

            bot.loop.create_task(expire(ctx.channel.id, ctx.channel))
            return

        matchmaking_queue.remove(match)
        database.add_link(
            ctx.channel.id, ctx.guild.id, match["channel_id"], match["guild_id"], link_type="random"
        )

    partner_channel = bot.get_channel(match["channel_id"])
    await ctx.send(
        f"🎲 Connected! You're now randomly linked with **{match['guild_name']}** "
        f"(#{match['channel_name']}). Use `!hangup` to disconnect."
    )
    if partner_channel:
        try:
            await partner_channel.send(
                f"🎲 Connected! You're now randomly linked with **{ctx.guild.name}** "
                f"(#{ctx.channel.name}). Use `!hangup` to disconnect."
            )
        except discord.HTTPException:
            pass


@bot.command(name="cancel")
async def cancel_wait(ctx: commands.Context):
    """Stop waiting in the !ucall matchmaking queue."""
    async with queue_lock:
        before = len(matchmaking_queue)
        matchmaking_queue[:] = [e for e in matchmaking_queue if e["channel_id"] != ctx.channel.id]
        after = len(matchmaking_queue)

    if before == after:
        await ctx.send("This channel isn't waiting for a match.")
    else:
        await ctx.send("❌ Cancelled. No longer waiting for a random match.")


@bot.command(name="hangup")
async def hangup(ctx: commands.Context):
    """End this channel's active random (!ucall) connection."""
    partner_ids = database.get_linked_channels_by_type(ctx.channel.id, "random")

    if not partner_ids:
        await ctx.send("You don't have an active random connection. Use `!ucall` to start one.")
        return

    database.remove_links_for_channel(ctx.channel.id, link_type="random")
    await ctx.send("🔌 Disconnected from the random match.")

    for cid in partner_ids:
        partner_channel = bot.get_channel(cid)
        if partner_channel:
            try:
                await partner_channel.send(
                    f"🔌 **{ctx.guild.name}** hung up. The random connection has ended."
                )
            except discord.HTTPException:
                pass


@bot.command(name="myid")
async def my_channel_id(ctx: commands.Context):
    """Show this channel's ID (needed when setting up a link)."""
    await ctx.send(f"This channel's ID is: `{ctx.channel.id}`")


@link_channel.error
@unlink_channel.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need the **Manage Server** permission to use this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please provide a valid channel ID, e.g. `!link 123456789012345678`")
    else:
        raise error


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN not found. Did you create a .env file from .env.example?")
    bot.run(TOKEN)
