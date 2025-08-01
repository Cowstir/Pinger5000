import discord
from discord.ext import commands, tasks
import asyncio
import os
import Webserver

TOKEN = os.environ['discordkey']
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

ping_tasks = {}
do_not_ping_list = set()  # Can include both user and role IDs


@bot.command()
async def pingstart(ctx, target: discord.Role | discord.Member, interval: float = 5.0):
    """Start pinging a user or role every `interval` seconds (supports decimals)."""

    if target.id in do_not_ping_list:
        await ctx.send(f"{target.mention} is on the Do Not Ping list.")
        return

    if target.id in ping_tasks:
        await ctx.send(f"Already pinging {target.mention}!")
        return

    async def ping_loop():
        try:
            while True:
                await ctx.send(f"{target.mention} 👋")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(ping_loop())
    ping_tasks[target.id] = task
    await ctx.send(f"Started pinging {target.mention} every {interval} seconds.")

@bot.command()
async def pingstop(ctx, target: discord.Role | discord.Member):
    """Stop pinging a user or role."""
    task = ping_tasks.pop(target.id, None)
    if task:
        task.cancel()
        await ctx.send(f"Stopped pinging {target.mention}.")
    else:
        await ctx.send(f"{target.mention} was not being pinged.")

@bot.command()
async def DoNotPing(ctx, target: discord.Role | discord.Member):
    """Prevent the bot from pinging this user or role."""
    if target.id in do_not_ping_list:
        await ctx.send(f"{target.mention} is already on the Do Not Ping list.")
        return

    
    await pingstop(ctx, target)

    do_not_ping_list.add(target.id)
    await ctx.send(f"{target.mention} has been added to the Do Not Ping list.")

@bot.command()
async def CanPing(ctx, target: discord.Role | discord.Member):
    """Allow the bot to ping this user or role again."""
    if target.id not in do_not_ping_list:
        await ctx.send(f"{target.mention} is not on the Do Not Ping list.")
        return

    do_not_ping_list.remove(target.id)
    await ctx.send(f"{target.mention} has been removed from the Do Not Ping list.")

Webserver.keep_alive()
bot.run(TOKEN)
