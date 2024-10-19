import random
class Deck:
    def __init__(self, num_of_decks):
        self.deck = []
        print("Creating new deck...", flush=True)
        cards = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "j", "q", "k", "a"]
        suits = ["spade", "heart", "diamond", "club"]
        i = 1
        while(i < num_of_decks):
            for suit in suits:
                for card in cards:
                    self.deck.append(f"{card}_{suit}")
            i += 1
        print("Deck created with {} cards...".format(len(self.deck)), flush=True)
        shuffles = random.randint(200, 500)
        print("Shuffling deck {} times...".format(shuffles), flush=True)
        for _ in range(shuffles):
            random.shuffle(self.deck)
        print("Deck shuffled!", flush=True)

class Hand:
    def __init__(self):
        self.hand = []
        print("Creating new hand...", flush=True)

    def draw(self, deck):
        card = deck.deck.pop()
        self.hand.append(card)
        print("Drew card: {}".format(card), flush=True)