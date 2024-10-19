import utils.db as db
import random

class DeathRoll():
    def __init__(self, ctx, bet, pitboss):
        self.pitboss = pitboss
        self.ctx = ctx
        self.bet = bet
        self.emojis = []
        self.reaction_emoji = ""
        self.player = str(ctx.author)
        self.whos_first = ""
        self.whos_turn = ""
        self.balance = 0
        self.transaction_amount = 0
        self.game_instance = None
        self.game_content = ""
        self.result = ""
        self.roll = 100

    def timeout(self):
        self.result = "lost"
        self.game_content += f"\nTime's up!, you lost {self.bet} coins. Balance: {self.balance - self.bet}"
        self.transaction_amount = -self.bet
        print(f"**DEBUG**: Timed out, result is '{self.result}' and balance is {self.balance - self.bet}", flush=True)

    def closing_logic(self):
        if self.whos_turn == "Jankbot":
            self.result = "won"
            self.game_content += f"\nYou won {self.bet} coins. Balance: {self.balance + self.bet}"
            print(f"**DEBUG**: Won, result is '{self.result}' and balance is {self.balance + self.bet}", flush=True)
        if self.whos_turn == "Player":
            self.result = "lost"
            self.game_content += f"\nYou lost {self.bet} coins. Balance: {self.balance - self.bet}"
            print(f"**DEBUG**: Lost, result is '{self.result}' and balance is {self.balance - self.bet}", flush=True)
        if self.result == "won":
            self.transaction_amount = self.bet
        else:
            self.transaction_amount = -self.bet

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
            self.whos_first = "timeout"
            print(f"**DEBUG**: Timed out while waiting for reaction", flush=True)
        await self.game_instance.clear_reactions()

    async def initialize_game(self):
        self.pitboss.active_games[self.player] = "DeathRoll"
        self.balance = await db.get_balance(self.player)
        self.game_content = f"Deathroll! Bet: {self.bet}\nWho goes first? (/roll 1-100)"
        print(f"**DEBUG**: Initializing game with bet {self.bet} and balance {self.balance}", flush=True)
        self.game_instance = await self.ctx.send(self.game_content)
        self.emojis = ["🤖", "🧑🏻"]
        await self.add_reaction()
        await self.wait_for_reaction()
        if self.whos_first == "timeout":
            print(f"**DEBUG**: Timed out while waiting for first move", flush=True)
            return
        if self.reaction_emoji == "🤖":
            self.whos_first = "Jankbot"
            self.whos_turn = "Jankbot"
            self.game_content += f"\nJankbot goes first"
        else:
            self.whos_first = "Player"
            self.whos_turn = "Player"
            self.game_content += f"\nYou go first"
        print(f"**DEBUG**: Whose turn is {self.whos_first} and balance is {self.balance}", flush=True)
        await self.game_instance.edit(content=self.game_content)

    async def game_loop(self):
        if self.whos_first == "timeout":
            self.timeout()
            return  
        while True:
            if self.whos_turn == "Jankbot":
                self.roll = random.randint(1, self.roll)
                self.game_content += f"\nJankbot rolled {self.roll}"
                print(f"**DEBUG**: Jankbot rolled {self.roll}", flush=True)
            if self.whos_turn == "Player":
                self.emojis = ["🎲"]
                await self.add_reaction()
                await self.wait_for_reaction()
                if self.whos_first == "timeout":
                    self.timeout()
                    break
                self.roll = random.randint(1, self.roll)
                self.game_content += f"\nYou rolled {self.roll}"
                print(f"**DEBUG**: Rolled {self.roll}", flush=True)
            if self.roll == 1:
                self.closing_logic()
                break
            await self.game_instance.edit(content=self.game_content)
            if self.whos_turn == "Jankbot":
                self.whos_turn = "Player"
            else:
                self.whos_turn = "Jankbot"

    async def end_game(self):
        print(f"**DEBUG**: Ending game", flush=True)
        await self.game_instance.edit(content=self.game_content)
        await db.set_balance(self.player, self.transaction_amount)
        await db.log_deathroll(self)
        self.pitboss.active_games.pop(self.player)
        # if self.bet < self.balance:
        #     self.game_content += f"\nClick the MoneyBag to play again."
        #     await self.game_instance.edit(content = self.game_content)
        #     self.emojis = "💰"
        #     await self.add_reaction()
        #     await self.wait_for_reaction()
        #     if self.reaction_emoji == "💰":
        #         await self.start_game(self.ctx, self.bet, self.pitboss)

    async def deathroll(self):
        print(f"**DEBUG**: Starting deathroll with bet {self.bet}", flush=True)
        await self.initialize_game()
        await self.game_loop()
        await self.end_game()

    @classmethod
    async def start_game(cls, ctx, bet: int, pitboss):
        instance = cls(ctx, bet, pitboss)
        print(f"**DEBUG**: Starting game with bet {bet}", flush=True)
        await instance.deathroll()