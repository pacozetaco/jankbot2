from utils.cards import Deck, Hand
import discord
import utils.db as db
import random

class BaccaratManager:
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel

    async def game_loop(self):
        #while True:
        await Shoe.start_shoe(self)

    @classmethod
    async def start_manager(cls, bot, channel):
        #print("Starting Baccarat instance...", flush=True)
        instance = cls(bot, channel)
        await instance.game_loop()

class Shoe:
    def __init__(self, baccarat_manager):
        self.baccarat_manager = baccarat_manager
        self.deck = Deck(8)
        self.game_history = []
        self.bets = []
        self.game_instance = None
        self.bet_instance = None
        self.player_hand = Hand()
        self.dealer_hand = Hand()

    async def initialize_game(self):
        await self.baccarat_manager.channel.purge()
        game_view = BacView(["Player", "Tie", "Banker"], self)
        bet_view = BacView(["20", "40", "60", "80", "100", "120", "140", "160", "180", "200"],self)
        #draw gameboard and history
        self.game_instance = await self.baccarat_manager.channel.send(view=game_view, content="test")
        self.bet_instance = await self.baccarat_manager.channel.send(view=bet_view, content="test")


    async def shoe_loop(self):
        cut_spot = random.randint(30, 100)
        #while len(self.deck.deck) > cut_spot:
        await self.initialize_game()

            #initialize game in discord with views gameboard betting area
            #wait for bets
            #play game
            #check winners
            #return results and clear bets
            #loop through same shoe until cut point
        


    @classmethod
    async def start_shoe(cls, baccarat_manager):
        #print("Starting new shoe", flush=True)
        instance = cls(baccarat_manager)
        await instance.shoe_loop()


class BacView(discord.ui.View):
    def __init__(self, buttons, shoe):
        super().__init__(timeout=None)
        self.buttons = buttons
        self.shoe = shoe

        for button_label in buttons:
            style = {
                "Player": discord.ButtonStyle.blurple,
                "Banker": discord.ButtonStyle.red,
                "Tie": discord.ButtonStyle.green
            }.get(button_label, discord.ButtonStyle.grey)

            button = discord.ui.Button(label=button_label, custom_id=button_label, style=style)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        player = interaction.user.name
        try:
            balance = await db.get_balance(player)
        except:
            balance = 0
        bet = await db.get_denomination(player)
        if custom_id in ("Player", "Banker", "Tie") and balance >= bet:
            self.shoe.bets.append([custom_id, player, bet])
            await interaction.response.send_message(content=f"Bet:{bet} - {custom_id}", ephemeral=True, delete_after=5)
        elif custom_id.isdigit() and balance >= int(custom_id):
            await db.set_denomination(player, custom_id)
            await interaction.response.send_message(content=f"Bet set to {custom_id}", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(f"You do not have enough money. Balance:{balance} - Bet:{bet}", ephemeral=True, delete_after=10)
