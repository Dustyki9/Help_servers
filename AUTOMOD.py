import ssl
import os
import discord
from discord.ext import commands
import json
import asyncio

ssl_context = ssl.create_default_context()
ssl_context.set_ciphers('ALL')
# Bot instance
intents = discord.Intents.default()
intents.messages = True  # Enable message-related events
intents.guilds = True  # Enable guild-related events
intents.members = True  # Enable member-related events
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Warnings storage (use a dictionary to store user warnings)
warnings = {}

# Banned words list
banned_words = ["poop"]


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if the message contains any banned words
    if any(banned_word in message.content.lower() for banned_word in banned_words):
        await message.delete()
        await message.channel.send(f"{message.author.mention} NO! YOU KNOW THAT IS A NO NO WORD")
        await issue_warning(message.author)

    # Process commands after handling the banned words
    await bot.process_commands(message)


async def issue_warning(user):
    # Issue a warning and store it in the warnings dictionary
    if user.id not in warnings:
        warnings[user.id] = 0
    warnings[user.id] += 1

    # Write warnings to a file
    with open("warnings.json", "w") as f:
        json.dump(warnings, f)

    # Notify the user about their warning
    await user.send(f"You have received a warning! Total warnings: {warnings[user.id]}")
@bot.event
async def on_message_delete(message):
    # Get the log channel (make sure it exists)
    log_channel = discord.utils.get(message.guild.text_channels, name="message-logs")

    if log_channel:
        # Create an embed to log the deleted message
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
    # Check if the bot has the necessary permissions to manage roles
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have permission to manage roles!")
        return

    # Check if the bot's role is high enough to mute
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role.position >= ctx.guild.me.top_role.position:
        await ctx.send("I cannot mute members higher than or equal to my role.")
        return

    if not muted_role:
        # If the "Muted" role doesn't exist, create it
        muted_role = await ctx.guild.create_role(name="Muted", reason="Mute role creation")

        # Set the role's permissions to deny send messages
        await muted_role.edit(permissions=discord.Permissions(send_messages=False))

    # Add the muted role to the member
    await member.add_roles(muted_role)
    await ctx.send(f"{member.mention} has been muted for {duration} minutes.")

    # Unmute the user after the specified duration
    await asyncio.sleep(duration * 60)  # Convert duration to seconds
    await member.remove_roles(muted_role)
    await ctx.send(f"{member.mention} has been unmuted.")

    # Delete the command message (the one the user typed)
    await ctx.message.delete()


@bot.command()
async def unmute(ctx, member: discord.Member):
    # Check if the bot has the necessary permissions to manage roles
    if not ctx.guild.me.guild_permissions.manage_roles:
        await ctx.send("I don't have permission to manage roles!")
        return

    # Check if the bot's role is high enough to unmute
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role and muted_role.position >= ctx.guild.me.top_role.position:
        await ctx.send("I cannot unmute members higher than or equal to my role.")
        return

    if muted_role not in member.roles:
        await ctx.send(f"{member.mention} is not muted.")
        return

    # Remove the "Muted" role from the member
    await member.remove_roles(muted_role)
    await ctx.send(f"{member.mention} has been unmuted.")

    # Delete the command message
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


bot.run('TOKEN')
