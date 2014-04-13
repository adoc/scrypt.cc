from urllib.parse import urljoin
import random
import requests

from bs4 import BeautifulSoup


__all__ = ('ppr', 'Scryptcc')


CHROME_HEADER = ("""Mozilla/5.0 (Windows NT 6.1; WOW64) """
                 """AppleWebKit/537.36 (KHTML, like Gecko) """
                 """Chrome/34.0.1847.116 Safari/537.36""")


def ppr(resp, do_print=True):
    """Pretty print the URL source."""
    # resp = requests.get(url, verify=True)
    soup = BeautifulSoup(resp.text)
    if do_print is True:
        print(soup.prettify())
    else:
        return soup.prettify()


class Base:
    base_url = 'https://scrypt.cc'

    uris = {'root': '/',
            'login': 'login.php',
            'users': '/users/index.php',
            'api': '/users/api.php'}

    api_methods = {'mining': {'method':'4', 'c': 'm'}}

    def __init__(self, sid=None, cookiejar = {}):
        self.sid = sid
        self._cookiejar = cookiejar
        # Get initial uid cookie.
        self.get('root')

    @property
    def sid(self):
        return self._cookiejar.get('sid')

    @sid.setter
    def sid(self, val):
        self._cookiejar['sid'] = val

    def _get_url(self, name):
        return urljoin(self.base_url, self.uris[name])

    def _prep_kwargs(self, **kwa):
        kwa['verify'] = True
        kwa['headers'] = kwa.get('headers', {})
        kwa['cookies'] = kwa.get('cookies', {})
        kwa['cookies'].update(self._cookiejar)
        return kwa

    def _update_cookies(self, resp):
        self._cookiejar.update(requests.utils.dict_from_cookiejar(resp.cookies))
        # But lets go through all the history.
        for history in resp.history:
            self._cookiejar.update(
                requests.utils.dict_from_cookiejar(history.cookies))

    def get(self, name, **kwa):
        kwa = self._prep_kwargs(**kwa)
        url = self._get_url(name)
        kwa['headers']['user-agent'] = CHROME_HEADER
        resp = requests.get(url, **kwa)
        self._update_cookies(resp)
        return resp

    def post(self, name, **kwa):
        kwa = self._prep_kwargs(**kwa)
        url = self._get_url(name)
        kwa['headers']['referer'] = url # This might not always be the case...
        kwa['headers']['origin'] = self.base_url
        kwa['headers']['content-type'] = 'application/x-www-form-urlencoded'
        kwa['headers']['user-agent'] = CHROME_HEADER
        resp = requests.post(url, **kwa)
        self._update_cookies(resp)
        return resp

    def api(self, method, **kwa):
        """Pepare and execute user API call to Scrypt."""
        kwa['params'] = kwa.get('params', {})
        kwa['params'].update(self.api_methods[method])
        
        kwa['params']['p'] = kwa.get('p', '1')
        if 'p' in kwa: del kwa['p']
        
        kwa['params']['r'] = random.random()
        kwa['headers'] = kwa.get('headers', {})
        kwa['headers']['referer'] = self._get_url('users')
        kwa['headers']['x-requested-with'] = 'XMLHttpRequest'

        return self.get('api', **kwa)