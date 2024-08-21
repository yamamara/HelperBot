import discord
import os

from discord.ext import commands
from dotenv import load_dotenv

bot = commands.Bot("!", intents=discord.Intents.all())


# First function ran when client connects
@bot.event
async def on_ready():
    print(f'Logged into server as: {bot.user}')


# Runs on every message sent in any channel
@bot.event
async def on_message(message):
    # Does nothing when message is from the bot
    if message.author == bot.user:
        return

# Loads environment variables from detected ".env"
load_dotenv()

try:
    bot.run(os.getenv('TOKEN'))
except discord.errors.HTTPException:
    print("We are being rate limited! Restarting now.")
    os.system('kill 1')
