from deals import AllCardsDeal, DealTypes, Deal, DealType
from models import Card, CardSuit, StepResult
import logging


class GoatGame:
    def __init__(self, owner_id, request_trump_handler, request_send_current_cards_to_pm_handler,
                 request_show_bribe_handler, request_ask_for_deal_handler, request_ask_for_step_handler,
                 request_show_pants_handler, request_show_jackpot_handler, request_show_total_score_handler,
                 request_ask_for_pants_step_handler, request_show_current_pants_handler):
        self.request_trump_handler = request_trump_handler
        self.request_send_current_cards_to_pm_handler = request_send_current_cards_to_pm_handler
        self.request_show_pants_handler = request_show_pants_handler
        self.request_show_bribe_handler = request_show_bribe_handler
        self.request_ask_for_deal_handler = request_ask_for_deal_handler
        self.request_ask_for_step_handler = request_ask_for_step_handler
        self.request_show_jackpot_handler = request_show_jackpot_handler
        self.request_show_total_score_handler = request_show_total_score_handler
        self.request_ask_for_pants_step_handler = request_ask_for_pants_step_handler
        self.request_show_current_pants_handler = request_show_current_pants_handler
        self.deal = None
        self.player1_id = owner_id
        self.player2_id = -1
        self.player3_id = -1
        self.player4_id = -1
        self.first_team_total_score = 0
        self.second_team_total_score = 0

    def add_player(self, player: int) -> bool:
        if self.player1_id == player or self.player2_id == player or \
                self.player3_id == player or self.player4_id == player:
            return False
        logging.debug(f'GoatGame.add_player({player}) called')
        if self.player2_id < 0:
            self.player2_id = player
            return True
        elif self.player3_id < 0:
            self.player3_id = player
            return True
        elif self.player4_id < 0:
            self.player4_id = player
            return True
        return False

    def need_player_count(self) -> int:
        logging.debug('GoatGame.need_player_count called')
        count = 3
        if self.player2_id > 0:
            count -= 1
        if self.player3_id > 0:
            count -= 1
        if self.player4_id > 0:
            count -= 1
        return count

    def first_deal(self):
        logging.debug('GoatGame.first_deal called')
        if self.need_player_count() != 0:
            return
        self.deal = AllCardsDeal(0)
        self._apply_deal_handlers(self.deal)
        self.deal.process_deal()

    def get_player_cards(self, player_id: int) -> list[Card]:
        if self.need_player_count() != 0:
            raise NotImplementedError()
        return self.deal.get_player_cards(self.get_player_index_by_id(player_id))

    def get_player_index_by_id(self, player_id: int) -> int:
        players = {self.player1_id: 0, self.player2_id: 1, self.player3_id: 2, self.player4_id: 3}
        return players.get(player_id)

    def get_player_id_by_index(self, player_id: int) -> int:
        players = {0: self.player1_id, 1: self.player2_id, 2: self.player3_id, 3: self.player4_id}
        return players.get(player_id)

    def get_owner(self) -> int:
        return self.get_player_id_by_index(self.deal.owner_index)

    def select_trump(self, player_id: int, trump: CardSuit) -> bool:
        if self.get_owner() != player_id:
            return False
        self.deal.set_trump(trump)
        return True

    def is_wait_for_trump(self):
        return self.deal.is_wait_for_trump()

    def do_player_step(self, player_id: int, card: Card) -> True:  # TODO request should be from deals?
        logging.debug(f'GoatGame.do_player_step({player_id}, {card.to_string()}) called')
        player_index = self.get_player_index_by_id(player_id)
        if self.deal.player_index != player_index:
            return False
        step_result = self.deal.do_player_step(player_index, card)
        if step_result is StepResult.JACKPOT:
            self._on_jackpot(self.deal.get_jackpot_winner_team())
            self._complete_current_deal()
        if step_result is StepResult.END:
            self._on_complete_deal()
            self._complete_current_deal()
        return True

    def do_player_pants_step(self, player_id: int, left_card: Card, right_card: Card) -> bool:
        logging.debug(f'GoatGame.do_player_pants_step'
                      f'({player_id}, {left_card.to_string()}, {right_card.to_string()}) called')
        if self.deal.get_deal_type() != DealType.PANTS:
            return False
        player_index = self.get_player_index_by_id(player_id)
        if self.deal.player_index != player_index:
            return False
        return self.deal.set_pant_card(player_index, left_card, right_card)

    def _complete_current_deal(self):
        logging.debug('GoatGame._complete_current_deal called')
        self.request_show_total_score_handler(self.first_team_total_score, self.second_team_total_score)
        current_owner_index = self.deal.owner_index + 1
        if current_owner_index > 3:
            current_owner_index = 0
        self.request_ask_for_deal_handler(self.get_player_id_by_index(current_owner_index))

    def is_wait_for_player_card(self, player_id: int):
        logging.debug(f'GoatGame.is_wait_for_player_card({player_id}) called')
        player_index = self.get_player_index_by_id(player_id)
        return self.deal.player_index == player_index

    def get_table_data(self) -> (list[Card], Card, int, int):
        cards, top, top_owner = self.deal.get_table_data()
        return cards, top, self.get_player_id_by_index(top_owner), self.get_player_id_by_index(self.deal.player_index)

    def get_last_bribe_data(self) -> (list[Card], Card, int, int):
        cards, top, top_owner = self.deal.get_last_bribe()
        return cards, top, self.get_player_id_by_index(top_owner), self.get_player_id_by_index(self.deal.player_index)

    def should_go_to_next_deal(self) -> bool:
        return not self.deal.can_process_next_deal_step()

    def is_wait_for_deal(self, player_id: int):
        owner_index = self.deal.owner_index
        next_owner_index = owner_index + 1
        if next_owner_index > 3:
            next_owner_index = 0
        return self.deal.is_completed() and next_owner_index == self.get_player_index_by_id(player_id)

    def get_next_deal_owner(self) -> int:
        next_owner_index = self.deal.owner_index
        next_owner_index += 1
        if next_owner_index > 3:
            next_owner_index = 0
        return self.get_player_id_by_index(next_owner_index)

    def start_next_deal(self, player_id: int, deal_name: str) -> bool:
        logging.debug(f'GoatGame.start_next_deal({player_id}, {deal_name}) called')
        if not self.deal.is_completed() or self.get_next_deal_owner() != player_id:
            return False
        if not DealTypes().is_deal(deal_name):
            return False
        deal = DealTypes.get_deal(deal_name, self.get_player_index_by_id(player_id))
        if deal is None:
            return False
        self._apply_deal_handlers(deal)
        self.deal = deal
        self.deal.process_deal()
        return True

    def _apply_deal_handlers(self, deal: Deal):
        deal.request_trump_handler = lambda x: self.request_trump_handler(self.get_player_id_by_index(x))
        deal.request_send_current_cards_to_pm_handler = lambda x: \
            self.request_send_current_cards_to_pm_handler(self.get_player_id_by_index(x))
        deal.request_show_bribe_handler = lambda cards, card, x: \
            self.request_show_bribe_handler(cards, card, self.get_player_id_by_index(x))
        deal.request_ask_for_deal_handler = lambda x: self.request_ask_for_deal_handler(self.get_player_id_by_index(x))
        deal.request_ask_for_step_handler = lambda x: self.request_ask_for_step_handler(self.get_player_id_by_index(x))
        deal.request_show_jackpot_handler = lambda x, y: \
            self.request_show_jackpot_handler(self.get_player_id_by_index(x), self.get_player_id_by_index(y))

        if deal.get_deal_type() == DealType.PANTS:
            deal.request_show_pants_handler = lambda l_c, l_t_c, l_t_c_o, r_c, r_t_c, r_t_c_o, next_index: \
                self.request_show_pants_handler(l_c, l_t_c, self.get_player_id_by_index(l_t_c_o),
                                                r_c, r_t_c, self.get_player_id_by_index(r_t_c_o),
                                                self.get_player_id_by_index(next_index))
            deal.request_ask_for_pants_step_handler = lambda x: \
                self.request_ask_for_pants_step_handler(self.get_player_id_by_index(x))
            deal.request_show_current_pants_handler = self.request_show_current_pants_handler

    def get_score(self) -> (int, int):
        return self.first_team_total_score, self.second_team_total_score

    def _on_complete_deal(self):
        logging.debug('GoatGame._on_complete_deal called')
        first_team_score = self.deal.get_team_score(0)
        second_team_score = self.deal.get_team_score(1)
        if first_team_score > second_team_score:
            self.first_team_total_score += 4 if second_team_score < 30 else 2
        else:
            self.second_team_total_score += 4 if first_team_score < 30 else 2

    def _on_jackpot(self, winner_team_index: int):
        logging.debug(f'GoatGame._on_jackpot({winner_team_index}) called')
        if winner_team_index == 0:
            self.first_team_total_score += 4
        else:
            self.second_team_total_score += 4

    @staticmethod
    def get_deal_list() -> list[str]:
        return DealTypes.names

    def get_available_pants_pairs(self, player_id: int) -> list | None:
        if self.deal.get_deal_type() != DealType.PANTS:
            return None
        return self.deal.get_card_pairs_for_pants(self.get_player_index_by_id(player_id))
