import discord
from discord.ext import commands
import asyncio
import os
import Webserver

TOKEN = os.environ['discordkey']
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

ping_tasks = {}  # key: user/role ID, value: task
do_not_ping_list = set()  # user/role IDs

# For status updater
status_message = None
status_channel = None
status_update_task = None
status_update_interval = 10  # seconds


async def build_status_embed(ctx):
    active_mentions = []
    for id in ping_tasks:
        obj = ctx.guild.get_member(id) or ctx.guild.get_role(id)
        if obj:
            active_mentions.append(obj.mention)
        else:
            active_mentions.append(f"<Unknown ID {id}>")

    dnp_mentions = []
    for id in do_not_ping_list:
        obj = ctx.guild.get_member(id) or ctx.guild.get_role(id)
        if obj:
            dnp_mentions.append(obj.mention)
        else:
            dnp_mentions.append(f"<Unknown ID {id}>")

    embed = discord.Embed(title="📊 Bot Status", color=discord.Color.blurple())
    embed.add_field(
        name="🔁 Currently Pinging",
        value=", ".join(active_mentions) if active_mentions else "None",
        inline=False
    )
    embed.add_field(
        name="🚫 Do Not Ping List",
        value=", ".join(dnp_mentions) if dnp_mentions else "None",
        inline=False
    )
    return embed


async def status_updater():
    global status_message, status_channel, status_update_task
    try:
        while True:
            if status_message is None or status_channel is None:
                break
            # Refresh message
            status_message = await status_channel.fetch_message(status_message.id)
            embed = await build_status_embed(status_message)
            await status_message.edit(embed=embed)
            await asyncio.sleep(status_update_interval)
    except (discord.NotFound, discord.Forbidden):
        status_message = None
        status_channel = None
        status_update_task = None


@bot.command()
async def pingstart(ctx, interval: float = 5.0, *targets: discord.Role | discord.Member):
    """Start pinging one or more users/roles every `interval` seconds."""
    if not targets:
        await ctx.send("Please mention at least one user or role.")
        return

    started = []
    skipped = []

    for target in targets:
        if target.id in do_not_ping_list:
            skipped.append(f"{target.mention} (Do Not Ping)")
            continue

        if target.id in ping_tasks:
            skipped.append(f"{target.mention} (Already pinging)")
            continue

        # Handle Role
        if isinstance(target, discord.Role):
            async def ping_role_loop(r=target):
                try:
                    while True:
                        mentions = [
                            m.mention for m in r.members
                            if m.id not in do_not_ping_list and not m.bot
                        ]
                        if mentions:
                            await ctx.send(" ".join(mentions) + " 👋")
                        await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    pass

            task = asyncio.create_task(ping_role_loop())
            ping_tasks[target.id] = task
            started.append(target.mention)

        # Handle Member
        elif isinstance(target, discord.Member):
            async def ping_user_loop(m=target):
                try:
                    while True:
                        await ctx.send(f"{m.mention} 👋")
                        await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    pass

            task = asyncio.create_task(ping_user_loop())
            ping_tasks[target.id] = task
            started.append(target.mention)

    if started:
        await ctx.send(f"Started pinging: {', '.join(started)} every {interval} seconds.")
    if skipped:
        await ctx.send(f"Skipped: {', '.join(skipped)}")


@bot.command()
async def pingstop(ctx, *targets: discord.Role | discord.Member):
    """Stop pinging one or more users/roles."""
    if not targets:
        await ctx.send("Please mention at least one user or role.")
        return

    stopped = []
    not_found = []

    for target in targets:
        task = ping_tasks.pop(target.id, None)
        if task:
            task.cancel()
            stopped.append(target.mention)
        else:
            not_found.append(target.mention)

    if stopped:
        await ctx.send(f"Stopped pinging: {', '.join(stopped)}")
    if not_found:
        await ctx.send(f"Not being pinged: {', '.join(not_found)}")


@bot.command()
async def DoNotPing(ctx, *targets: discord.Role | discord.Member):
    """Add users/roles to the Do Not Ping list."""
    added = []
    already = []

    for target in targets:
        if target.id in do_not_ping_list:
            already.append(target.mention)
        else:
            await pingstop(ctx, target)
            do_not_ping_list.add(target.id)
            added.append(target.mention)

    if added:
        await ctx.send(f"Added to Do Not Ping list: {', '.join(added)}")
    if already:
        await ctx.send(f"Already on Do Not Ping list: {', '.join(already)}")


@bot.command()
async def CanPing(ctx, *targets: discord.Role | discord.Member):
    """Remove users/roles from the Do Not Ping list."""
    removed = []
    not_on_list = []

    for target in targets:
        if target.id in do_not_ping_list:
            do_not_ping_list.remove(target.id)
            removed.append(target.mention)
        else:
            not_on_list.append(target.mention)

    if removed:
        await ctx.send(f"Removed from Do Not Ping list: {', '.join(removed)}")
    if not_on_list:
        await ctx.send(f"Not on Do Not Ping list: {', '.join(not_on_list)}")


@bot.command()
async def status(ctx):
    """Show current pinging and Do Not Ping status, auto-updates every 10 seconds."""
    global status_message, status_channel, status_update_task

    embed = await build_status_embed(ctx)
    if status_message and status_channel:
        try:
            status_message = await status_channel.fetch_message(status_message.id)
            await status_message.edit(embed=embed)
            await ctx.message.delete()
        except discord.NotFound:
            status_message = None
            status_channel = None

    if status_message is None or status_channel is None:
        status_message = await ctx.send(embed=embed)
        status_channel = ctx.channel

    if status_update_task is None or status_update_task.done():
        status_update_task = asyncio.create_task(status_updater())


@bot.command()
async def stopall(ctx):
    """Stop all active pings immediately."""
    if not ping_tasks:
        await ctx.send("There are no active pings.")
        return

    stopped = []
    for target_id, task in list(ping_tasks.items()):
        task.cancel()
        obj = ctx.guild.get_member(target_id) or ctx.guild.get_role(target_id)
        if obj:
            stopped.append(obj.mention)
        else:
            stopped.append(f"<Unknown ID {target_id}>")
        ping_tasks.pop(target_id)

    await ctx.send(f"🛑 Stopped all pings: {', '.join(stopped)}")


Webserver.keep_alive()
bot.run(TOKEN)
