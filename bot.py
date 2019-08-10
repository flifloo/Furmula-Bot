import shelve
from discord import NotFound, InvalidArgument
from discord.ext import commands

bot = commands.Bot(command_prefix="%")


def set_config(guild, conf):
    print(f"Set config for {guild.name}")
    conf[str(guild.id)] = dict()
    for opt in [["default_role_id", ""], ["reaction_messages", dict()]]:
        conf[str(guild.id)][opt[0]] = opt[1]


@bot.event
async def on_ready():
    with shelve.open("config.conf", writeback=True) as conf:
        for g in bot.guilds:
            if str(g.id) not in conf:
                set_config(g, conf)

    print("FurrMula Bot online !")


@bot.event
async def on_guild_join(guild):
    with shelve.open("config.conf", writeback=True) as conf:
        set_config(guild, conf)


@bot.event
async def on_member_join(member):
    with shelve.open("config.conf") as conf:
        if "default_role_id" in conf[str(member.guild.id)] and conf[str(member.guild.id)]["default_role_id"]:
            role = member.guild.get_role(conf[str(member.guild.id)]["default_role_id"])
            await member.add_roles(role)


@bot.event
async def on_raw_reaction_add(payload):
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    await reaction_role(payload.message_id, guild, str(payload.emoji), member, True)


@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    await reaction_role(payload.message_id, guild, str(payload.emoji), member, False)


async def reaction_role(message_id, guild, emoji, member, state):
    with shelve.open("config.conf") as conf:
        if not member.bot and \
                "reaction_messages" in conf[str(guild.id)] and \
                message_id in conf[str(guild.id)]["reaction_messages"] and \
                emoji in conf[str(guild.id)]["reaction_messages"][message_id]:

            role = guild.get_role(conf[str(guild.id)]["reaction_messages"][message_id][emoji])

            if state:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)


@bot.command()
async def shutdown(ctx):
    if await bot.is_owner(ctx.author):
        await ctx.send("Shutdown !")
        await bot.logout()
        await bot.close()
    else:
        await ctx.send("Not allowed !")


@bot.command()
@commands.guild_only()
async def set_default_role(ctx):
    with shelve.open("config.conf", writeback=True) as conf:
        if len(ctx.message.role_mentions) == 1:
            conf[str(ctx.guild.id)]["default_role_id"] = ctx.message.role_mentions[0].id
            await ctx.send(f"Role ``{ctx.message.role_mentions[0].name}`` set to default role")
        elif len(ctx.message.role_mentions) == 0:
            conf[str(ctx.guild.id)]["default_role_id"] = ""
            await ctx.send("Default role disabled")
        else:
            await ctx.send("Too many roles !")


@bot.command()
@commands.guild_only()
async def default_role(ctx):
    with shelve.open("config.conf") as conf:
        await ctx.send(conf[str(ctx.guild.id)]["default_role_id"])


@bot.command()
@commands.guild_only()
async def reaction_message(ctx, state=None, message_id=None, reaction=None):
    if state not in ["set", "unset", "add", "remove"]:
        await ctx.send("Wrong argument !")
    else:
        try:
            message = await ctx.fetch_message(int(message_id))
        except (TypeError, ValueError, NotFound):
            await ctx.send("Invalid message ID !")
        else:
            with shelve.open("config.conf", writeback=True) as conf:
                if state == "set":
                    if message.id in conf[str(ctx.guild.id)]["reaction_messages"]:
                        await ctx.send("Message already set !")
                    else:
                        conf[str(ctx.guild.id)]["reaction_messages"][message.id] = dict()
                        await ctx.send("Message set")
                elif state == "unset":
                    try:
                        del conf[str(ctx.guild.id)]["reaction_messages"][message.id]
                    except KeyError:
                        await ctx.send("Message not set !")
                    else:
                        await ctx.send("Message remove")
                else:
                    if message.id not in conf[str(ctx.guild.id)]["reaction_messages"]:
                        await ctx.send("Message not set !")
                    else:
                        if state == "add":
                            if len(ctx.message.role_mentions) != 1:
                                await ctx.send("Invalid role !")
                            else:
                                try:
                                    await message.add_reaction(reaction)
                                except InvalidArgument:
                                    await ctx.send("Invalid reaction !")
                                else:
                                    conf[str(ctx.guild.id)]["reaction_messages"][message.id][reaction] =\
                                        ctx.message.role_mentions[0].id
                                    await ctx.send("Reaction add")
                        if state == "remove":
                            try:
                                await message.remove_reaction(reaction, bot.user)
                            except (InvalidArgument, NotFound):
                                await ctx.send("Invalid reaction !")
                            else:
                                del conf[str(ctx.guild.id)]["reaction_messages"][message.id][reaction]
                                await ctx.send("Reaction remove")


@bot.command()
async def debug(ctx, config=None):
    with shelve.open("config.conf") as conf:
        data = conf[str(ctx.guild.id)]
        if config:
            data = data[config]
        print(data)
        await ctx.send(f"``{data}``")

bot.run(open("token.ini").read())
