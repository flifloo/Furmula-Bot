import shelve
from discord import NotFound, InvalidArgument, Embed
from discord.ext import commands

bot = commands.Bot(command_prefix="%")  # Set bot object and command prefix
bot.remove_command("help")  # Override default help command


def set_config(guild, conf):
    """guild : guild object, conf: shelve object
    Set configuration for server on configuration file"""
    print(f"Set config for {guild.name}")
    conf[str(guild.id)] = dict()  # Create default dictionary
    for opt in [["default_role_id", ""], ["reaction_messages", dict()]]:  # Set up each option in configuration file
        conf[str(guild.id)][opt[0]] = opt[1]


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
        if "default_role_id" in conf[str(member.guild.id)] and conf[str(member.guild.id)]["default_role_id"]:
            role = member.guild.get_role(conf[str(member.guild.id)]["default_role_id"][0])  # Get the role from guild
            await member.add_roles(role)


@bot.event
async def on_raw_reaction_add(payload):
    """payload: RawReaction payload object
    When a reaction is add check if is a role reaction and apply the request"""
    guild = bot.get_guild(payload.guild_id)  # Get the current guild
    member = guild.get_member(payload.user_id)  # Get the current member
    await reaction_role(payload.message_id, guild, str(payload.emoji), member, True)


@bot.event
async def on_raw_reaction_remove(payload):
    """payload: RawReaction payload object
    When a reaction is remove check if is a role reaction and apply the request"""
    guild = bot.get_guild(payload.guild_id)  # Get the current guild
    member = guild.get_member(payload.user_id)  # Get the current member
    await reaction_role(payload.message_id, guild, str(payload.emoji), member, False)


async def reaction_role(message_id, guild, emoji, member, state):
    """message_id: (int) the id of the message, guild: guild object, emoji: the reaction emoji, member: member object,
        state: (bool) add or remove target role
    Check the configuration and if available, set the link role to the player"""
    with shelve.open("config.conf") as conf:
        # Avoid bot user and check if message and reaction are in configuration
        if not member.bot and \
                "reaction_messages" in conf[str(guild.id)] and \
                message_id in conf[str(guild.id)]["reaction_messages"] and \
                emoji in conf[str(guild.id)]["reaction_messages"][message_id]:

            # If member has default new role, give him default role
            def_new_role = guild.get_role(conf[str(guild.id)]["default_role_id"][0])
            if def_new_role in member.roles:
                def_role = guild.get_role(conf[str(guild.id)]["default_role_id"][1])
                await member.remove_roles(def_new_role)
                await member.add_roles(def_role)

            role = guild.get_role(conf[str(guild.id)]["reaction_messages"][message_id][emoji])  # Get the target role

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
                                                   "default role and default role, if any role mentioned this disable "
                                                   "the option")
    embed.add_field(name="Default roles", value="``default_role`` show the default roles")
    embed.add_field(name="Reaction message", value="""``reaction_message <action> <message id> <...>``
    **__actions :__**
    ``set <message id>`` to set a reaction message
    ``unset <message id>`` to unset a reaction message
    ``add <message id> <reaction emoji> @role`` to add a reaction on set message
    ``remove <message id> <reaction emoji>`` to remove a reaction on set message""")
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
async def reaction_message(ctx, action=None, message_id=None, reaction=None):
    """ctx: context object, action: (str) command action, message_id: (str) the message id,
        reaction: (str) reaction emoji
    Set or unset a reaction message and add reaction emoji link with roles"""
    if action not in ["set", "unset", "add", "remove"]:  # Check if action is correct
        raise commands.BadArgument("argument")
    else:
        try:  # Check message id
            message = await ctx.fetch_message(int(message_id))
        except (TypeError, ValueError, NotFound):
            raise commands.BadArgument("message id")
        else:
            with shelve.open("config.conf", writeback=True) as conf:
                if action == "set":  # Set a reaction message
                    if message.id in conf[str(ctx.guild.id)]["reaction_messages"]:  # Check if not already set
                        raise commands.BadArgument("already set")
                    else:
                        conf[str(ctx.guild.id)]["reaction_messages"][message.id] = dict()  # Add to configuration
                        await ctx.send("Message set :white_check_mark:")
                elif action == "unset":  # Unset a reaction message
                    try:  # Check if the message is set when remove
                        del conf[str(ctx.guild.id)]["reaction_messages"][message.id]
                    except KeyError:
                        raise commands.BadArgument("not set")
                    else:
                        await ctx.send("Message remove :wastebasket:")
                else:  # Add and Remove reaction actions
                    if message.id not in conf[str(ctx.guild.id)]["reaction_messages"]:  # Check if message is set
                        raise commands.BadArgument("not set")
                    else:
                        if action == "add":  # Add reaction
                            if len(ctx.message.role_mentions) != 1:  # Check if correct mentioned role
                                raise commands.BadArgument("role")
                            else:
                                try:  # Add reaction to message and check if given emoji is correct
                                    await message.add_reaction(reaction)
                                except InvalidArgument:
                                    raise commands.BadArgument("reaction")
                                else:  # Add reaction and role to configuration
                                    conf[str(ctx.guild.id)]["reaction_messages"][message.id][reaction] =\
                                        ctx.message.role_mentions[0].id
                                    await ctx.send("Reaction add :white_check_mark:")
                        if action == "remove":  # Remove a reaction
                            try:  # Remove reaction from message and check if given emoji is correct
                                await message.remove_reaction(reaction, bot.user)
                            except (InvalidArgument, NotFound):
                                raise commands.BadArgument("reaction")
                            else:  # Delete reaction from configuration
                                del conf[str(ctx.guild.id)]["reaction_messages"][message.id][reaction]
                                await ctx.send("Reaction remove :wastebasket:")


@reaction_message.error
async def reaction_message_error(ctx, error):
    """ctx: context object, error: raised error
    Manage reaction_message command errors"""
    err = {"argument": "Invalid arguments !", "message id": "Invalid message id", "already set": "Message already set",
           "not set": "Message not set", "role": "Invalid mentioned role", "reaction": "Invalid reaction"}  # Database
    if str(error) in err:
        await ctx.send(f"{err[str(error)]} :x:")
    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You are missing Administrator permission to run this command ! :no_entry:")


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
