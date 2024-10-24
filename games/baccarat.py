from utils.cards import Deck, Hand
import discord, asyncio
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
        self.deck = Deck(1)
        self.game_history = []
        self.bets = []
        self.game_instance = None
        self.bet_instance = None
        self.player_hand = None
        self.dealer_hand = None

    async def initialize_game(self):
        self.game_ongoing = True
        await self.baccarat_manager.channel.purge()
        game_view = BacView(["Player", "Tie", "Banker", "No Bet"], self)
        bet_view = BacView(["20", "40", "60", "80", "100", "200", "300", "500", "1000", "2000"],self)
        #draw gameboard and history
        self.game_instance = await self.baccarat_manager.channel.send(view=game_view, content="TESTING")
        embed = discord.Embed(title="Denomination")
        self.bet_instance = await self.baccarat_manager.channel.send(view=bet_view, embed=embed)
    
    async def update_bets(self):
        pass
        
    async def update_gameboard(self):
        for bet in self.bets:
            if bet[0] == "Player":
                pass
                #add bet to player side
            elif bet[0] == "Banker":
                pass
                #add bet to banker side
            else:
                pass
                #add to tie side
            #update gameboard with bets

    async def start_hand(self):
        await self.bet_instance.delete()
        await self.game_instance.edit(view = None)
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        print("we started this bish")
        self.player_hand.draw(self.deck)
        self.player_hand.draw(self.deck)
        self.dealer_hand.draw(self.deck)
        self.dealer_hand.draw(self.deck)
        print(len(self.deck.deck))
        self.bets = []
        await self.shoe_loop()


    async def shoe_loop(self):
        self.player_hand = None
        self.dealer_hand = None
        cut_spot = 40
        if len(self.deck.deck) > cut_spot:
            await self.initialize_game()
        else: await self.baccarat_manager.game_loop()
        #play the game
        

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
        self.new_bet = False

        for button_label in buttons:
            style = {
                "Player": discord.ButtonStyle.blurple,
                "Banker": discord.ButtonStyle.red,
                "Tie": discord.ButtonStyle.green
            }.get(button_label, discord.ButtonStyle.grey)

            button = discord.ui.Button(label=button_label, custom_id=button_label, style=style)
            button.callback = self.button_callback
            self.add_item(button)

    async def start_timer(self):
        i = 0
        while i < 3:
            if not self.shoe.bets:
                self.new_bet = False
                print("no bets!!!!!")
                return
            i += 1
            print("going to sleep")
            await asyncio.sleep(1)
        await self.shoe.start_hand()


    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        player = interaction.user.name
        try:
            balance = await db.get_balance(player)
        except:
            balance = 0
        bet = await db.get_denomination(player)
        if custom_id in ("Player", "Banker", "Tie") and balance >= bet:
            players_in_bets = [sublist[1] for sublist in self.shoe.bets]
            if player not in players_in_bets:
                self.shoe.bets.append([custom_id, player, bet])
                await interaction.response.send_message(content=f"Bet:{bet} - {custom_id}", ephemeral=True, delete_after=5)
                await self.shoe.update_bets()
                if not self.new_bet:
                    self.new_bet = True
                    print("bet set to true")
                    await self.start_timer()
            else:
                await interaction.response.send_message(content="You already have a bet!", ephemeral=True, delete_after=5)
        elif custom_id == "No Bet":
            players_in_bets = [sublist[1] for sublist in self.shoe.bets]
            if player in players_in_bets:
                for i, sublist in enumerate(self.shoe.bets):
                    if sublist[1] == player:
                        removed_bet = self.shoe.bets.pop(i)
                        await interaction.response.send_message(content=f"Removed bet of {removed_bet[2]} for {removed_bet[1]}", ephemeral=True, delete_after=5)
                        await self.shoe.update_bets()
                        break
            else:
                await interaction.response.send_message(content="You don't have a bet to remove!", ephemeral=True, delete_after=5)

        elif custom_id.isdigit() and balance >= int(custom_id):
            await db.set_denomination(player, custom_id)
            await interaction.response.send_message(content=f"Bet set to {custom_id}", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(f"You do not have enough money. Balance:{balance} - Bet:{bet}", ephemeral=True, delete_after=10)

