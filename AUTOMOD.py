import ssl
import os
import discord
import json
import asyncio
import re
import datetime
from discord import app_commands
from discord.ext import commands
from rapidfuzz import fuzz

ssl_context = ssl.create_default_context()
ssl_context.set_ciphers('ALL')

# Bot instance
intents = discord.Intents.default()
intents.messages = True  # Enable message-related events
intents.guilds = True  # Enable guild-related events
intents.members = True  # Enable member-related events
intents.message_content = True


GUILD_ID = 1170420782313259179  #South of Heaven 2.1.7
guild = discord.Object(id=GUILD_ID)


bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree  #Shortcut to access app_commands


#Vik's Shiiiet Slash commands.

@tree.command(name="timeout", description="Time-Out a member for a specified duration", guild=guild)
@app_commands.describe(
    member="The member to time-out",
    duration="Time-Out duration in minutes (1-10080)",
    reason="Reason for the Time-Out"
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    duration: int,
    reason: str = "No reason provided"
):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You don't have permission to Time-Out Members.", ephemeral=True)
        return

    if duration < 1 or duration > 10080:
        await interaction.response.send_message("Duration must be between 1-10080 minutes (7 days)", ephemeral=True)
        return

    try:
        timeout_duration = datetime.timedelta(minutes=duration)
        await member.timeout(timeout_duration, reason=reason)
        until_time = discord.utils.format_dt(discord.utils.utcnow() + timeout_duration, style='R')
        await interaction.response.send_message(
            f"{member.mention} has been timed out for {duration} minute(s). Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to Time-Out that member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


@tree.command(name="untimeout", description="Remove a Time-Out from a member.", guild=guild)
@app_commands.describe(
    member="The member to remove the Time-Out from",
    reason="Reason for the Removal"
)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You don't have permission to Un-Time-Out Members.", ephemeral=True)
        return

    try:
        await member.timeout(None, reason=reason)
        await interaction.response.send_message(
            f"Time-Out has been removed from {member.mention}. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to Un-Time-Out that member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error has occurred: {e}", ephemeral=True)


# Warnings storage (use a dictionary to store user warnings)
warnings = {}
if os.path.exists('warning.json'):
    with open('warning.json', 'r') as f:
        warnings = json.load(f)

ZERO_WIDTH_CHARS = [
    '\u200B', '\u200C', '\u200D', '\uFEFF'
]


def strip_zero_width(text: str) -> str:
    """Remove zero-width characters from text"""
    return ''.join(c for c in text if c not in ZERO_WIDTH_CHARS)


def soundex(word: str) -> str:
    word = word.upper()
    if not word:
        return ""
    # Soundex mappings
    codes = ("BFPV", "CGJKQSXZ", "DT", "L", "MN", "R")
    soundex_code = word[0]

    def char_to_code(c):
        for i, group in enumerate(codes, 1):
            if c in group:
                return str(i)
        return '0'

    last_code = char_to_code(soundex_code)
    for c in word[1:]:
        code = char_to_code(c)
        if code != '0' and code != last_code:
            soundex_code += code
        last_code = code

    soundex_code = soundex_code.ljust(4, '0')
    return soundex_code[:4]


# Build banned words soundex codes for phonetic matching
def build_soundex_map(words):
    return {word: soundex(word) for word in words}


# Emoji detection regex - detect emoji or symbols inside words
EMOJI_PATTERN = re.compile("["
                           "\U0001F600-\U0001F64F"  # emoticons
                           "\U0001F300-\U0001F5FF"  # symbols & pictographs
                           "\U0001F680-\U0001F6FF"  # transport & map symbols
                           "\U0001F1E0-\U0001F1FF"  # flags
                           "]+", flags=re.UNICODE)

# Banned words list
#  Enhanced pattern loader to detect spaced-out or symbol-separated banned words, including leetspeak

leet_dict = {
    'a': ['a', '@', '4'],
    'b': ['b', '8'],
    'c': ['c', '(', '<'],
    'e': ['e', '3'],
    'g': ['g', '9'],
    'h': ['h', '#'],
    'i': ['i', '1', '!', '|'],
    'l': ['l', '1', '|'],
    'o': ['o', '0'],
    's': ['s', '$', '5'],
    't': ['t', '7', '+'],
    'z': ['z', '2'],
}


def generate_variants(word):
    variants = [word]
    if not word.endswith('s'):
        variants.append(word + 's')
    if not word.endswith('es'):
        variants.append(word + 'es')
    if not word.endswith('ed'):
        variants.append(word + 'ed')
    if not word.endswith('ing'):
        variants.append(word + 'ing')
    return variants


import logging

logging.basicConfig(level=logging.INFO)


def build_banned_patterns(filepath):
    patterns = []
    words = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    words.append(word)
                    pattern = ''
                    for char in word:
                        if char in leet_dict:
                            # Removed space detection: no [\W_]*
                            pattern += f"[{''.join(re.escape(c) for c in leet_dict[char])}]"
                        else:
                            pattern += f"{re.escape(char)}"
                    patterns.append(re.compile(pattern, re.IGNORECASE))
    except FileNotFoundError:
        print(f"{filepath} not found. No banned words loaded.")
    return patterns, words


BANNED_PATTERNS, BANNED_WORDS = build_banned_patterns("BANNED_WORDS.txt")
BANNED_SOUNDEX_MAP = build_soundex_map(BANNED_WORDS)
MOD_LOG_CHANNEL_NAME = "message-logs"


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Strip zero-width chars before processing
    content = strip_zero_width(message.content.lower())
    # Remove emojis for word extraction (only for fuzzy check)
    content_no_emoji = EMOJI_PATTERN.sub('', content)

    # 1. Check regex banned patterns (with leetspeak + spacing)
    for pattern in BANNED_PATTERNS:
        if pattern.search(content):
            logging.info(f"Regex matched pattern: {pattern.pattern} on message: {content}")
            try:
                await message.delete()
            except discord.Forbidden:
                logging.warning(f"Could not delete message in #{message.channel}.")
            await issue_warning(message.author)
            return

    # 2. Fuzzy check for banned words
    FUZZY_THRESHOLD = 80  # Adjust threshold as needed (0-100)
    words = re.findall(r'\w+', content_no_emoji)
    for w in words:
        for banned_word in BANNED_WORDS:
            similarity = fuzz.ratio(w, banned_word)
            if similarity >= FUZZY_THRESHOLD:
                logging.info(f"Fuzzy match: '{w}' ~ '{banned_word}' (score: {similarity})")
                try:
                    await message.delete()
                except discord.Forbidden:
                    logging.warning(f"Could not delete message in #{message.channel}.")
                await issue_warning(message.author)
                return

    await bot.process_commands(message)


async def issue_warning(user):
    user_id_str = str(user.id)  # JSON keys must be strings
    if user_id_str not in warnings:
        warnings[user_id_str] = 0
    warnings[user_id_str] += 1

    with open("warnings.json", "w") as f:
        json.dump(warnings, f, indent=4)

    try:
        await user.send(f"You have received a warning! Total warnings: {warnings[user_id_str]}")
    except discord.Forbidden:
        print(f"Could not send DM to {user.name}.")


@bot.command()
async def test_banned(ctx, *, text: str):
    """Test banned words detection on arbitrary text."""
    stripped = strip_zero_width(text.lower())
    stripped_no_emoji = EMOJI_PATTERN.sub('', stripped)

    # Check regex patterns
    regex_hits = [p.pattern for p in BANNED_PATTERNS if p.search(stripped)]

    # Check phonetic hits
    words = re.findall(r'\w+', stripped_no_emoji)
    phonetic_hits = []
    for w in words:
        w_soundex = soundex(w)
        for banned_word, banned_soundex in BANNED_SOUNDEX_MAP.items():
            if w_soundex == banned_soundex:
                phonetic_hits.append(banned_word)

    hits = set(regex_hits + phonetic_hits)
    if hits:
        await ctx.send(f"Detected banned words or phonetic matches: {', '.join(hits)}")
    else:
        await ctx.send("No banned words detected.")


@bot.event
async def on_message_delete(message):
    log_channel = discord.utils.get(message.guild.text_channels, name=MOD_LOG_CHANNEL_NAME)
    if log_channel:
        embed = discord.Embed(
            title="Message Deleted",
            description=f"Message deleted in {message.channel.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="Author", value=message.author.mention)
        embed.add_field(name="Content", value=message.content or "No content")
        embed.set_footer(text=f"Message ID: {message.id}")
        await log_channel.send(embed=embed)


@bot.command()
async def mute(ctx, member: discord.Member, duration: int):
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have permission to manage roles!")
        return

    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted", reason="Mute role creation")
        await muted_role.edit(permissions=discord.Permissions(send_messages=False))

    if muted_role.position >= ctx.guild.me.top_role.position:
        await ctx.send("I cannot mute members higher than or equal to my role.")
        return

    await member.add_roles(muted_role)
    await ctx.send(f"{member.mention} has been muted for {duration} minutes.")

    await asyncio.sleep(duration * 60)
    await member.remove_roles(muted_role)
    await ctx.send(f"{member.mention} has been unmuted.")
    await ctx.message.delete()


#Viktor was here
@bot.command()
async def unmute(ctx, member: discord.Member):
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have permission to manage roles!")
        return

    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        await ctx.send(f"{member.mention} is not muted.")
        return

    if muted_role.position >= ctx.guild.me.top_role.position:
        await ctx.send("I cannot unmute members higher than or equal to my role.")
        return

    await member.remove_roles(muted_role)
    await ctx.send(f"{member.mention} has been unmuted.")
    await ctx.message.delete()


@bot.command()
async def add_role(ctx, member: discord.Member, role: discord.Role):
    # Check if the bot has the necessary permissions to manage roles
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have permission to manage roles!")
        return

    # Check if the bot's role is high enough to add the requested role
    if role.position >= ctx.guild.me.top_role.position:
        await ctx.send("I cannot assign roles higher than or equal to my role.")
        return

    # Add the role to the member
    await member.add_roles(role)
    await ctx.send(f"{role.name} role has been added to {member.mention}")


@bot.command()
async def remove_role(ctx, member: discord.Member, role: discord.Role):
    # Check if the bot has the necessary permissions to manage roles
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have permission to manage roles!")
        return

    # Check if the bot's role is high enough to remove the requested role
    if role.position >= ctx.guild.me.top_role.position:
        await ctx.send("I cannot remove roles higher than or equal to my role.")
        return

    # Remove the role from the member
    await member.remove_roles(role)
    await ctx.send(f"{role.name} role has been removed from {member.mention}")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Moderating the server!"))

    try:
        print("Syncing slash commands..")
        synced = await bot.tree.sync(guild=discord.Object(id=1170420782313259179))
        print(f"Synced {len(synced)} slash command(s):")
        for cmd in synced:
            print(f" - {cmd.name}: {cmd.description}")
    except Exception as e:
        print(f" Failed to sync commands: {e}")


bot.run('YOUR_BOT_TOKEN')
