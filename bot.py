import discord


class Bot(discord.Client):
    async def on_ready(self):
        print("FurrMula Bot online !")


bot = Bot()
bot.run(open("token.ini").read())
