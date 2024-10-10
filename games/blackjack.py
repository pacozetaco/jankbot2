import utils.db as db, random, discord, os
from PIL import Image, ImageDraw, ImageFont

class BlackJack():
    def __init__(self, ctx, bet, pitboss):
        self.pitboss = pitboss
        self.ctx = ctx
        self.bet = bet
        self.player = str(ctx.author)
        self.emojis = []
        self.reaction_emoji = ""
        self.game_instance = None
        self.transaction_amount = 0
        self.balance = 0
        self.game_log = []
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.result = ""
        self.whos_turn = ""
        self.player_hand_value = 0
        self.dealer_hand_value = 0
        self.game_ongoing = True
        self.table_path = "./assets/tables/blackjack_table.png"
        self.font = ImageFont.truetype("./assets/font/pixel_font.ttf", 15)
        self.game_pic_path = f"./temp/{self.player}_blackjack_game.png"
        self.game_pic = None

    def create_dark_embed(self):
        embed = discord.Embed(title = self.game_content,color=0x00008B )
        return embed


    def draw_game(self):
        def paste_cards(hand, x):
            w = 32
            totalwidth = len(hand) * w
            start_x = (background.width - totalwidth) // 2
            i = 0
            for card in hand:
                background.paste(Image.open(f"./assets/cards/{card}.png"), (start_x + (i * w), x))
                i += 1

        background = Image.open(self.table_path)
        if self.whos_turn == "player":
            dealer_hand = [self.dealer_hand[0], "0_back"]
        else:
            dealer_hand = self.dealer_hand
        paste_cards(self.player_hand, 176)
        paste_cards(dealer_hand, 32)
        draw = ImageDraw.Draw(background)
        draw.multiline_text((23, 104), f"Jank: {self.dealer_hand_value}", font=self.font, fill=(0,0,0))
        draw.multiline_text((38, 136), f"You: {self.player_hand_value}", font=self.font, fill=(0, 0, 0))
        draw.multiline_text((176, 110), f"Bet", font=self.font, fill=(0, 0, 0))
        draw.multiline_text((176, 130), f"{self.bet}", font=self.font, fill=(0, 0, 0))
        background.save(self.game_pic_path, "PNG")
        self.game_pic = discord.File(self.game_pic_path)
        

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
            self.reaction_emoji = "timeout"
        await self.game_instance.clear_reactions()

    def calculate_hand_value(self):
        def hand_value(hand):
            card_values = {
                '0': 0, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
                'j': 10, 'q': 10, 'k': 10, 'a': 11
            }
            values = [card.split('_')[0] for card in hand]
            aces = values.count('a')
            score = sum(card_values[value] for value in values)
            while score > 21 and aces:
                score -= 10
                aces -= 1
            return score
        self.player_hand_value = hand_value(self.player_hand)
        if self.whos_turn == "player":
            hand = [self.dealer_hand[0], "0_fake"]
            self.dealer_hand_value = hand_value(hand)
        else:
            self.dealer_hand_value = hand_value(self.dealer_hand)

    async def initialize_game(self):
        self.pitboss.active_games[str(self.ctx.author)] = "BlackJack"
        self.game_instance = await self.ctx.reply("Shuffling deck...")
        self.balance = await db.get_balance(self.player)
        cards = ["2","3","4","5","6","7","8","9","10","j","q","k","a"]
        suits = ["spade", "heart", "diamond", "club"]
        for suit in suits:
            for card in cards:
                self.deck.append(f"{card}_{suit}")
        shuffles = random.randint(100, 300)
        for _ in range(shuffles):
            random.shuffle(self.deck)
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.calculate_hand_value()
        if self.player_hand_value == 21 or self.dealer_hand_value == 21:
            self.whos_turn = "blackjack"
            self.game_ongoing = False

    async def players_turn(self):
        while True:
            self.emojis = ["👇🏻","👋🏻"]
            self.game_content = f"Hit or Stand?"
            if self.whos_turn == "":
                if self.bet * 2 <= self.balance:
                    self.emojis.append("🤑")
                    self.game_content = f"Hit, Stand, or Double Down?"
            self.whos_turn = "player"
            self.calculate_hand_value()
            if self.player_hand_value == 21:
                break
            if self.player_hand_value > 21:
                self.game_ongoing = False
                break
            self.draw_game()
            embed = self.create_dark_embed()
            await self.game_instance.delete()
            self.game_instance = await self.ctx.reply(file = self.game_pic, embed = embed)
            await self.add_reaction()
            await self.wait_for_reaction()
            if self.reaction_emoji == "timeout":
                self.game_ongoing = False
                break
            if self.reaction_emoji == "👇🏻":
                self.player_hand.append(self.deck.pop())
            elif self.reaction_emoji == "👋🏻":
                break
            elif self.reaction_emoji == "🤑":
                self.bet = self.bet * 2
                self.player_hand.append(self.deck.pop())
                self.calculate_hand_value()
                if self.player_hand_value > 21:
                    self.game_ongoing = False
                break
        self.whos_turn = "dealer"

    def dealers_turn(self):
        while True:
            self.calculate_hand_value()
            if self.dealer_hand_value > 16:
                break
            self.dealer_hand.append(self.deck.pop())

    def who_won(self):
        self.calculate_hand_value()
        if self.reaction_emoji == "timeout":
            self.result = "lost"
            return
        if self.player_hand_value > 21:
            self.result = "lost"
            return
        if self.dealer_hand_value > 21:
            self.result = "won"
            return
        if self.player_hand_value > self.dealer_hand_value:
            self.result = "won"
            return
        if self.player_hand_value < self.dealer_hand_value:
            self.result = "lost"
            return
        if self.player_hand_value == self.dealer_hand_value:
            self.result = "pushed"
            return
        
    def transaction_logic(self):
        if self.whos_turn == "blackjack":
            if self.result == "won":
                self.transaction_amount = self.bet * 1.5
            else:
                self.transaction_amount = -self.bet
            return
        if self.result == "won":
            self.transaction_amount = self.bet
        if self.result == "lost":
            self.transaction_amount = -self.bet
        if self.result == "tied":
            self.transaction_amount = 0

    async def end_game(self):
        await db.set_balance(self.player, self.transaction_amount)
        await db.log_bj(self)
        self.balance = await db.get_balance(self.player)
        self.game_content = f"You {self.result}! Bet: {self.bet} Balance: {self.balance}"
        if self.bet <= self.balance:
            self.game_content += f"\nClick the MoneyBag to play again."
        await self.game_instance.delete()
        embed = self.create_dark_embed()
        self.draw_game()
        self.game_instance = await self.ctx.reply(file = self.game_pic, embed = embed)
        self.pitboss.active_games.pop(str(self.ctx.author))
        if self.bet <= self.balance:
            self.emojis = "💰"
            await self.add_reaction()
            await self.wait_for_reaction()
            if self.reaction_emoji == "💰":
                await self.start_game(self.ctx, self.bet, self.pitboss)
        os.remove(self.game_pic_path)


    async def blackjack(self):
        await self.initialize_game()
        if self.game_ongoing == True:
            await self.players_turn()
        if self.game_ongoing == True:
            self.dealers_turn()
        self.who_won()
        self.transaction_logic()
        await self.end_game()


    @classmethod
    async def start_game(cls, ctx, bet: int, pitboss):
        instance = cls(ctx, bet, pitboss)
        await instance.blackjack()
    



