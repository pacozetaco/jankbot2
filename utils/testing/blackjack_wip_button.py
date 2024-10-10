import discord
from utils.cards import Deck, Hand

class WIPBlackJack:
    def __init__(self, ctx, bet, pitboss):
        self.ctx = ctx
        self.pitboss = pitboss
        self.bet = bet
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.game_ongoing = True
        self.game_instance = None

    def hand_value(self, hand):
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

    def initialize_game(self):
        self.pitboss.active_games[str(self.ctx.author)] = "BlackJack"
        for _ in range(2):
            self.player_hand.draw(self.deck)
            self.dealer_hand.draw(self.deck)
        player_score = self.hand_value(self.player_hand.hand)
        dealer_score = self.hand_value(self.dealer_hand.hand)
        if player_score == 21 or dealer_score == 21:
            self.game_instance = "BlackJack"
            self.game_ongoing = False

    async def players_turn(self):
        pass

    async def blackjack(self):
        self.initialize_game()
        if self.game_ongoing:
            await self.players_turn()
        if self.game_ongoing:
            self.dealers_turn()
        await self.end_game()


    @classmethod
    async def start_game(cls, ctx, bet: int, pitboss):
        instance = cls(ctx, bet, pitboss)
        await instance.blackjack()



