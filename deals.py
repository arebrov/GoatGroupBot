from enum import Enum
from itertools import permutations
from models import Card, CardSuit, Deck, CardKind, StepResult
import logging


class DealType(Enum):
    CLASSIC = 1,
    PANTS = 2


class Deal:
    request_trump_handler = None
    request_send_current_cards_to_pm_handler = None
    request_show_bribe_handler = None
    request_ask_for_deal_handler = None
    request_ask_for_step_handler = None
    request_show_jackpot_handler = None

    def __init__(self, owner_index: int):
        logging.debug(f'Deal construct owner_index: {owner_index}')
        self.is_started = False
        self.deck = Deck()
        self.deck.shuffle()
        self.cards_history = []
        self.owner_index = owner_index
        self.player1_cards = []
        self.player2_cards = []
        self.player3_cards = []
        self.player4_cards = []
        self.player_index = owner_index
        self.team1_cards = []
        self.team2_cards = []
        self.cards = []
        self.trump = None

    def get_deal_type(self) -> DealType:
        raise NotImplementedError()

    def get_player_cards(self, player_index: int) -> list:
        logging.debug(f'Deal.get_player_cards({player_index}) called')
        cards = {0: self.player1_cards, 1: self.player2_cards, 2: self.player3_cards, 3: self.player4_cards}
        return cards.get(player_index)

    def _remove_player_card(self, player_index: int, card: Card):
        logging.debug(f'Deal._remove_player_card({player_index}, {card.to_string()}) called')
        player_cards = self.get_player_cards(player_index)
        index = -1
        for i in range(0, len(player_cards)):
            if card.equals(player_cards[i]):
                index = i
                break
        player_cards.remove(player_cards[index])

    @staticmethod
    def _get_team_index_by_player_index(player_index: int) -> int:
        logging.debug(f'Deal._get_team_index_by_player_index({player_index}) called')
        if player_index == 0 or player_index == 2:
            return 0
        else:
            return 1

    def _get_team_taken_cards(self, team_index: int) -> list[Card]:
        logging.debug(f'Deal._get_team_taken_cards({team_index}) called')
        if team_index == 0:
            return self.team1_cards
        else:
            return self.team2_cards

    @staticmethod
    def _calc_score(cards: list) -> int:
        logging.debug(f'Deal._calc_score({" ".join([x.to_string() for x in cards])}) called')
        total_score = 0
        for card in cards:
            total_score += card['card'].get_value()
        logging.debug(f'Deal._calc_score result {total_score}')
        return total_score

    def get_team_score(self, team_index: int) -> int:
        logging.debug(f'Deal.get_team_score({team_index}) called')
        return self._calc_score(self._get_team_taken_cards(team_index))

    def _process_jackpot(self):
        logging.debug('Deal._process_jackpot called')
        self.request_show_jackpot_handler(self._get_jackpot_winner(), self._get_jackpot_looser())
        self.cards_history.append(self.cards.copy())
        self.cards.clear()

    def _process_bribe(self) -> int:
        logging.debug('Deal._process_bribe called')
        current_owner = 0
        card = None
        for i in range(0, 4):
            if card is None:
                card = self.cards[i]
                current_owner = self.cards[i]['owner']
            else:
                if card['card'].greaterThan(self.cards[i]['card'], self.trump):
                    current_owner = self.cards[i]['owner']
                card = self.cards[i]
        logging.debug(f'Deal._process_bribe owner: {current_owner} card: {card.to_string()}')
        self._get_team_taken_cards(self._get_team_index_by_player_index(current_owner)).extend(self.cards)
        self.cards_history.append(self.cards.copy())
        self.cards.clear()
        return current_owner

    def _get_new_turn_player(self, previous_taken: int) -> int:
        raise NotImplementedError()

    def is_completed(self):
        logging.debug('Deal.is_completed called')
        return self.is_started \
            and len(self.player1_cards) == 0 \
            and len(self.player2_cards) == 0 \
            and len(self.player3_cards) == 0 \
            and len(self.player4_cards) == 0

    def _check_for_jackpot(self) -> bool:
        logging.debug('Deal._check_for_jackpot called')
        is_queen_exists = False
        is_six_exists = False
        for card_obj in self.cards:
            if card_obj['card'].suit == CardSuit.CLUBS and card_obj['card'].kind == CardKind.SIX:
                is_six_exists = True
            if card_obj['card'].suit == CardSuit.CLUBS and card_obj['card'].kind == CardKind.QUEEN:
                is_queen_exists = True
        logging.debug(f'Deal._check_for_jackpot is_queen_exists: {is_queen_exists} is_six_exists: {is_six_exists}')
        return is_queen_exists and is_six_exists

    def _get_jackpot_winner(self) -> int:
        logging.debug('Deal._get_jackpot_winner called')
        for card_obj in self.cards:
            if card_obj['card'].suit == CardSuit.CLUBS and card_obj['card'].kind == CardKind.SIX:
                return card_obj['owner']
        return -1

    def _get_jackpot_looser(self) -> int:
        logging.debug('Deal._get_jackpot_looser called')
        for card_obj in self.cards:
            if card_obj['card'].suit == CardSuit.CLUBS and card_obj['card'].king == CardKind.QUEEN:
                return card_obj['owner']
        return -1

    def do_player_step(self, player_index: int, card: Card) -> StepResult:
        logging.debug(f'Deal.do_player_step({player_index}, {card.to_string()}) called')
        if self.player_index != player_index:
            return StepResult.ERROR
        self.cards.append({'card': card, 'owner': player_index})
        self._remove_player_card(player_index, card)
        if self._check_for_jackpot():
            self._process_jackpot()
            return StepResult.JACKPOT
        self.player_index += 1
        if self.player_index > 3:
            self.player_index = 0
        if len(self.cards) > 3:
            taken = self._process_bribe()
            self.player_index = self._get_new_turn_player(taken)
            cards, top_card, top_card_owner = self.get_last_bribe()
            self.request_show_bribe_handler(cards, top_card, top_card_owner)
            if self.is_completed():
                return StepResult.END
        self.request_ask_for_step_handler(self.player_index)
        return StepResult.SUCCESS

    def get_jackpot_winner_team(self) -> int:
        logging.debug('Deal.get_jackpot_winner called')
        for card_obj in self.cards_history[-1]:
            if card_obj['card'].suit == CardSuit.CLUBS and card_obj['card'].kind == CardKind.SIX:
                return self._get_team_index_by_player_index(card_obj['owner'])
        return -1

    def process_deal(self):
        raise NotImplementedError()

    def can_process_next_deal_step(self) -> bool:
        raise NotImplementedError()

    def process_deal_step(self):
        raise NotImplementedError()

    def after_set_trump(self):
        pass

    def set_trump(self, trump: CardSuit):
        logging.debug(f'Deal.set_trump({trump}) called')
        self.is_started = True
        self.trump = trump
        self.after_set_trump()

    def is_wait_for_trump(self):
        logging.debug('Deal.is_wait_for_trump called')
        return self.trump is None

    def get_table_data(self) -> (list[Card], Card, int):
        logging.debug('Deal.get_table_data called')
        return self._get_bribe_data(self.cards, CardSuit(self.trump))

    def get_last_bribe(self) -> (list[Card], Card, int):
        logging.debug('Deal.get_last_bribe called')
        last_bribe = self.cards_history[-1]
        return self._get_bribe_data(last_bribe, CardSuit(self.trump))

    @staticmethod
    def _get_bribe_data(bribe: list, trump: CardSuit) -> (list[Card], Card, int):
        bribe_str = " ".join([f'[{x["card"].to_string()} {x["owner"]}]' for x in bribe])
        logging.debug(f'Deal._get_bribe_data({bribe_str}, {trump}) called')
        result = []
        top_card = None
        top_card_owner = -1
        for card_obj in bribe:
            if top_card is None:
                top_card = card_obj['card']
                top_card_owner = card_obj['owner']
            else:
                if top_card.less_than(card_obj['card'], trump):
                    top_card = card_obj['card']
                    top_card_owner = card_obj['owner']
            result.append(card_obj['card'])
        return result, top_card, top_card_owner


class AllCardsDeal(Deal):
    DEFAULT_TRUMP_CARD = Card(CardKind.ACE, CardSuit.DIAMONDS)

    def __init__(self, owner_index: int):
        logging.debug(f'AllCardsDeal constructor called {owner_index}')
        super().__init__(owner_index)

    def get_deal_type(self):
        return DealType.CLASSIC

    def process_deal(self):
        logging.debug('AllCardsDeal.process_deal called')
        for i in range(0, 8):
            self.player1_cards.append(self.deck.get_next())
            self.player2_cards.append(self.deck.get_next())
            self.player3_cards.append(self.deck.get_next())
            self.player4_cards.append(self.deck.get_next())
        self._update_owner()
        logging.debug(f'AllCardsDeal.process_deal completed: {" ".join([x.to_string() for x in self.player1_cards])};'
                      f'{" ".join([x.to_string() for x in self.player2_cards])};'
                      f'{" ".join([x.to_string() for x in self.player3_cards])};'
                      f'{" ".join([x.to_string() for x in self.player4_cards])} {self.owner_index}')
        self.request_send_current_cards_to_pm_handler(self.owner_index)
        self.request_trump_handler(self.owner_index)

    def after_set_trump(self):
        logging.debug('AllCardsDeal.after_set_trump called')
        for i in range(4):
            if i == self.owner_index:
                continue
            self.request_send_current_cards_to_pm_handler(i)
        self.request_ask_for_step_handler(self.owner_index)

    def process_deal_step(self):
        logging.debug('AllCardsDeal.process_deal_step called')
        pass

    def can_process_next_deal_step(self) -> bool:
        logging.debug('AllCardsDeal.can_process_deal_step called')
        return False

    def _get_new_turn_player(self, previous_taken: int) -> int:
        logging.debug('AllCardsDeal._get_next_turn_player called')
        return previous_taken

    def _get_owner_internal(self, cards: list[Card], index: int) -> bool:
        logging.debug(f'AllCardsDeal._get_owner_internal({" ".join([x.to_string() for x in cards])}, {index}) called')
        for current in cards:
            if self.DEFAULT_TRUMP_CARD.equals(current):
                self.owner_index = index
                return True
        return False

    def _update_owner(self):
        logging.debug('AllCardsDeal._update_owner called')
        for i in range(4):
            if self._get_owner_internal(self.get_player_cards(i), i):
                return


class NumDeal(Deal):
    def __init__(self, owner_index: int):
        logging.debug(f'NumDeal constructor {owner_index} called')
        super().__init__(owner_index)

    def get_deal_type(self) -> DealType:
        return DealType.CLASSIC

    def process_deal(self):
        logging.debug('NumDeal.process_deal called')
        self.process_deal_step()

    def can_process_next_deal_step(self) -> bool:
        logging.debug('NumDeal.can_process_next_deal_step called')
        return self.deck.get_rest_cards() > 0

    def _get_cards_count(self) -> int:
        raise NotImplementedError()

    def after_set_trump(self):
        logging.debug('NumDeal.after_set_trump called')
        for i in range(4):
            if i == self.owner_index:
                continue
            self.request_send_current_cards_to_pm_handler(i)
        self.request_ask_for_step_handler(self.owner_index)

    def process_deal_step(self):
        logging.debug('NumDeal.process_deal_step called')
        for _ in range(0, self._get_cards_count()):
            self.get_player_cards(self.owner_index).append(self.deck.get_next())
        curr_player_index = self.owner_index
        for _ in range(0, self._get_cards_count()):
            for i in range(4):
                if curr_player_index == self.owner_index:
                    continue
                self.get_player_cards(curr_player_index).append(self.deck.get_next())
                curr_player_index = self._inc_player_index(curr_player_index)
        self.request_send_current_cards_to_pm_handler(self.owner_index)
        self.request_trump_handler()

    @staticmethod
    def _inc_player_index(player_index: int) -> int:
        player_index += 1
        if player_index > 3:
            player_index = 0
        return player_index

    def _get_new_turn_player(self, previous_taken: int) -> int:
        return self.owner_index


class TwoDeal(NumDeal):
    def __init__(self, owner_index: int):
        logging.debug(f'TwoDeal constructor {owner_index} called')
        super().__init__(owner_index)

    def _get_cards_count(self) -> int:
        return 2


class ThreeDeal(NumDeal):
    def __init__(self, owner_index: int):
        logging.debug(f'ThreeDeal constructor {owner_index} called')
        super().__init__(owner_index)

    def _get_cards_count(self) -> int:
        return 3


class FourDeal(NumDeal):
    def __init__(self, owner_index: int):
        logging.debug(f'FourDeal constructor {owner_index} called')
        super().__init__(owner_index)

    def _get_cards_count(self) -> int:
        return 4


class PantsStepResult(Enum):
    OK = 1,
    COMPLETE = 2,
    ERROR = 3


class PantsDeal(Deal):
    request_show_pants_handler = None
    request_ask_for_pants_step_handler = None
    request_show_current_pants_handler = None

    def __init__(self, owner_index: int):
        logging.debug(f'PantsDeal constructor {owner_index} called')
        super().__init__(owner_index)
        self.is_trump_received = False
        self.player_cards_count = {0: 0, 1: 0, 2: 0, 3: 0}

    def get_deal_type(self) -> DealType:
        return DealType.PANTS

    def process_deal_step(self):
        pass

    def can_process_next_deal_step(self) -> bool:
        return self.is_trump_received

    def _process_start_cards(self, player_index: int):
        raise NotImplementedError()

    @staticmethod
    def _get_teammate_by_player_index(player_index: int) -> int:
        return (player_index + 2) % 3

    def _can_take_cards(self, player_index: int) -> bool:
        raise NotImplementedError()

    def process_step_cards(self, player_index: int) -> bool:
        logging.debug(f'PantsDeal.process_step_cards({player_index}) called')
        user_cards = self.get_player_cards(player_index)
        if self.player_cards_count[player_index] == 8:
            last_card = user_cards.pop(-1)
            pre_last_card = user_cards.pop(-1)
            self.player_cards_count[player_index] -= 2
            teammate_index = self._get_teammate_by_player_index(player_index)
            if not self._can_take_cards(teammate_index):
                return False
            teammate_cards = self.get_player_cards(teammate_index)
            teammate_cards.append(pre_last_card)
            teammate_cards.append(last_card)
            self.player_cards_count[teammate_index] += 2
        user_cards.append(self.deck.get_next())
        user_cards.append(self.deck.get_last())
        self.player_cards_count[player_index] += 2
        return True

    def can_player_make_step(self, player_index: int) -> bool:
        logging.debug(f'PantsDeal.can_player_make_step({player_index}) called')
        non_trump_count = 0
        player_cards = self.get_player_cards(player_index)
        for card in player_cards:
            if not card.is_trump(self.trump) and card.kind != CardKind.ACE:
                non_trump_count += 1
        return non_trump_count >= 2

    def _get_card_list_for_pants(self, player_index: int) -> list[Card]:
        logging.debug(f'PantsDeal._get_card_list_for_pants({player_index}) called')
        player_cards = self.get_player_cards(player_index)
        result = []
        for card in player_cards:
            if not card.is_trump(self.trump):
                result.append(card)
        return result

    def get_cards_for_pants(self, player_index: int) -> list:
        raise NotImplementedError()

    def process_other_cards(self):
        logging.debug('PantsDeal.process_other_cards called')
        rest_card_count = self.deck.get_rest_cards()
        while rest_card_count > 0:
            min_card_player_index = self._get_min_card_count_index(self.owner_index)
            self.get_player_cards(min_card_player_index).append(self.deck.get_next())
            self.player_cards_count[min_card_player_index] += 1

    def _get_min_card_count_index(self, start_index: int) -> int:
        logging.debug(f'PantsDeal._get_min_card_count_index({start_index}) called')
        curr_start_index = start_index
        min_card_count = 8
        min_card_player_index = -1
        for i in range(4):
            if min_card_count > self.player_cards_count[curr_start_index]:
                min_card_count = self.player_cards_count[curr_start_index]
                min_card_player_index = curr_start_index
                curr_start_index = self._inc_player_index(curr_start_index)
        return min_card_player_index

    @staticmethod
    def _inc_player_index(self: int) -> int:
        next_player_index = self + 1
        if next_player_index > 3:
            next_player_index = 0
        return next_player_index

    def process_deal(self):
        logging.debug('PantsDeal.process_deal called')
        self._process_start_cards(self.owner_index)
        self.request_send_current_cards_to_pm_handler(self.owner_index)
        self.request_trump_handler(self.owner_index)

    def after_set_trump(self):
        logging.debug('PantsDeal.after_set_trump called')
        self.request_ask_for_pants_step_handler(self.owner_index)

    def set_pant_card(self, player_index: int, cards) -> bool:
        raise NotImplementedError()

    def _complete_pant_part(self):
        raise NotImplementedError()

    def get_pants_cards(self) -> list:
        raise NotImplementedError()

    def _get_new_turn_player(self, previous_taken: int) -> int:
        return previous_taken


class SinglePantsDeal(PantsDeal):
    def __init__(self, owner_index: int):
        logging.debug(f'SinglePantsDeal constructor {owner_index} called')
        super().__init__(owner_index)
        self.pant_cards = []

    def get_cards_for_pants(self, player_index: int) -> list:
        logging.debug(f'SinglePantsDeal.get_cards_for_pants({player_index}) called')
        return self._get_card_list_for_pants(player_index)

    def set_pant_card(self, player_index: int, cards) -> bool:
        logging.debug(f'SinglePantsDeal.set_pant_card({player_index}, {cards}) called')
        if len(cards) != 1:
            return False
        card = cards[0]
        if card.is_trump(self.trump):
            return False
        self.player_cards_count[player_index] -= 1
        self.pant_cards.append({'card': card, 'owner': player_index})
        result, top_card, top_card_owner = self._complete_pant_part()
        if result:
            owner_team_index = self._get_team_index_by_player_index(self.owner_index)
            card_owner_team_index = self._get_team_index_by_player_index(top_card_owner)
            if card_owner_team_index != owner_team_index:
                self.player_index = top_card_owner
            else:
                self.player_index = self.owner_index
            self.request_show_pants_handler([x['card'] for x in self.pant_cards], top_card, top_card_owner,
                                            None, None, -1)
            self.request_ask_for_step_handler(self.player_index)
            return True
        self.request_show_current_pants_handler(self.get_pants_cards())
        return True

    def _complete_pant_part(self) -> (bool, Card, int):
        logging.debug('SinglePantsDeal._complete_pant_part called')
        if len(self.pant_cards) != 4:
            return False, None, -1
        top_pant_card = self.pant_cards[0]['card']
        top_pant_player = self.pant_cards[0]['owner']
        for i in range(1, 4):
            if top_pant_card.less_than(self.pant_cards[i]['card']):
                top_pant_card = self.pant_cards[i]['card']
                top_pant_player = self.pant_cards[i]['owner']
        return True, top_pant_card, top_pant_player

    def get_pants_cards(self) -> list:
        logging.debug('SinglePantsDeal.get_pants_cards called')
        result = []
        if len(self.pant_cards) < 2:
            return result
        for i in range(1, len(self.pant_cards)):
            result.append((self.pant_cards[i]['card'],))
        return result

    def _can_take_cards(self, player_index: int) -> bool:
        logging.debug(f'SinglePantsDeal._car_take_cards({player_index}) called')
        return self.player_cards_count[player_index] <= 4

    def _process_start_cards(self, player_index: int):
        logging.debug(f'SinglePantsDeal._process_start_cards({player_index}) called')
        user_cards = self.get_player_cards(player_index)
        user_cards.append(self.deck.get_next())
        user_cards.append(self.deck.get_last())
        self.player_cards_count[player_index] += 2


class DoublePantsDeal(PantsDeal):
    def __init__(self, owner_index: int):
        logging.debug(f'DoublePantsDeal constructor {owner_index} called')
        super().__init__(owner_index)
        self.left_pant_cards = []
        self.right_pant_cards = []

    def get_cards_for_pants(self, player_index: int) -> list:
        logging.debug(f'DoublePantsDeal.get_cards_for_pants({player_index}) called')
        return list(permutations(self._get_card_list_for_pants(player_index), 2))

    def set_pant_card(self, player_index: int, cards) -> bool:
        logging.debug(f'DoublePantsDeal.set_pant_card({player_index}, {cards}) called')
        if len(cards) != 2:
            return False
        left_card, right_card = cards
        if left_card.is_trump(self.trump) or right_card.is_trump(self.trump):
            return False
        self.player_cards_count[player_index] -= 2
        self.left_pant_cards.append({'card': left_card, 'owner': player_index})
        self.right_pant_cards.append({'card': right_card, 'owner': player_index})
        result, top_left_card, top_left_card_owner, top_right_card, top_right_card_owner = self._complete_pant_part()
        if result:
            owner_team_index = self._get_team_index_by_player_index(self.owner_index)
            left_owner_team_index = self._get_team_index_by_player_index(top_left_card_owner)
            right_owner_team_index = self._get_team_index_by_player_index(top_right_card_owner)
            if left_owner_team_index != owner_team_index or right_owner_team_index != owner_team_index:
                if left_owner_team_index != owner_team_index and right_owner_team_index != owner_team_index:
                    self.player_index = self._inc_player_index(self.owner_index)
                elif left_owner_team_index != owner_team_index:
                    self.player_index = top_left_card_owner
                else:
                    self.player_index = top_right_card_owner
            self.request_show_pants_handler(
                [x['card'] for x in self.left_pant_cards], top_left_card, top_left_card_owner,
                [x['card'] for x in self.right_pant_cards], top_right_card, top_right_card_owner)
            self.request_ask_for_step_handler(self.player_index)
            return True
        self.request_show_current_pants_handler(self.get_pants_cards())
        return True

    def _complete_pant_part(self) -> (bool, Card, int, Card, int):
        logging.debug('DoublePantsDeal.+complete_pant_part called')
        if len(self.left_pant_cards) != 4 or len(self.right_pant_cards) != 4:
            return False, None, -1, None, -1
        top_left_pant_card, top_right_pant_card = \
            self.left_pant_cards[0]['card'], self.right_pant_cards[0]['card']
        top_left_pant_player, top_right_pant_player = \
            self.left_pant_cards[0]['owner'], self.right_pant_cards[0]['owner']
        for i in range(1, 4):
            if top_left_pant_card.less_than(self.left_pant_cards[i]['card']):
                top_left_pant_card = self.left_pant_cards[i]['card']
                top_left_pant_player = self.left_pant_cards[i]['owner']
            if top_right_pant_card.less_than(self.right_pant_cards[i]['card']):
                top_right_pant_card = self.right_pant_cards[i]['card']
                top_right_pant_player = self.right_pant_cards[i]['owner']
        return True, top_left_pant_card, top_left_pant_player, top_right_pant_card, top_right_pant_player

    def get_pants_cards(self) -> list:
        logging.debug('DoublePantsDeal.get_pants_cards called')
        result = []
        if len(self.left_pant_cards) < 2 or len(self.right_pant_cards) < 2:
            return result
        for i in range(1, len(self.left_pant_cards)):
            result.append((self.left_pant_cards[i]['card'], self.right_pant_cards[i]['card']))
        return result

    def _can_take_cards(self, player_index: int) -> bool:
        logging.debug(f'DoublePantsDeal._can_take_cards({player_index}) called')
        return self.player_cards_count[player_index] <= 2

    def _process_start_cards(self, player_index: int):
        logging.debug(f'DoublePantsDeal._process_start_cards({player_index}) called')
        user_cards = self.get_player_cards(player_index)
        user_cards.append(self.deck.get_next())
        user_cards.append(self.deck.get_next())
        user_cards.append(self.deck.get_last())
        user_cards.append(self.deck.get_last())
        self.player_cards_count[player_index] += 4


class DealTypes:
    names = ['По всем', 'По 2', 'По 3', 'По 4', 'Одинарные штаны', 'Двойные штаны']

    @staticmethod
    def get_deal(name: str, player_index: int) -> Deal | None:
        logging.debug(f'DealTypes.get_deal({name}, {player_index}) called')
        if name == 'По всем':
            return AllCardsDeal(player_index)
        if name == 'По 2':
            return TwoDeal(player_index)
        if name == 'По 3':
            return ThreeDeal(player_index)
        if name == 'По 4':
            return FourDeal(player_index)
        if name == 'Одинарные штаны':
            return SinglePantsDeal(player_index)
        if name == 'Двойные штаны':
            return DoublePantsDeal(player_index)
        return None

    def is_deal(self, text: str) -> bool:
        logging.debug(f'DealTypes.is_deal({text}) called')
        return text.lower() in [x.lower() for x in self.names]
