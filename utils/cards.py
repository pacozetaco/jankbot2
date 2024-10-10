import random
class Deck:
    def __init__(self):
        self.deck = []
        cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "j", "q", "k", "a"]
        suits = ["spade", "heart", "diamond", "club"]
        for suit in suits:
            for card in cards:
                self.deck.append(f"{card}_{suit}")
        shuffles = random.randint(200, 500)
        for _ in range(shuffles):
            random.shuffle(self.deck)

class Hand:
    def __init__(self):
        self.hand = []

    def draw(self, deck):
        card = deck.deck.pop()
        self.hand.append(card)