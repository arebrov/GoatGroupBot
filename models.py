import random
from enum import Enum, IntEnum


class CardKind(IntEnum):
    ACE = 9,
    KING = 8,
    QUEEN = 7,
    JACK = 6,
    TEN = 5,
    NINE = 4,
    EIGHT = 3,
    SEVEN = 2,
    SIX = 1


class CardSuit(IntEnum):
    NONE = 0,
    DIAMONDS = 1,
    HEARTS = 2,
    SPADES = 3,
    CLUBS = 4


class CardSuitString(Enum):
    DIAMONDS = '\U00002666',
    HEARTS = '\U00002665',
    SPADES = '\U00002660',
    CLUBS = '\U00002663'


SUIT_STRING_TO_SUIT = {str(CardSuitString.DIAMONDS): CardSuit.DIAMONDS, str(CardSuitString.HEARTS): CardSuit.HEARTS,
                       str(CardSuitString.SPADES): CardSuit.SPADES, str(CardSuitString.CLUBS): CardSuit.SPADES,
                       'без козыря': CardSuit.NONE, 'бескозырка': CardSuit.NONE}

START_GAME_MESSAGES = {'Погнали': True, 'Пас': False}


class StepResult(Enum):
    SUCCESS = 1,
    ERROR = 2,
    NEXT_CYCLE = 3,
    JACKPOT = 4,
    END = 5


class Card:
    _cardValues = {CardKind.ACE: 11, CardKind.KING: 4, CardKind.QUEEN: 3, CardKind.JACK: 2, CardKind.TEN: 10,
                   CardKind.NINE: 0, CardKind.EIGHT: 0, CardKind.SEVEN: 0, CardKind.SIX: 0}

    _cardKindStr = {CardKind.ACE: "Т", CardKind.KING: "К", CardKind.QUEEN: "Д", CardKind.JACK: "В",
                    CardKind.TEN: "10", CardKind.NINE: "9", CardKind.EIGHT: "8", CardKind.SEVEN: "7",
                    CardKind.SIX: "6"}
    _cardStrKind = {"Т": CardKind.ACE, "К": CardKind.KING, "Д": CardKind.QUEEN, "В": CardKind.JACK,
                    "10": CardKind.TEN, "9": CardKind.NINE, "8": CardKind.EIGHT, "7": CardKind.SEVEN,
                    "6": CardKind.SIX}
    _cardSuitStr = {CardSuit.DIAMONDS: "\U00002666", CardSuit.CLUBS: "\U00002663",
                    CardSuit.SPADES: "\U00002660", CardSuit.HEARTS: "\U00002665"}
    _cardStrSuit = {"\U00002666": CardSuit.DIAMONDS, "\U00002663": CardSuit.CLUBS,
                    "\U00002660": CardSuit.SPADES, "\U00002665": CardSuit.HEARTS}

    def __init__(self, kind: CardKind, suit: CardSuit):
        self.kind = kind
        self.suit = suit

    def is_trump(self, trump_suit: CardSuit):
        if trump_suit is CardSuit.NONE:
            return self.is_default_trump()
        return self.suit == trump_suit or self.is_default_trump()

    def get_value(self):
        return self._cardValues.get(self.kind)

    def equals(self, card) -> bool:
        if card.suit == self.suit and card.kind == self.kind:
            return True
        return False

    def is_default_trump(self) -> bool:
        if self.kind == CardKind.SIX and self.suit == CardSuit.CLUBS:
            return True
        return self.kind == CardKind.QUEEN or self.kind == CardKind.JACK

    def is_greater_by_kind(self, card):
        if self.kind == CardKind.SIX and self.suit == CardSuit.CLUBS:
            return True
        if card.kind == CardKind.SIX and card.suit == CardSuit.CLUBS:
            return False
        return self.get_value() > card.get_value()

    def greater_than(self, card, trump_suit: CardSuit) -> bool:
        if self.equals(card):
            return False
        if trump_suit is CardSuit.NONE:
            return self._greater_than_no_trump(card)
        if (self.is_default_trump() or self.suit == trump_suit) and \
                (card.is_default_trump() or card.suit == trump_suit):
            return self.is_greater_by_kind(card)
        if not self.is_default_trump() and self.suit != trump_suit and \
                not card.is_default_trump() and card.suit != trump_suit:
            return self.is_greater_by_kind(card)
        if (self.is_default_trump() or self.suit == trump_suit) and \
                not card.is_default_trump() and card.suit != trump_suit:
            return True
        if not self.is_default_trump() and self.suit != trump_suit and \
                (card.is_default_trump() or card.suit == trump_suit):
            return False
        return True

    def _greater_than_no_trump(self, card):
        if (self.is_default_trump() and card.is_default_trump()) or (
                not self.is_default_trump() and not card.is_default_trump()):
            return self.is_greater_by_kind(card)
        return self.is_default_trump() and not card.is_default_trump()

    def less_than(self, card, trump_suit: CardSuit) -> bool:
        if self.equals(card):
            return False
        return not self.greater_than(card, trump_suit)

    def to_string(self):
        return f"{self._cardKindStr.get(self.kind)}{self._cardSuitStr.get(self.suit)}"

    @staticmethod
    def try_parse(text: str) -> (bool, object):
        if len(text) > 3 or len(text) < 2:
            return False, None
        try:
            suit = Card._cardStrSuit.get(text[-1])
        finally:
            pass
        try:
            kind = Card._cardStrKind.get(text[0:-1].upper())
        finally:
            pass
        if kind is not None and suit is not None:
            return True, Card(kind, suit)
        return False, None


class Deck:
    COUNT = 32

    def __init__(self):
        self.cards = []
        self.currentIndex = 0
        self.lastIndex = self.COUNT - 1
        for i in range(1, 5):
            for j in range(1, 10):
                if j == 2:
                    continue
                self.cards.append(Card(CardKind(j), CardSuit(i)))

    def reset(self):
        self.currentIndex = 0

    def shuffle(self):
        random.shuffle(self.cards)

    def get_next(self, skip: bool = True):
        if self.currentIndex == self.COUNT:
            self.currentIndex = 0
        result = self.cards[self.currentIndex]
        if skip:
            self.currentIndex += 1
        return result

    def get_last(self, skip: bool = True):
        if self.lastIndex == 0:
            self.lastIndex = self.COUNT - 1
        result = self.cards[self.lastIndex]
        if skip:
            self.lastIndex -= 1
        return result

    def get_rest_cards(self) -> int:
        return self.lastIndex - self.currentIndex + 1


class GoatUser:
    def __init__(self, user_id: int, first_name: str, last_name: str, user_name: str):
        self.first_name = first_name
        self.last_name = last_name
        self.user_name = user_name
        self.id = user_id

    def get_full_name(self) -> str:
        if len(self.first_name) > 0 and len(self.last_name) > 0:
            return f'{self.first_name} {self.last_name}'
        elif len(self.first_name) > 0:
            return self.first_name
        return self.last_name