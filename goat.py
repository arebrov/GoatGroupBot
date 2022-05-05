import telebot
import logging
from telebot import types

from DBConnector import DBConnector
from deals import DealTypes
from goatGame import GoatGame
from models import Card, CardSuit, SUIT_STRING_TO_SUIT, CardSuitString, START_GAME_MESSAGES, GoatUser, StepResult


def _message_to_log_str(message: types.Message):
    if message is None:
        return ''
    return f'Msg(from: {message.from_user.id}, ' \
           f'reply_to: {_message_to_log_str(message.reply_to_message)}, ' \
           f'text: {message.text})'


class Goat:
    def __init__(self, tele_bot: telebot.TeleBot):
        logging.debug('Goat constructor called')
        self.db = DBConnector()
        self.chat_id = None
        self.is_started = False
        self.request_game_message_id = -1
        self.game = None
        self.bot = tele_bot

    def on_message_received(self, message: types.Message):
        logging.debug('Goat.on_message_received({0}) called', _message_to_log_str(message))
        if self.is_started:
            self.bot.reply_to(message, "Тсс, играют, не мешай")

    def start_game(self, chat_id: int, player_id: int):
        logging.debug('Goat.start_game({0}, {1}) called', chat_id, player_id)
        self.is_started = True
        self.game = GoatGame(player_id, self.on_request_trump,
                             self.send_current_cards_to_private_message,
                             self.on_request_show_bribe_handler,
                             self.on_ask_for_deal,
                             self.on_ask_for_step,
                             self.on_request_show_pants,
                             self.send_jackpot,
                             self.show_total_score,
                             self.on_ask_for_pants_step,
                             self.on_request_show_current_pants)
        self.chat_id = chat_id
        self._request_for_game(player_id)

    def stop_game(self):
        logging.debug('Goat.stop_game called')
        self.is_started = False
        self.game = None

    def _request_for_game(self, player_id: int):
        logging.debug('Goat._request_for_game({0}) called', player_id)
        markup = types.ReplyKeyboardMarkup()
        markup.one_time_keyboard = True
        for message in START_GAME_MESSAGES.keys():
            markup.row(message)
        users = self.db.get_users(self.chat_id)
        request_links = [f'[{x.get_full_name()}](tg://user?id={str(x.id)})' for x in users if x.id != player_id]
        message = self.bot.send_message(self.chat_id, f'Кто в козла?\r\n\r\n{", ".join(request_links)}',
                                        reply_markup=markup, parse_mode='MarkdownV2')
        self.request_game_message_id = message.id
        pass

    def start(self):
        logging.debug('Goat.start called')
        self.game.first_deal()
        pass

    @staticmethod
    def _cards_to_str(cards: list[Card]) -> str:
        cards_str = []
        for card in cards:
            cards_str.append(card.to_string())
        return "\t".join(cards_str)

    @staticmethod
    def _suit_str_to_suit(text: str) -> CardSuit:
        if text in SUIT_STRING_TO_SUIT:
            return SUIT_STRING_TO_SUIT[text]
        return CardSuit.NONE

    def on_trump_received(self, message: types.Message):
        logging.debug('Goat.on_trump_received({0}) called', _message_to_log_str(message))
        if not self.is_started or not self.game.is_wait_for_trump():
            self.bot.reply_to(message, "Так нельзя!")
            return
        selected_trump = self._suit_str_to_suit(message.text)
        self.game.select_trump(message.from_user.id, selected_trump)
        pass

    def on_card_received(self, message: types.Message):
        logging.debug('Goat.on_card_received({0}) called', _message_to_log_str(message))
        if not self.is_started or not self.game.is_wait_for_player_card(message.from_user.id):
            self.bot.reply_to(message, 'Так нельзя.')
            return
        _, card = Card.try_parse(message.text)
        if not self.game.do_player_step(message.from_user.id, card):
            self.bot.reply_to(message, 'Ну дождись своего хода')

    def on_card_pair_received(self, message: types.Message):
        logging.debug('Goat.on_card_pair_received({0}) called', _message_to_log_str(message))
        if not self.is_started or not self.game.is_wait_for_player_card_pair(message.from_user.id):
            self.bot.reply_to(message, 'Так нельзя...')
            return
        cards = message.text.split(' ', 2)
        _, card1 = Card.try_parse(cards[0])
        _, card2 = Card.try_parse(cards[1])
        if not self.game.do_player_pants_step(message.from_user.id, card1, card2):
            self.bot.reply_to(message, 'Так нельзя!!!')

    def on_deal_received(self, message: types.Message):
        logging.debug('Goat.on_deal_received({0}) called', _message_to_log_str(message))
        if not self.is_started or not self.game.is_wait_for_deal(message.from_user.id):
            self.bot.reply_to(message, "Так нельзя")
            return
        if not self.game.start_next_deal(message.from_user.id, message.text):
            self.bot.reply_to(message, 'Вы не можете выбрать хваленку')
            return
        pass

    def on_request_trump(self, player_id: int):
        logging.debug('Goat.on_request_trump({0}) called', player_id)
        user = self.bot.get_chat_member(self.chat_id, player_id).user
        markup = types.ReplyKeyboardMarkup()
        markup.one_time_keyboard = True
        markup.selective = True
        markup.row(types.KeyboardButton(str(CardSuitString.DIAMONDS)), types.KeyboardButton(str(CardSuitString.HEARTS)))
        markup.row(types.KeyboardButton(str(CardSuitString.SPADES)), types.KeyboardButton(str(CardSuitString.CLUBS)))
        markup.row("Без козыря")
        self.bot.send_message(self.chat_id, f'[{user.full_name}]'
                                            f'(tg://user?id={str(player_id)}), выбирай козырь',
                              reply_markup=markup, parse_mode='MarkdownV2')
        pass

    def on_request_show_pants(self, l_c: list[Card], t_l_c: Card, t_l_c_o: int,
                              r_c: list[Card], t_r_c: Card, t_r_c_o: int, next_id: int):
        logging.debug('Goat.on_request_show_pants({0}, {1}, {2}, {3}, {4}, {5}, {6}) called',
                      self._cards_to_str(l_c),
                      t_l_c.to_string(),
                      t_l_c_o,
                      self._cards_to_str(r_c),
                      t_r_c.to_string() if t_r_c is not None else None,
                      t_l_c_o,
                      next_id)
        left_taken_user = self.bot.get_chat_member(self.chat_id, t_l_c_o).user
        right_taken_user = self.bot.get_chat_member(self.chat_id, t_r_c_o).user
        next_user = left_taken_user if next_id == t_l_c_o else right_taken_user
        self.bot.send_message(self.chat_id, f'Штаны:\r\n\r\n'
                                            f'Слева: {self._cards_to_str(l_c)}\r\n'
                                            f'Забрал: *{left_taken_user.full_name}* - *{t_l_c.to_string()}*\r\n\r\n'
                                            f'Справа: {self._cards_to_str(r_c)}\r\n'
                                            f'Забрал: *{right_taken_user.full_name}* - *{t_r_c.to_string()}*\r\n\r\n'
                                            f'Ходит: *{next_user.full_name}*', parse_mode="MarkdownV2")
        pass

    def on_request_show_current_pants(self, cards: list):
        logging.debug('Goat.on_request_show_current_pants({0}) called', cards)
        result = ''
        for card_obj in cards:
            if len(result) > 0:
                result += '\r\n'
            if len(card_obj) == 2:
                result += card_obj[0].to_string() + " " + card_obj[1].to_string()
            elif len(card_obj) == 1:
                result += card_obj[0].to_string()
        self.bot.send_message(self.chat_id, f'Штаны:\r\n\r\n{result}')

    def send_current_cards_to_private_message(self, player_id: int):
        logging.debug('Goat.send_current_cards_to_private_message({0}) called', player_id)
        cards = self.game.get_player_cards(player_id)
        self.bot.send_message(player_id, f'Ваши карты: {self._cards_to_str(cards)}')
        pass

    def on_request_show_bribe_handler(self, cards: list[Card], card: Card, player_id: int):
        logging.debug('Goat.on_request_show_bribe_handler({0}, {1}, {2}) called',
                      self._cards_to_str(cards), card.to_string(), player_id)
        user = self.bot.get_chat_member(self.chat_id, player_id).user
        self.bot.send_message(self.chat_id, f'Взятка: {self._cards_to_str(cards)}\r\n'
                                            f'Забрал: *{user.full_name}* - *{card.to_string()}*\r\n\r\n',
                              parse_mode='MarkdownV2')
        pass

    def on_ask_for_step(self, player_id: int):
        logging.debug('Goat.on_ask_for_step({0}) called', player_id)
        user = self.bot.get_chat_member(self.chat_id, player_id).user
        cards = self.game.get_player_cards(player_id)
        markup = types.ReplyKeyboardMarkup()
        markup.one_time_keyboard = True
        markup.selective = True
        cards_str = []
        for card in cards:
            cards_str.append(card.to_string())
        markup.add(*cards_str, row_width=4)
        self.bot.send_message(self.chat_id, f'Сейчас ходит [{user.full_name}]'
                                            f'(tg://user?id={str(player_id)})',
                              reply_markup=markup, parse_mode='MarkdownV2')

    def on_ask_for_pants_step(self, player_id: int):
        logging.debug('Goat.on_ask_for_pants_step({0}) called', player_id)
        card_pairs = self.game.get_available_pants_pairs(player_id)
        if card_pairs is None:
            self.bot.send_message(player_id, f'Что-то пошло не по плану')
            return
        markup = types.ReplyKeyboardMarkup()
        markup.one_time_keyboard = True
        markup.selective = True
        cards_str = []
        for card_pair in card_pairs:
            if len(card_pair) == 2:
                cards_str.append(f'{card_pair[0].to_string()} {card_pair[1].to_string()}')
            else:
                cards_str.append(card_pair[0].to_string())
        markup.add(*cards_str, row_width=4)
        self.bot.send_message(player_id, f'Что заложить?',
                              reply_markup=markup, parse_mode='MarkdownV2')

    def on_ask_for_deal(self, player_id: int):
        logging.debug('Goat.on_ask_for_deal({0}) called', player_id)
        user = self.bot.get_chat_member(self.chat_id, player_id).user
        markup = types.ReplyKeyboardMarkup()
        markup.one_time_keyboard = True
        markup.selective = True
        deals_str = self.game.get_deal_list()
        for deal_str in deals_str:
            markup.row(deal_str)
        self.bot.send_message(self.chat_id, f'Хвалится [{user.full_name}]'
                                            f'(tg://user?id={str(player_id)})',
                              reply_markup=markup, parse_mode='MarkdownV2')

    def send_jackpot(self, winner_id: int, looser_id: int):
        logging.debug('Goat.send_jackpot({0}, {1}) called', winner_id, looser_id)
        winner_user = self.bot.get_chat_member(self.chat_id, winner_id).user
        looser_user = self.bot.get_chat_member(self.chat_id, looser_id).user
        self.bot.send_message(self.chat_id, f'Четыре балла!\r\n\r\n'
                                            f'*{winner_user.full_name}* поймал *{looser_user}*',
                              parse_mode='MarkdownV2')

    def show_total_score(self, first_team: int, second_team: int):
        logging.debug('Goat.show_total_score({0}, {1}) called', first_team, second_team)
        self.bot.send_message(self.chat_id, f'Счет: *{first_team}:{second_team}*',
                              reply_markup=types.ReplyKeyboardRemove(), parse_mode='MarkdownV2')

    def on_player_apply_to_game_received(self, message: types.Message):
        logging.debug('Goat.on_player_apply_to_game_received({0}) called', _message_to_log_str(message))
        markup = types.ReplyKeyboardRemove()
        if self.game.need_player_count() > 0:
            self.game.add_player(message.from_user.id)
            if self.game.need_player_count() == 0:
                self.bot.send_message(self.chat_id, 'Народ набрали, поїхали', reply_markup=markup)
                self.game.start()
        else:
            self.bot.reply_to(message, 'Сорян, все места заняты', reply_markup=markup)

    def register_user(self, chat_id: int, message: types.Message):
        logging.debug('Goat.register_user({0}, {1}) called', chat_id, _message_to_log_str(message))
        if self.db.add_user(chat_id, GoatUser(message.from_user.id, message.from_user.first_name,
                                              message.from_user.last_name, message.from_user.username)):
            self.bot.reply_to(message, f'Салют, {message.from_user.full_name}')
        else:
            self.bot.reply_to(message, 'Брат, здоровались уже')
        pass

    def get_started_member_count(self, chat_id: int):
        logging.debug('Goat.get_started_member_count({0}) called', chat_id)
        return len(self.db.get_users(chat_id))


bot = telebot.TeleBot('TOKEN')

goat = Goat(bot)


class RespondToRequestTrump(telebot.custom_filters.SimpleCustomFilter):
    key = 'trump_response'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        logging.debug('check trump_response({0}) called', _message_to_log_str(message))
        reply_message = message.reply_to_message
        if reply_message is None or reply_message.via_bot is None or \
                reply_message.via_bot.username.lower() != 'goatgroupbot':
            return False
        return message.text.lower() in SUIT_STRING_TO_SUIT


class RespondToRequestCard(telebot.custom_filters.SimpleCustomFilter):
    key = 'card_response'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        logging.debug('check card_response({0}) called', _message_to_log_str(message))
        reply_message = message.reply_to_message
        if reply_message is None or reply_message.via_bot is None or \
                reply_message.via_bot.username.lower() != 'goatgroupbot':
            return False
        if len(message.text) < 2 or len(message.text) > 3:
            return False
        result, _ = Card.try_parse(message.text)
        return result


class RespondToRequestCardPair(telebot.custom_filters.SimpleCustomFilter):
    key = 'card_pair_response'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        logging.debug('check card_pair_response({0}) called', _message_to_log_str(message))
        if len(message.text) < 5 or len(message.text) > 7:
            return False
        pair = message.text.split(' ', 2)
        result1, _ = Card.try_parse(pair[0])
        result2, _ = Card.try_parse(pair[1])
        return result1 and result2


class RespondToRequestDeal(telebot.custom_filters.SimpleCustomFilter):
    key = 'deal_response'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        logging.debug('check deal_response({0}) called', _message_to_log_str(message))
        reply_message = message.reply_to_message
        if reply_message is None or reply_message.via_bot is None or \
                reply_message.via_bot.username.lower() != 'goatgroupbot':
            return False
        return DealTypes().is_deal(reply_message.text)


class RespondToRequestPlayers(telebot.custom_filters.SimpleCustomFilter):
    key = 'play_response'

    @staticmethod
    def check(message: telebot.types.Message, **kwargs):
        logging.debug('check play_response({0}) called', _message_to_log_str(message))
        reply_message = message.reply_to_message
        if reply_message is None or reply_message.via_bot is None or \
                reply_message.via_bot.username.lower() != 'goatgroupbot':
            return False
        return reply_message in START_GAME_MESSAGES.keys()


@bot.message_handler(commands=['start'])
def start(message: types.Message):
    logging.debug('start {0} called', _message_to_log_str(message))
    goat.register_user(message.chat.id, message)
    pass


@bot.message_handler(commands=['deal'])
def deal(message: types.Message):
    logging.debug('deal {0} called', _message_to_log_str(message))
    if message.chat.type != 'group' and message.chat.type != 'supergroup':
        bot.reply_to(message, 'Бот работает только в группах')
        return
    if bot.get_chat_member_count(message.chat.id) < 4:
        bot.reply_to(message, 'Для игры нужно минимум 4 человека')
        return
    if goat.get_started_member_count(message.chat.id) < 4:
        bot.reply_to(message, 'Мало людей в группе запустили меня, толкни чтобы написали /start')
        return
    if goat.is_started:
        bot.reply_to(message, 'Игра уже запущена')
        return
    goat.start_game(message.chat.id, message.from_user.id)


@bot.message_handler(commands=['stop'])
def stop(message: types.Message):
    logging.debug('stop {0} called', _message_to_log_str(message))
    if not goat.is_started:
        bot.reply_to(message, 'Игра не запущена')
        return
    goat.stop_game()
    bot.reply_to(message, 'Игра остановлена')


@bot.message_handler(play_response=True)
def on_apply_to_game_received(message: types.Message):
    logging.debug('on_apply_to_game_received {0} called', _message_to_log_str(message))
    if message.reply_to_message.id == goat.request_game_message_id:
        goat.on_player_apply_to_game_received(message)


@bot.message_handler(trump_response=True)
def on_trump_received(message: types.Message):
    logging.debug('on_trump_received {0} called', _message_to_log_str(message))
    goat.on_trump_received(message)


@bot.message_handler(card_response=True)
def on_card_received(message: types.Message):
    logging.debug('on_card_received {0} called', _message_to_log_str(message))
    goat.on_card_received(message)


@bot.message_handler(card_pair_response=True)
def on_card_pair_received(message: types.Message):
    logging.debug('on_card_pair_received {0} called', _message_to_log_str(message))
    goat.on_card_pair_received(message)


@bot.message_handler(deal_response=True)
def on_deal_received(message: types.Message):
    logging.debug('on_deal_received {0} called', _message_to_log_str(message))
    goat.on_deal_received(message)


@bot.message_handler()
def on_message_received(message: types.Message):
    logging.debug('on_message_received {0} called', _message_to_log_str(message))
    goat.on_message_received(message)


bot.infinity_polling()
