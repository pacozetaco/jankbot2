import utils.db as db, random, cogs.pitboss as Pitboss

class HiLo:
    def __init__(self, ctx, bet: int, pitboss):
        self.pitboss = pitboss
        self.ctx = ctx
        self.bet = bet
        self.game_content = ""
        self.choice = ""
        self.resut = ""
        self.roll = 0
        self.player = str(ctx.author)
        self.emojis = []
        self.reaction_emoji = ""
        self.game_instance = None
        self.transaction_amount = 0
        self.balance = 0

    async def add_reaction(self):
        for emoji in self.emojis:
            await self.game_instance.add_reaction(emoji)

    async def wait_for_reaction(self):
        def check_reaction(reaction, user):
            return user == self.ctx.author and str(reaction.emoji) in self.emojis and reaction.message.id == self.game_instance.id
        try:
            reaction, user = await self.ctx.bot.wait_for('reaction_add', timeout=30.0, check=check_reaction)
            self.reaction_emoji = str(reaction.emoji)
        except:
            self.choice = "timeout"
        await self.game_instance.clear_reactions()

    async def initialize_game(self):
        self.pitboss.active_games[self.player] = "HiLo"
        self.balance = await db.get_balance(self.player)
        self.game_content = f"HiLo! Bet: {self.bet}\nIs your roll higher or lower than 50? (/roll 1-100)"
        self.emojis = ["🔼", "🔽"]
        self.game_instance = await self.ctx.send(self.game_content)
        await self.add_reaction()

    def game_logic(self):
        if self.choice == "timeout":
            self.result = "lost"
            self.transaction_amount = -self.bet
            self.game_content += f"\nTime's up!, you lost {self.bet} coins. Balance: {self.balance - self.bet}"
            return
        self.choice = "high" if self.reaction_emoji == "🔼" else "low"
        self.roll = random.randint(1, 100)
        self.result = "tie" if self.roll == 50 else "won" if (self.choice == "high" and self.roll > 50) or (self.choice == "low" and self.roll < 50) else "lost"
        self.transaction_amount = -self.bet if self.result == "lost" else self.bet if self.result == "won" else 0
        self.balance += self.transaction_amount
        self.game_content += f"\nYou chose: {self.choice}\nThe dice rolled: {self.roll}\nYou {self.result} {self.bet} coins. Balance: {self.balance}"

    async def end_game(self):
        await self.game_instance.edit(content = self.game_content)
        await db.set_balance(self.player, self.transaction_amount)
        await db.log_hilo(self)
        self.pitboss.active_games.pop(self.player)
        # if self.bet < self.balance:
        #     self.game_content += f"\nClick the MoneyBag to play again."
        #     await self.game_instance.edit(content = self.game_content)
        #     self.emojis = "💰"
        #     await self.add_reaction()
        #     await self.wait_for_reaction()
        #     if self.reaction_emoji == "💰":
        #         await self.start_game(self.ctx, self.bet, self.pitboss)

    async def hilo(self):
        await self.initialize_game()
        await self.wait_for_reaction()
        self.game_logic()
        await self.end_game()

        
    @classmethod
    async def start_game(cls, ctx, bet: int, pitboss):
        instance = cls(ctx, bet, pitboss)
        await instance.hilo()