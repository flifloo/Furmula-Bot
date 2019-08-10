import shelve
from discord.ext import commands

bot = commands.Bot(command_prefix="%")


def set_config(guild, conf):
    print(f"Set config for {guild.name}")
    conf[str(guild.id)] = dict()
    for opt in ["default_role_id"]:
        conf[str(guild.id)][opt] = ""


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
    print(1)
    with shelve.open("config.conf") as conf:
        print(2)
        print(conf[str(member.guild.id)]["default_role_id"])
        if "default_role_id" in conf[str(member.guild.id)] and conf[str(member.guild.id)]["default_role_id"]:
            print(3)
            role = member.guild.get_role(conf[str(member.guild.id)]["default_role_id"])
            print(4)
            await member.add_roles(role)
            print(5)


@bot.command()
async def shutdown(ctx):
    await ctx.send("Shutdown !")
    await bot.logout()
    await bot.close()


@bot.command()
async def set_default_role(ctx):
    with shelve.open("config.conf", writeback=True) as conf:
        if len(ctx.message.role_mentions) == 1:
            conf[str(ctx.guild.id)]["default_role_id"] = ctx.message.role_mentions[0].id
            await ctx.send(f"Role {ctx.message.role_mentions[0].name} set to default role")
        elif len(ctx.message.role_mentions) == 0:
            conf[str(ctx.guild.id)]["default_role_id"] = ""
            await ctx.send("Default role disabled")
        else:
            await ctx.send("Too many roles !")


@bot.command()
async def default_role(ctx):
    with shelve.open("config.conf") as conf:
        await ctx.send(conf[str(ctx.guild.id)]["default_role_id"])


bot.run(open("token.ini").read())
