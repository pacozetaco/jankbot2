from discord.ext import commands
import utils.db as db, config, games

def casino_channel_only(func):
    async def wrapper(self, *args, **kwargs):
        if args[0].channel.name != config.MAIN_CASINO_CHANNEL:
            return
        return await func(self, *args, **kwargs)
    return wrapper

def can_play(func):
    async def wrapper(self, ctx, bet):
        player = str(ctx.author)
        if not bet.isdigit() or int(bet) <= 0:
            await ctx.send("Check your syntax. ex. `!hilo 20`")
            return
        if player in self.active_games:
            await ctx.send(f"You're already playing {self.active_games[player]}.")
            return
        balance = await db.get_balance(player)
        if balance == None:
            await ctx.send(f"No balance found for {player}.\nGet your first coins with command `!daily`.")
            return
        if balance < int(bet):
            await ctx.send(f"You don't have enough coins. Balance: {balance}")
            return
        return await func(self, ctx, int(bet))
    return wrapper

class PitBoss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @commands.command(name="hilo")
    @casino_channel_only
    @can_play
    async def hilo(self, ctx, bet: int):
        await games.HiLo.start_game(ctx, bet, self)

    @commands.command(name="dr")
    @casino_channel_only
    @can_play
    async def dr(self, ctx, bet: int):
        await games.DeathRoll.start_game(ctx, bet, self)

    @commands.command(name="bj")
    @casino_channel_only
    @can_play
    async def bj(self, ctx, bet: int):
        if not bet %2 == 0:
            await ctx.send("BlackJack bets must be even to play.")
            return
        await games.BlackJack.start_game(ctx, bet, self)

    @commands.command(name="daily")
    @casino_channel_only
    async def daily(self, ctx):
        reply = await (db.daily_coins(ctx))
        await ctx.send(reply)

    @commands.command(name="stats")
    @casino_channel_only
    async def stats(self, ctx):
        reply = await (db.win_loss(ctx))
        await ctx.send(reply)

    @commands.command(name="balance")
    @casino_channel_only
    async def balance(self, ctx):
        balance = await (db.get_balance(str(ctx.author)))
        await ctx.send(f"Your Balance: {balance}")

async def setup(bot):
    await bot.add_cog(PitBoss(bot))
