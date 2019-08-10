import shelve
from discord import NotFound, InvalidArgument, HTTPException, Embed
from discord.ext import commands
from asyncio import sleep

bot = commands.Bot(command_prefix="%")  # Set bot object and command prefix
bot.remove_command("help")  # Override default help command
purges = dict()


def set_config(guild, conf):
    """guild : guild object, conf: shelve object
    Set configuration for server on configuration file"""
    print(f"Set config for {guild.name}")
    conf[str(guild.id)] = dict()  # Create default dictionary
    for opt in [["default_role_id", ""], ["reaction", dict()]]:  # Set up each option in configuration file
        conf[str(guild.id)][opt[0]] = opt[1]


async def find_message(guild, message_id):
    """guild: guild object, messgae_id: (in) message id
    Find a message on a guild"""
    message = None
    for c in guild.text_channels:
        try:  # Check message id
            message = await c.fetch_message(int(message_id))
        except NotFound:
            pass
        else:
            break
    return message


async def clean_reaction(message, emoji):
    """message: message object, emoji, target emoji
    Clean all reaction of a specific message and emoji"""
    for r in message.reactions:
        if str(r) == emoji:
            async for u in r.users():
                await r.remove(u)


async def event_check(guild_id=None, message_id=None, user_id=None, emoji=None):
    """guild_id: (int) the guild id, message_id: (int) the message id
    Check if the event touch a message in config and remove it if needed"""
    if message_id and user_id and guild_id:  # If bot reaction is remove
        with shelve.open("config.conf", writeback=True) as conf:
            guild = bot.get_guild(guild_id)
            if message_id in conf[str(guild.id)]["reaction"] and user_id == bot.user.id:
                message = await find_message(guild, message_id)
                await clean_reaction(message, emoji)
                del conf[str(guild.id)]["reaction"][message_id][emoji]
                if len(conf[str(guild.id)]["reaction"][message_id]) == 0:
                    del conf[str(guild.id)]["reaction"][message_id]
                return True
        return False
    elif guild_id and message_id:  # If message reaction is remove
        with shelve.open("config.conf", writeback=True) as conf:
            guild = bot.get_guild(guild_id)
            if message_id in conf[str(guild.id)]["reaction"]:
                del conf[str(guild.id)]["reaction"][message_id]
                return True
        return False


@bot.event
async def on_ready():
    """When bot start check if guilds doesn't need configuration"""
    with shelve.open("config.conf", writeback=True) as conf:
        for g in bot.guilds:  # Check each guild
            if str(g.id) not in conf:
                set_config(g, conf)

    print("FurrMula Bot online !")


@bot.event
async def on_guild_join(guild):
    """guild: guild object
    If the bot get a new guild, setup the configuration"""
    with shelve.open("config.conf", writeback=True) as conf:
        set_config(guild, conf)


@bot.event
async def on_member_join(member):
    """member: member object
    If available, add a default role to new members of guild"""
    with shelve.open("config.conf") as conf:
        if conf[str(member.guild.id)]["default_role_id"]:
            role = member.guild.get_role(conf[str(member.guild.id)]["default_role_id"][0])  # Get the role from guild
            await member.add_roles(role)


@bot.event
async def on_raw_reaction_add(payload):
    """payload: RawReaction payload object
    When a reaction is add check if is a role reaction and apply the request"""
    guild = bot.get_guild(payload.guild_id)  # Get the current guild
    member = guild.get_member(payload.user_id)  # Get the current member

    if payload.user_id in purges:
        if payload.channel_id == purges[member.id].channel.id:
            channel = guild.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            async with channel.typing():
                await channel.purge(before=purges[payload.user_id], after=message)
                await purges[payload.user_id].delete()
                await message.delete()
                del purges[payload.user_id]
    else:
        await reaction_role(payload.message_id, guild, str(payload.emoji), member, True)


@bot.event
async def on_raw_reaction_remove(payload):
    """payload: RawReaction payload object
    When a reaction is remove check if is a role reaction and apply the request"""
    if not await event_check(payload.guild_id, payload.message_id, payload.user_id, str(payload.emoji)):  # Event check
        guild = bot.get_guild(payload.guild_id)  # Get the current guild
        member = guild.get_member(payload.user_id)  # Get the current member
        await reaction_role(payload.message_id, guild, str(payload.emoji), member, False)


@bot.event
async def on_raw_message_delete(payload):
    """payload: RawMessageDelete payload object
    When a message is remove check if is not in configuration to delete it"""
    await event_check(payload.guild_id, payload.message_id)


@bot.event
async def on_raw_reaction_clear(payload):
    """payload: RawReactionClear payload object
    When a reaction clear check if is not in configuration to delete it"""
    await event_check(payload.guild_id, payload.message_id)


async def reaction_role(message_id, guild, emoji, member, state):
    """message_id: (int) the id of the message, guild: guild object, emoji: the reaction emoji, member: member object,
        state: (bool) add or remove target role
    Check the configuration and if available, set the link role to the player"""
    with shelve.open("config.conf") as conf:
        # Avoid bot user and check if message and reaction are in configuration
        if not member.bot and \
                "reaction" in conf[str(guild.id)] and \
                message_id in conf[str(guild.id)]["reaction"] and \
                emoji in conf[str(guild.id)]["reaction"][message_id]:

            # If member has default new role, give him default role
            if conf[str(member.guild.id)]["default_role_id"]:
                def_new_role = guild.get_role(conf[str(guild.id)]["default_role_id"][0])
                if def_new_role in member.roles:
                    def_role = guild.get_role(conf[str(guild.id)]["default_role_id"][1])
                    await member.remove_roles(def_new_role)
                    await member.add_roles(def_role)

            role = guild.get_role(conf[str(guild.id)]["reaction"][message_id][emoji])  # Get the target role

            # State-dependent action
            if state:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)


@bot.command(name="help")
@commands.has_permissions(administrator=True)
async def help_cmd(ctx):
    embed = Embed(title="Help", description="", color=0xffff00)
    embed.add_field(name="Set default role", value="``set_default_roles @new_default @default`` to set new member "
                                                   "default role and default role, if no role mentioned this disable "
                                                   "the option")
    embed.add_field(name="Default roles", value="``default_role`` show the default roles")
    embed.add_field(name="Reaction", value="""``reaction <action> <...>``
    **__actions :__**
    ``add <message id> <reaction emoji> @role`` to add/edit a reaction on message
    ``remove <message id> <reaction emoji>`` to remove a reaction on message
    ``remove-all <message id>`` to remove all reactions of a message""")
    embed.add_field(name="Reaction list", value="``reaction_list`` show the list of message with role reaction on the "
                                                "guild ")
    await ctx.send(embed=embed)


@help_cmd.error
async def help_cmd_error(ctx, error):
    """ctx: context object, error: raised error
    Manage help_cmd command errors"""
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Administrator permission to run this command ! :no_entry:")


@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def set_default_roles(ctx):
    """ctx: context object
    Set the default role of a guild"""
    with shelve.open("config.conf", writeback=True) as conf:
        if len(ctx.message.role_mentions) == 2:  # Accept only two mentioned role
            conf[str(ctx.guild.id)]["default_role_id"] = [ctx.message.role_mentions[0].id,
                                                          ctx.message.role_mentions[1].id]  # Set in configuration
            await ctx.send(f"Roles ``{ctx.message.role_mentions[0].name}`` and ``{ctx.message.role_mentions[1].name}``"
                           f" set to default role :white_check_mark:")
        elif len(ctx.message.role_mentions) == 0:  # If any role, disable default role option
            conf[str(ctx.guild.id)]["default_role_id"] = ""  # Set in configuration
            await ctx.send("Default role disabled :warning:")
        else:  # If invalid arguments
            raise commands.BadArgument


@set_default_roles.error
async def set_default_roles_error(ctx, error):
    """ctx: context object, error: raised error
    Manage set_default_roles command errors"""
    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid mentioned role ! :x:")
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Administrator permission to run this command ! :no_entry:")


@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def default_role(ctx):
    """ctx: context object
    Show guild default roles"""
    with shelve.open("config.conf") as conf:
        new_role = ctx.guild.get_role(conf[str(ctx.guild.id)]["default_role_id"][0]).name  # Get new role
        role = ctx.guild.get_role(conf[str(ctx.guild.id)]["default_role_id"][1]).name  # Get default role
        await ctx.send(f"Guild default roles: ``{new_role}`` and ``{role}``")


@default_role.error
async def default_role_error(ctx, error):
    """ctx: context object, error: raised error
    Manage default_role command errors"""
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Administrator permission to run this command ! :no_entry:")


@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def reaction(ctx, action, message_id, emoji=None):
    """ctx: context object, action: (str) command action, message_id: (str) the message id,
        emoji: (str) reaction emoji
    Set or unset a reaction message and add reaction emoji link with roles"""
    if action not in ["add", "remove", "remove-all"]:  # Check if action is correct
        raise commands.BadArgument("argument")
    else:
        try:
            message_id = int(message_id)
            message = await find_message(ctx.guild, message_id)
            if not message:
                raise ValueError
        except ValueError:
            raise commands.BadArgument("message id")

        with shelve.open("config.conf", writeback=True) as conf:
            if message.id not in conf[str(ctx.guild.id)]["reaction"]:  # Check if not already set
                conf[str(ctx.guild.id)]["reaction"][message.id] = dict()  # Add to configuration
            if action == "add":  # Add reaction
                if len(ctx.message.role_mentions) != 1:  # Check if correct mentioned role
                    raise commands.BadArgument("role")
                else:
                    try:  # Add reaction to message and check if given emoji is correct
                        await message.add_reaction(emoji)
                    except (InvalidArgument, NotFound, HTTPException):
                        raise commands.BadArgument("reaction")
                    else:  # Add reaction and role to configuration
                        conf[str(ctx.guild.id)]["reaction"][message.id][emoji] =\
                            ctx.message.role_mentions[0].id
                        await ctx.send("Reaction add :white_check_mark:")

            elif action == "remove":  # Remove a reaction
                try:  # Remove reaction from message and check if given emoji is correct
                    await message.remove_reaction(emoji, bot.user)
                    await clean_reaction(message, emoji)
                except (InvalidArgument, NotFound, HTTPException):
                    raise commands.BadArgument("reaction")
                else:  # Delete reaction from configuration
                    del conf[str(ctx.guild.id)]["reaction"][message.id][emoji]
                    if len(conf[str(ctx.guild.id)]["reaction"][message.id]) == 0:  # Clean if no reaction left
                        del conf[str(ctx.guild.id)]["reaction"][message.id]
                    await ctx.send("Reaction remove :wastebasket:")

            elif action == "remove-all":  # Remove all reactions
                for r in conf[str(ctx.guild.id)]["reaction"][message.id]:
                    try:  # Remove all reaction from message
                        await message.remove_reaction(r, bot.user)
                        await clean_reaction(message, r)
                    except (InvalidArgument, NotFound, HTTPException):
                        pass
                del conf[str(ctx.guild.id)]["reaction"][message.id]
                await ctx.send("All reactions remove :wastebasket:")


@reaction.error
async def reaction_error(ctx, error):
    print(error)
    """ctx: context object, error: raised error
    Manage reaction command errors"""
    err = {"argument": "Invalid arguments !", "message id": "Invalid message id", "already set": "Message already set",
           "not set": "Message not set", "role": "Invalid mentioned role", "reaction": "Invalid reaction"}  # Database
    if str(error) in err:
        await ctx.send(f"{err[str(error)]} :x:")
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Administrator permission to run this command ! :no_entry:")


@bot.command()
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def reaction_list(ctx):
    """ctx: context object
    Show a list of all message with reaction role on the guild"""
    embed = Embed(title="Reaction list", description="", color=0xffff00)
    with shelve.open("config.conf", writeback=True) as conf:
        for m in conf[str(ctx.guild.id)]["reaction"]:  # All message in configuration
            message = await find_message(ctx.guild, m)
            if not message:  # Clean if message not found
                del conf[str(ctx.guild.id)]["reaction"][m]
            else:
                reactions = str()
                for r in conf[str(ctx.guild.id)]["reaction"][m]:  # All reaction of message
                    role = ctx.guild.get_role(conf[str(ctx.guild.id)]['reaction'][m][r])
                    if not role:  # Clean if can't get role
                        await clean_reaction(message, r)
                        del conf[str(ctx.guild.id)]['reaction'][m][r]
                    else:
                        reactions += f"{r} - ``{role.name}``\n"
                if len(conf[str(ctx.guild.id)]["reaction"][m]) == 0:  # Clean if any reaction left
                    del conf[str(ctx.guild.id)]["reaction"][m]
                else:
                    embed.add_field(name=f"{m} [{message.channel.name}]", value=reactions, inline=False)
        if len(embed.fields) == 0:
            embed.add_field(name="Empty", value="No message with reaction on this guild :/")
        await ctx.send(embed=embed)


@reaction_list.error
async def reaction_list_error(ctx, error):
    """ctx: context object, error: raised error
    Manage reaction_list command errors"""
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Administrator permission to run this command ! :no_entry:")


@bot.command()
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
async def purge(ctx):
    purges[ctx.message.author.id] = ctx.message
    await ctx.message.add_reaction("👍")

    await sleep(2*60)
    try:
        if purges[ctx.message.author.id] == ctx.message:
            await ctx.message.clear_reactions()
            del purges[ctx.message.author.id]
    except (KeyError, HTTPException):
        pass


@reaction_list.error
async def reaction_list_error(ctx, error):
    print(error)
    """ctx: context object, error: raised error
    Manage reaction_list command errors"""
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Manage messages permission to run this command ! :no_entry:")


@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    """ctx: context object
    Owner shutdown command"""
    if await bot.is_owner(ctx.author):
        await ctx.send("Shutdown ! :wave:")
        await bot.logout()
        await bot.close()


@shutdown.error
async def shutdown_error(ctx, error):
    """ctx: context object, error: raised error
    Manage shutdown command errors"""
    if isinstance(error, commands.errors.NotOwner):
        await ctx.send("You do not own this bot ! :no_entry:")


@bot.command()
@commands.is_owner()
async def debug(ctx, config=None):
    """ctx: context object, config: (str) configuration entry to check"""
    if await bot.is_owner(ctx.author):
        with shelve.open("config.conf") as conf:
            data = conf[str(ctx.guild.id)]  # Add all guild configuration
            if config:  # If specified send only target configuration
                data = data[config]
            await ctx.send(f"``{data}``")


@debug.error
async def debug_error(ctx, error):
    """ctx: context object, error: raised error
    Manage debug command errors"""
    if isinstance(error, commands.errors.NotOwner):
        await ctx.send("You do not own this bot ! :no_entry:")


bot.run(open("token.ini").read())  # Get token from token.ini and start the bot
