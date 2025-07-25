import os
import discord
import asyncio
import re
import datetime
import sys
import ssl
import sqlite3
from discord import app_commands
from discord.ext import commands
from rapidfuzz import fuzz
from datetime import timezone


def load_banned_words(filepath="BANNED_WORDS.txt"):
    try:
        with open("BANNED_WORDS.txt", "r", encoding="utf-8") as file:
            return [line.strip().lower() for line in file if line.strip()]
    except FileNotFoundError:
        print("BANNED_WORDS.txt not found. Fix your shit cuh.")
        return[]

banned_words = load_banned_words()
conn = sqlite3.connect('warnings.db')
c = conn.cursor()
c.execute('''
          CREATE TABLE IF NOT EXISTS warnings (
                                                  user_id TEXT,
                                                  reason TEXT,
                                                  timestamp TEXT
          )
          ''')
conn.commit()


ssl_context = ssl.create_default_context()
ssl_context.set_ciphers('ALL')

AUTO_TIMEOUT_THRESHOLD = 3  # Number of warnings to trigger timeout
AUTO_TIMEOUT_DURATION_MINUTES = 4  # Duration of timeout in minutes

def load_warnings_from_db():
    c.execute('SELECT user_id, COUNT(*) FROM warnings GROUP BY user_id')
    rows = c.fetchall()
    for user_id, count in rows:
        warnings[user_id] = count

warnings = {}
load_warnings_from_db()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def log_warning(user_id, reason):
    timestamp = datetime.datetime.now().isoformat()
    c.execute('INSERT INTO warnings (user_id, reason, timestamp) VALUES (?, ?, ?)', (user_id, reason, timestamp))
    conn.commit()


def get_warning_count(user_id):
    c.execute('SELECT COUNT(*) FROM warnings WHERE user_id = ?', (user_id,))
    return c.fetchone()[0]
    return results[0] if results else 0



# Bot instance
intents = discord.Intents.default()
intents.messages = True  # Enable message-related events
intents.guilds = True  # Enable guild-related events
intents.members = True  # Enable member-related events
intents.message_content = True


GUILD_ID = #GUILD ID GO HERE
guild = discord.Object(id=GUILD_ID) #<----DO NOT CHANGE NO NEED.


def is_admin():
    def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree  #Shortcut to access app_commands


#Vik's Shiiiet Slash commands.

@tree.command(name="timeout", description="Time-Out a member for a specified duration", guild=guild)
@is_admin()
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
@is_admin()
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

@tree.command(name="mute", description="Mute a member for a number of minutes", guild=guild)
@is_admin()
@app_commands.describe(member="Member to mute", duration="Mute duration in minutes")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int):
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I don't have permission to manage roles!", ephemeral=True)
        return

    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await interaction.guild.create_role(name="Muted", reason="Mute role creation")
        await muted_role.edit(permissions=discord.Permissions(send_messages=False))

    if muted_role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message("I cannot mute members above or equal to my role.", ephemeral=True)
        return

    await member.add_roles(muted_role)
    await interaction.response.send_message(f"{member.mention} has been muted for {duration} minutes.")

    await asyncio.sleep(duration * 60)
    await member.remove_roles(muted_role)
    try:
        await interaction.channel.send(f"{member.mention} has been unmuted.")
    except Exception:
        pass


@tree.command(name="unmute", description="Unmute a member", guild=guild)
@is_admin()
@app_commands.describe(member="Member to unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I don't have permission to manage roles!", ephemeral=True)
        return

    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        await interaction.response.send_message(f"{member.mention} is not muted.", ephemeral=True)
        return

    if muted_role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message("I cannot unmute members above or equal to my role.", ephemeral=True)
        return

    await member.remove_roles(muted_role)
    await interaction.response.send_message(f"{member.mention} has been unmuted.")


@tree.command(name="add_role", description="Add a role to a member", guild=guild)
@is_admin()
@app_commands.describe(member="Member to add the role to", role="Role to assign")
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I don't have permission to manage roles!", ephemeral=True)
        return

    if role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message("I can't assign roles higher than or equal to my top role.", ephemeral=True)
        return

    await member.add_roles(role)
    await interaction.response.send_message(f"{role.name} role has been added to {member.mention}.")


@tree.command(name="remove_role", description="Remove a role from a member", guild=guild)
@is_admin()
@app_commands.describe(member="Member to remove the role from", role="Role to remove")
async def remove_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I don't have permission to manage roles!", ephemeral=True)
        return

    if role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message("I can't remove roles higher than or equal to my top role.", ephemeral=True)
        return

    await member.remove_roles(role)
    await interaction.response.send_message(f"{role.name} role has been removed from {member.mention}.")


@tree.command(name="test_banned", description="Test a message for banned words", guild=guild)
@is_admin()
@app_commands.describe(text="Text to check")
async def test_banned(interaction: discord.Interaction, text: str):
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
        await interaction.response.send_message(f"Detected banned words or phonetic matches: {', '.join(hits)}")
    else:
        await interaction.response.send_message("No banned words detected.")


@tree.command(name="warn", description="Warn a user", guild=guild)
@is_admin()
@app_commands.describe(member="Member to warn", reason="Reason for warning")
async def warn_user(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    # Log the warning in DB
    log_warning(str(member.id), reason)
    count = get_warning_count(str(member.id))

    # Issue warning (this function probably updates in-memory dict + sends DM)
    await issue_warning(member, reason=reason)

    # Respond to command
    await interaction.response.send_message(
        f"⚠️ WARNED {member.mention} for: {reason}\nThey now have **{count} warning(s)**"
    )

    # Try to DM the member
    try:
        await member.send(f"You were warned in {interaction.guild.name} for: {reason}")
    except discord.Forbidden:
       pass

@tree.command(name="reload", description="Reload Banned word database.", guild=guild)
@is_admin()
async def reload_banned_words(interaction: discord.Interaction):
    global BANNED_PATTERNS, BANNED_WORDS, BANNED_SOUNDEX_MAP

    banned_words = load_banned_words()  # no argument here
    BANNED_PATTERNS, _ = build_banned_patterns("BANNED_WORDS.txt")
    BANNED_SOUNDEX_MAP = build_soundex_map(banned_words)
    print(f"[Reload] Loaded {len(banned_words)} banned words.")
    await interaction.response.send_message("Banned words database reloaded.")


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
            await issue_warning(message.author, message=message, reason="Banned word detected")
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


async def issue_warning(user, message=None, reason="No reason provided"):
    user_id_str = str(user.id)
    log_warning(user_id_str, reason)
    total_warnings = get_warning_count(user_id_str)


    # Send log message to log channel
    if message and message.guild:
        log_channel = discord.utils.get(message.guild.channels, name="message-logs")
        if log_channel:
            embed = discord.Embed(
                title="Message Deleted and User Warned",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.add_field(name="User", value=f"{user.mention} (ID: {user.id})", inline=False)
            embed.add_field(name="Total Warnings", value=str(total_warnings), inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Deleted Message", value=message.content or "[No Content]", inline=False)
            embed.add_field(name="Channel", value=message.channel.mention, inline=False)
            embed.set_footer(text=f"Message ID: {message.id}")
            await log_channel.send(embed=embed)

    try:
        await user.send(f"You have received a warning! Total warnings: {total_warnings}\nReason: {reason}")
    except discord.Forbidden:
        print(f"Could not send DM to {user.name}.")

    # Apply automatic timeout if warning threshold is met
    if total_warnings >= AUTO_TIMEOUT_THRESHOLD:
        guild = message.guild if message else None
        if guild:
            member = guild.get_member(user.id)
            if member:
                timeout_duration = datetime.timedelta(minutes=AUTO_TIMEOUT_DURATION_MINUTES)
                try:
                    await member.timeout(timeout_duration, reason=f"Reached {AUTO_TIMEOUT_THRESHOLD} warnings")

                    if log_channel:
                        await log_channel.send(
                            f"{member.mention} has been automatically timed out for {AUTO_TIMEOUT_DURATION_MINUTES} minutes after {total_warnings} warnings."
                        )

                    try:
                        await user.send(
                            f"You have been timed out for {AUTO_TIMEOUT_DURATION_MINUTES} minutes because you reached {AUTO_TIMEOUT_THRESHOLD} warnings."
                        )
                    except discord.Forbidden:
                        pass
                except discord.Forbidden:
                    print(f"Failed to timeout {user.name} - missing permissions.")

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
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Moderating the server!"))

    try:
        print("Syncing slash commands..")
        synced = await bot.tree.sync(guild=discord.Object(id=#GUILD ID HERE))
        print(f"Synced {len(synced)} slash command(s):")
        for cmd in synced:
            print(f" - {cmd.name}: {cmd.description}")
    except Exception as e:
        print(f" Failed to sync commands: {e}")

bot.run(#PUT TOKEN HERE )