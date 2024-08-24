import atexit
import base64
import json
import os
import signal
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Loads environment variables from detected ".env"
load_dotenv()

guild_id = os.getenv("GUILD_ID")
bot = commands.Bot("!", intents=discord.Intents.all())
leaderboard_channel_id = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
secret_words = []


def on_kill(*args):
    sys.exit(0)


def does_file_exist(file_path):
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0


def is_owner(interaction):
    return interaction.user.id == int(os.getenv("OWNER_ID"))


def get_leaderboard_embed(description):
    return discord.Embed(title=os.getenv("LEADERBOARD_TITLE"), color=0x000000, description=description)


# Serializes updated and distinct leaderboard to "leaderboard.json"
def serialize_leaderboard():
    with open("leaderboard.json", "w") as outfile:
        json.dump(leaderboard, outfile)


async def add_to_leaderboard(message):
    description = ""

    # Adds one to user count for message author
    if str(message.author.id) not in leaderboard:
        leaderboard.update({str(message.author.id): 1})
    else:
        leaderboard[str(message.author.id)] += 1

    # Adds user leaderboard data to embed description string
    for user_id in leaderboard:
        description += f"<@{user_id}>: {leaderboard[user_id]}\n"

    # Updates first message in leaderboard channel with updated and formatted leaderboard
    async for channel_message in bot.get_channel(leaderboard_channel_id).history(oldest_first=True, limit=1):
        await channel_message.edit(embed=get_leaderboard_embed(description))

    await message.channel.send(
        f"Congratulations {message.author.mention} 🥳! You are the {leaderboard[str(message.author.id)]}th person "
        f"{os.getenv('CONGRATULATIONS_MESSAGE')}"
    )

    await message.add_reaction('🎉')
    await message.add_reaction('🥳')


# Converts bot latency from seconds to ms and sends it
@bot.tree.command(name="ping", description="Pings bot and returns latency", guild=discord.Object(id=guild_id))
async def ping(interaction):
    await interaction.response.send_message(
        f"{os.getenv('PING_MESSAGE')}\n```Latency: {round(bot.latency * 1000)}ms```")


@bot.tree.command(name="printleaderboard", description="Prints an empty leaderboard", guild=discord.Object(id=guild_id))
async def print_leaderboard(interaction):
    # Only allows owner to print leaderboard
    if is_owner(interaction):
        await bot.get_channel(leaderboard_channel_id).send(embed=get_leaderboard_embed(""))
        await interaction.response.send_message("Printed empty leaderboard to leaderboard channel!")
    else:
        await interaction.response.send_message(
            f"You do not have permission to run that command! {os.getenv('PERMISSION_MESSAGE')}"
        )


@bot.tree.command(name="printrules", description="Prints the rules", guild=discord.Object(id=guild_id))
async def print_rules(interaction):
    # Prints rules in rules channel if command sent by owner
    if is_owner(interaction):
        rules_channel = bot.get_channel(int(os.getenv("RULES_CHANNEL_ID")))
        await rules_channel.send(os.getenv("RULES"))
        await interaction.response.send_message("Printed rules to rules channel!")
    else:
        await interaction.response.send_message(os.getenv("RULES"))


# First function ran when client connects
@bot.event
async def on_ready():
    # Makes commands accessible by users in server
    await bot.tree.sync(guild=discord.Object(id=guild_id))
    print(f"Logged into server as: {bot.user}")


@bot.event
async def on_member_join(member):
    channel = await member.create_dm()
    await channel.send(f"Welcome to the server {member.mention}!")


# Runs on every message sent in any channel
@bot.event
async def on_message(message):
    # Does nothing when message is from the bot
    if message.author == bot.user:
        return

    for word in secret_words:
        if word in message.content:
            await add_to_leaderboard(message)


# Creates "leaderboard.json" file if it doesn't exist
if does_file_exist(os.path.join(os.path.dirname(__file__), "leaderboard.json")):
    # Deserializes dictionary from "leaderboard.json" into leaderboard variable
    with open("leaderboard.json", "r") as infile:
        leaderboard = json.load(infile)
else:
    leaderboard = {}

# Deserializes and decodes secret words list from "words.json"
with open("words.json", "r") as infile:
    # Puts all base64 decoded strings in "secret_words"
    for deserialized_word in json.load(infile):
        secret_words.append(
            str(base64.b64decode(deserialized_word))
            .replace("'", "", 2)
            .replace("b", "")
        )

# Serializes leaderboard on exit or kill
atexit.register(serialize_leaderboard)
signal.signal(signal.SIGINT, on_kill)
signal.signal(signal.SIGTERM, on_kill)

try:
    bot.run(os.getenv("TOKEN"))
except discord.errors.HTTPException:
    # Kills application on rate limited exception
    print("We are being rate limited! Shutting down now.")
    os.system("kill 1")
