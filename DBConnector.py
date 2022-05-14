import sqlite3
import logging

from models import GoatUser


class DBConnector:
    @staticmethod
    def get_users(chat_id: int) -> list[GoatUser] | None:
        _con = sqlite3.connect('goat.db')
        _cur = _con.cursor()
        db_result = _cur.execute('SELECT `user_id`,`first_name`,`last_name`,`user_name` FROM `users` WHERE '
                                 '`chat_id`=?', [chat_id])
        result = []
        for row in db_result:
            user_id, first_name, last_name, user_name = row
            result.append(GoatUser(user_id, first_name, last_name, user_name))
        _con.close()
        return result

    @staticmethod
    def add_user(chat_id: int, user: GoatUser) -> bool:
        _con = sqlite3.connect('goat.db')
        _cur = _con.cursor()
        _cur.execute('SELECT `id` FROM `users` WHERE `chat_id`=? AND `user_id`=?', (chat_id, user.id))
        result = _cur.fetchone()
        if result is not None:
            return False
        _cur.execute('INSERT INTO `users`(`chat_id`, `user_id`, `first_name`, `last_name`, `user_name`) '
                     'VALUES(?, ?, ?, ?, ?)',
                     (chat_id, user.id, user.first_name, user.last_name, user.user_name))
        _con.commit()
        _con.close()
        return True

