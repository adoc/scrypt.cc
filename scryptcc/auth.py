import requests
from scryptcc import *


__all__ = ('Auth', )


class Auth:
    def __init__(self, connector):
        self._conn = connector

    def login(self, user, passw):
        payload = {'action': '1',
                   'username': user,
                   'password': passw,
                   'submit': 'Login'}
        resp = self._conn.post('login', data=payload)

        # We're expecting our SID now.
        if 'sid' in self._conn._cookiejar:
            return True
        else:
            raise Exception("Login failed, bitch...")