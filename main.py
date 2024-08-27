import atexit
import base64
import json
import os
import random
import signal
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Loads environment variables from detected ".env"
load_dotenv()

guild_id = os.getenv("GUILD_ID")
bot = commands.Bot("!", intents=discord.Intents.all())
verification_channel_id = int(os.getenv("VERIFICATION_CHANNEL_ID"))
leaderboard_channel_id = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
unverified_role_id = int(os.getenv("UNVERIFIED_ROLE_ID"))
secret_words = []


# Custom "Buttons" class that executes code on click instead of only URL
class Buttons(discord.ui.View):
    def __init__(self, *, timeout=180, message):
        super().__init__(timeout=timeout)
        self.message = message

    # Removes unverified role of user on click of "Accept" button
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction, button):
        # Cross-checks author ID with member ID since DM message returns "User" object
        for member in bot.get_all_members():
            if member.id == self.message.author.id:
                guild = bot.get_guild(int(guild_id))
                member = guild.get_member(member.id)
                await member.remove_roles(guild.get_role(unverified_role_id))

        # Disables both "Accept" and "Deny" buttons
        for button in self.children:
            button.disabled = True

        embed = interaction.message.embeds[0]
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.response.defer()

    # Disables both buttons on click of "Disable" button
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction, button):
        for button in self.children:
            button.disabled = True

        embed = interaction.message.embeds[0]
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.response.defer()


# Runs exit code on OS signals instead of immediately killing
def on_kill(*args):
    sys.exit(0)


def does_file_exist(file_path):
    return os.path.isfile(file_path) and os.path.getsize(file_path) > 0


def is_owner(message_author):
    return message_author.id == int(os.getenv("OWNER_ID"))


def is_dm(interaction):
    return isinstance(interaction.channel, discord.channel.DMChannel)


def get_leaderboard_embed(description):
    return discord.Embed(title=os.getenv("LEADERBOARD_TITLE"), color=0x000000, description=description)


# Adds user leaderboard data to returned description string
def get_leaderboard_string():
    description = ""

    for user_id in leaderboard:
        description += f"<@{user_id}>: {leaderboard[user_id]}\n"

    return description


# Serializes updated and distinct leaderboard to "leaderboard.json"
def serialize_leaderboard():
    print(f"Serializing leaderboard: {leaderboard}")

    with open("leaderboard.json", "w") as outfile:
        json.dump(leaderboard, outfile)


def get_number_with_suffix(number):
    if 10 <= number % 100 <= 19:
        suffix = "th"
    elif number % 10 == 1:
        suffix = "st"
    elif number % 10 == 2:
        suffix = "nd"
    elif number % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"

    return number + suffix


async def add_to_leaderboard(message):
    # Adds one to leaderboard count for message author
    if str(message.author.id) not in leaderboard:
        leaderboard.update({str(message.author.id): 1})
    else:
        leaderboard[str(message.author.id)] += 1

    # Updates first message in leaderboard channel with updated and formatted leaderboard
    async for channel_message in bot.get_channel(leaderboard_channel_id).history(oldest_first=True, limit=1):
        await channel_message.edit(embed=get_leaderboard_embed(get_leaderboard_string()))

    await message.channel.send(
        f"Congratulations {message.author.mention} 🥳! "
        f"You are the {get_number_with_suffix(leaderboard[str(message.author.id)])}th person "
        f"{os.getenv('CONGRATULATIONS_MESSAGE')}"
    )

    await message.add_reaction('🎉')
    await message.add_reaction('🥳')


# Converts bot latency from seconds to ms and sends it
@bot.tree.command(name="ping", description="Pings bot and returns latency", guild=discord.Object(id=guild_id))
async def ping(interaction):
    await interaction.response.send_message(
        f"{os.getenv('PING_MESSAGE')}\n```Latency: {round(bot.latency * 1000)}ms```")


@bot.tree.command(name="leaderboard", description="Prints the current leaderboard", guild=discord.Object(id=guild_id))
async def leaderboard(interaction):
    # Adds user and count data from leaderboard into embed
    await interaction.response.send_message(embed=get_leaderboard_embed(get_leaderboard_string()))


@bot.tree.command(name="rules", description="Prints the rules", guild=discord.Object(id=guild_id))
async def rules(interaction):
    await interaction.response.send_message(os.getenv("RULES"))


# First function ran when client connects
@bot.event
async def on_ready():
    # Makes commands accessible by users in server
    await bot.tree.sync(guild=discord.Object(id=guild_id))
    print(f"Logged into server as: {bot.user}")
    print(f"Current leaderboard: {leaderboard}")


@bot.event
async def on_member_join(member):
    # Makes members unverified on join
    await member.add_roles(member.guild.get_role(unverified_role_id))

    # Sends DM to new members with welcome messages
    dm = await member.create_dm()
    await dm.send(os.getenv("WELCOME_MESSAGE_1"))
    await dm.send(os.getenv("WELCOME_MESSAGE_2"))


# Runs on every message sent in any channel
@bot.event
async def on_message(message):
    # Does nothing when message is from the bot
    if message.author == bot.user:
        return

    # Handles verification response if sent from DM
    if is_dm(message):
        verification_channel = bot.get_channel(verification_channel_id)

        # Sends DM response in verification channel as embed with random color
        await verification_channel.send(embed=discord.Embed(
            title=f"{message.author.name} appears",
            color=random.randint(1, 16777215),
            description=message.content
        ), view=Buttons(message=message))

        await message.channel.send(os.getenv("VERIFICATION_MESSAGE"))
    else:
        # Only allows owner to print empty leaderboard and rules in respective channels
        if message.content == "owner print leaderboard":
            if is_owner(message.author):
                await bot.get_channel(leaderboard_channel_id).send(embed=get_leaderboard_embed(""))
                await message.channel.send("Printed empty leaderboard to leaderboard channel!")
            else:
                await message.channel.send(os.getenv('PERMISSION_MESSAGE'))
        elif message.content == "owner print rules":
            if is_owner(message.author):
                rules_channel = bot.get_channel(int(os.getenv("RULES_CHANNEL_ID")))
                await rules_channel.send(os.getenv("RULES"))
                await message.channel.send("Printed rules to rules channel!")
            else:
                await message.channel.send(os.getenv("PERMISSION_MESSAGE"))

        # Only checks for secret word in server not DMs
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
