import sqlite3
import logging

from models import GoatUser


class DBConnector:
    def __init__(self):
        self.logger = logging.getLogger()
        self._con = sqlite3.connect('goat.db')
        self._cur = self._con.cursor()
        self.is_connected = True
        logging.info('connected to database')

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if not self.is_connected:
            return
        self._con.close()
        self._cur = None
        self.is_connected = False
        logging.info('disconnected from database')

    def get_users(self, chat_id: int) -> list[GoatUser] | None:
        if not self.is_connected:
            logging.warning('not connected to database')
            return None
        db_result = self._cur.execute('SELECT `user_id`,`first_name`,`last_name`,`user_name` FROM `users` WHERE '
                                      '`chat_id`=?', [chat_id])
        result = []
        for row in db_result:
            user_id, first_name, last_name, user_name = row
            result.append(GoatUser(user_id, first_name, last_name, user_name))
        return result

    def add_user(self, chat_id: int, user: GoatUser) -> bool:
        if not self.is_connected:
            logging.warning('not connected to database')
            return False
        self._cur.execute('SELECT `id` FROM `users` WHERE `chat_id`=? AND `user_id`=?', (chat_id, user.id))
        result = self._cur.fetchone()
        if result is not None:
            return False
        self._cur.execute('INSERT INTO `users`(`chat_id`, `user_id`, `first_name`, `last_name`, `user_name`) '
                          'VALUES(?, ?, ?, ?, ?)',
                          (chat_id, user.id, user.first_name, user.last_name, user.user_name))
        self._con.commit()
        return True