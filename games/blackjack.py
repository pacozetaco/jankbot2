import discord, os, asyncio
from utils.cards import Deck, Hand
import utils.db as db
from PIL import Image, ImageDraw, ImageFont

print("Importing modules...", flush=True)

class BlackJack:
    def __init__(self, ctx, bet, pitboss):
        print(f"Initializing game with player {ctx.author.name}...", flush=True)
        self.ctx = ctx
        self.pitboss = pitboss
        self.bet = bet
        self.deck = Deck(1)
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.whos_turn = ""
        self.game_ongoing = True
        self.game_instance = None
        self.game_pic = None
        self.player = str(ctx.author)
        self.result = ""
        self.game_pic_path = f"./temp/{self.player}_blackjack_game.png"
        self.waiting_for_react = False
        self.selected_button = ""

    def draw_game(self):
        print("Drawing game...", flush=True)
        font = ImageFont.truetype("./assets/font/pixel_font.ttf", 15)
        table_path = "./assets/tables/blackjack_table.png"
        def paste_cards(hand, x):
            w = 32
            totalwidth = len(hand) * w
            start_x = (background.width - totalwidth) // 2
            i = 0
            for card in hand:
                background.paste(Image.open(f"./assets/cards/{card}.png"), (start_x + (i * w), x))
                i += 1
        background = Image.open(table_path)
        if self.whos_turn == "player":
            dealer_hand = [self.dealer_hand.hand[0], "0_back"]
        else:
            dealer_hand = self.dealer_hand.hand
        dealer_hand_value = self.hand_value(dealer_hand)
        player_hand_value = self.hand_value(self.player_hand.hand)
        paste_cards(self.player_hand.hand, 176)
        paste_cards(dealer_hand, 32)
        draw = ImageDraw.Draw(background)
        draw.multiline_text((23, 104), f"Jank: {dealer_hand_value}", font=font, fill=(0,0,0))
        draw.multiline_text((38, 136), f"You: {player_hand_value}", font=font, fill=(0, 0, 0))
        draw.multiline_text((176, 110), f"Bet", font=font, fill=(0, 0, 0))
        draw.multiline_text((176, 130), f"{self.bet}", font=font, fill=(0, 0, 0))
        background.save(self.game_pic_path, "PNG")
        self.game_pic = discord.File(self.game_pic_path)

    def hand_value(self, hand):
        print("Calculating hand value...", flush=True)
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

    async def initialize_game(self):
        print("Initializing game...", flush=True)
        self.pitboss.active_games[self.player] = "BlackJack"
        for _ in range(2):
            self.player_hand.draw(self.deck)
            self.dealer_hand.draw(self.deck)
        player_score = self.hand_value(self.player_hand.hand)
        dealer_score = self.hand_value(self.dealer_hand.hand)
        if player_score == 21 or dealer_score == 21:
            self.whos_turn = "BlackJack"
            self.game_ongoing = False
        self.game_instance = await self.ctx.reply("Shuffling deck...")
        print(f"Game initialized with player {self.player}...", flush=True)

    async def players_turn(self):
        while self.game_ongoing:
            self.selected_button = ""
            buttons = ["Hit", "Stand"]
            balance = await db.get_balance(self.player)
            if self.whos_turn == "" and balance >= self.bet*2:
                buttons.append("Double Down")
            self.whos_turn = "player"
            hand_value = self.hand_value(self.player_hand.hand)
            if hand_value == 21:
                break
            if hand_value > 21:
                self.game_ongoing = False
                break
            view = BlackjackView(buttons, self)
            self.draw_game()
            await self.game_instance.delete()
            self.game_instance = await self.ctx.reply(file = self.game_pic, view = view)
            self.waiting_for_react = True
            i = 1
            while self.waiting_for_react:
                i += 1
                await asyncio.sleep(1)
                print(f"Waiting for player to react...", flush=True)
                if i == 30:
                    self.waiting_for_react = False
                    view.stop()
            button_pressed = self.selected_button
            if button_pressed == "Hit":
                self.player_hand.draw(self.deck)
            elif button_pressed == "Stand":
                break
            elif button_pressed == "Double Down":
                self.player_hand.draw(self.deck)
                self.bet = self.bet * 2
                handvalue = self.hand_value(self.player_hand.hand)
                if handvalue > 21:
                    self.game_ongoing = False
                break
            else:
                await self.game_instance.edit(view = None)
                self.game_ongoing = False
                self.whos_turn = "Timeout"
                print(f"Game ended due to timeout...", flush=True)
    
    def dealers_turn(self):
        while True:
            hand_value = self.hand_value(self.dealer_hand.hand)
            if hand_value >= 17:
                break
            self.dealer_hand.draw(self.deck)
            print(f"Dealer drew a card...", flush=True)

    def who_won(self):
        player_score = self.hand_value(self.player_hand.hand)
        dealer_score = self.hand_value(self.dealer_hand.hand)
        if self.whos_turn == "Timeout" or player_score > 21:
            self.result = "lost"
            return
        if dealer_score > 21:
            self.result = "won"
            return
        if player_score > dealer_score:
            self.result = "won"
            return
        elif player_score < dealer_score:
            self.result = "lost"
            return
        else:
            self.result = "pushed"
            return
    
    async def transaction_logic(self):
        print("Processing transactions...", flush=True)
        if self.whos_turn == "BlackJack":
            if self.result == "won":
                await db.set_balance(self.player, self.bet*1.5)
            elif self.result == "lost":
                await db.set_balance(self.player, -self.bet)
            return
        if self.result == "won":
            await db.set_balance(self.player, self.bet)
        elif self.result == "lost":
            await db.set_balance(self.player, -self.bet)

    async def end_game(self):
        print("Ending game...", flush=True)
        self.whos_turn = ""
        self.pitboss.active_games.pop(self.player)
        await db.log_bj(self)
        balance = await db.get_balance(self.player)
        content = f"You {self.result}. | Balance: {balance}"
        embed = discord.Embed(title = content,color=0x00008B)
        await self.game_instance.delete()
        self.draw_game()
        if self.bet <= balance:
            view = BlackjackView(["Play Again",], self)
        else:
            view = None
        self.game_instance = await self.ctx.reply(file=self.game_pic,embed=embed, view=view)
        if view != None:
            self.waiting_for_react = True
            i = 1
            while self.waiting_for_react:
                await asyncio.sleep(1)
                i += 1
                if i == 30:
                    self.waiting_for_react = False
            if self.selected_button == "Play Again":
                await self.game_instance.edit(view = None)
                await self.start_game(self.ctx, self.bet, self.pitboss)
        try:
            os.remove(self.game_pic_path)
        except:
            pass
        if view is not None:
            view.stop()
        await self.game_instance.edit(view = None)

    async def blackjack(self):
        await self.initialize_game()
        if self.game_ongoing:
            await self.players_turn()
        if self.game_ongoing:
            self.dealers_turn()
        self.who_won()
        await self.transaction_logic()
        await self.end_game()

    @classmethod
    async def start_game(cls, ctx, bet: int, pitboss):
        instance = cls(ctx, bet, pitboss)
        print(f"Starting game for player {ctx.author.name}...", flush=True)
        await instance.blackjack()

class BlackjackView(discord.ui.View):
    def __init__(self, buttons, bjgame):
        super().__init__()
        self.bjgame = bjgame

        for button_label in buttons:
            if button_label == "Play Again" or button_label == "Double Down":
                style = discord.ButtonStyle.green
                style = discord.ButtonStyle.blurple
                print(f"Button {button_label} created with style {style.value}", flush=True)
            elif button_label == "Stand":
                style = discord.ButtonStyle.red
                print(f"Button {button_label} created with style {style.value}", flush=True)
            else:
                style = discord.ButtonStyle.gray  # Default style for safety
                print(f"Button {button_label} created with style {style.value}", flush=True)

            # Create the button
            button = discord.ui.Button(label=button_label, style=style)

            # Set the callback for each button dynamically based on its label
            if button_label == "Hit":
                print("Setting Hit button callback...", flush=True)
                button.callback = self.hit_button_callback
            elif button_label == "Stand":
                print("Setting Stand button callback...", flush=True)
                button.callback = self.stand_button_callback
            elif button_label == "Double Down":
                print("Setting Double Down button callback...", flush=True)
                button.callback = self.double_down_button_callback
            elif button_label == "Play Again":
                print("Setting Play Again button callback...", flush=True)
                button.callback = self.play_again_button_callback
            # Add button to the view
            print(f"Adding button {button_label} to the view", flush=True)
            self.add_item(button)

    # Callback for the "Hit" button
    async def hit_button_callback(self, interaction: discord.Interaction):
        if interaction.user != self.bjgame.ctx.author:
            return
        print("Hit button pressed...", flush=True)
        self.bjgame.selected_button = "Hit"
        self.bjgame.waiting_for_react = False
        await interaction.response.defer()
        self.stop()

    # Callback for the "Stand" button
    async def stand_button_callback(self, interaction: discord.Interaction):
        if interaction.user != self.bjgame.ctx.author:
            return
        print("Stand button pressed...", flush=True)
        self.bjgame.selected_button = "Stand"
        self.bjgame.waiting_for_react = False
        await interaction.response.defer()
        self.stop()

    # Callback for the "Double Down" button
    async def double_down_button_callback(self, interaction: discord.Interaction):
        if interaction.user != self.bjgame.ctx.author:
            return
        print("Double Down button pressed...", flush=True)
        self.bjgame.selected_button = "Double Down"
        self.bjgame.waiting_for_react = False
        await interaction.response.defer()
        self.stop()

    # Callback for the "Play Again" button
    async def play_again_button_callback(self, interaction: discord.Interaction):
        if interaction.user != self.bjgame.ctx.author:
            return
        print("Play Again button pressed...", flush=True)
        self.bjgame.selected_button = "Play Again"
        self.bjgame.waiting_for_react = False
        await interaction.response.defer()
        self.stop()
