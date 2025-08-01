import discord
from discord.ext import commands, tasks
import asyncio
import os
import Webserver

TOKEN = os.enviorn['discordkey']  # Replace with your bot token
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Store tasks per user
ping_tasks = {}

@bot.command()
async def pingstart(ctx, member: discord.Member, interval: int = 5):
    """Start pinging a user every `interval` seconds."""
    if member.id in ping_tasks:
        await ctx.send(f"Already pinging {member.mention}!")
        return

    async def ping_loop():
        try:
            while True:
                await ctx.send(f"{member.mention} 👋")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass  # Task cancelled gracefully

    task = asyncio.create_task(ping_loop())
    ping_tasks[member.id] = task
    await ctx.send(f"Started pinging {member.mention} every {interval} seconds.")

@bot.command()
async def pingstop(ctx, member: discord.Member):
    """Stop pinging the user."""
    task = ping_tasks.pop(member.id, None)
    if task:
        task.cancel()
        await ctx.send(f"Stopped pinging {member.mention}.")
    else:
        await ctx.send(f"{member.mention} was not being pinged.")

Webserver.keep_alive()
bot.run(TOKEN)
