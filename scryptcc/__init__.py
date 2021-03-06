import time
import re
import random
import logging
import requests
import bs4
import pytz

from urllib.parse import urljoin



__all__ = ('ppr', 'Connection')

logger = logging.getLogger(__name__)

CHROME_HEADER = ("""Mozilla/5.0 (Windows NT 6.1; WOW64) """
                 """AppleWebKit/537.36 (KHTML, like Gecko) """
                 """Chrome/34.0.1847.116 Safari/537.36""")

THROTTLE = 0.1

def ppr(resp, do_print=True):
    """Pretty print the URL source."""
    # resp = requests.get(url, verify=True)
    soup = bs4.BeautifulSoup(resp.text)
    if do_print is True:
        print(soup.prettify())
    else:
        return soup.prettify()


class Connection:
    # Get this from config maybe???

    def __init__(self, config={}, init_root=True, login=True):
        """
        """
        self.__tz = None
        self._cookiejar = {}
        self.config = config
        self.sid = self.config.auth.get('sid')

        if self.config.main.get('debug') is True:
            logging.basicConfig() 
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Enabled Debugging Output")

        if init_root is True:
            # This will get the '__cfduid' cookie though unsure if that is
            # required for further operation. 'sid' is the cookie that is
            # the most important.
            self.get('root')

        if not self.sid and login is True:
            self.login()

    @property
    def sid(self):
        return self._cookiejar.get('sid')

    @sid.setter
    def sid(self, val):
        self._cookiejar['sid'] = val

    @property
    def tz(self):
        if self.__tz is None:
            self.__tz = pytz.timezone(self.config.main['timezone'])
        return self.__tz

    def _get_url(self, name):
        return urljoin(self.config.main['base_url'],
                        self.config.api['uris'][name])

    def _prep_kwargs(self, **kwa):
        kwa['verify'] = True
        kwa['headers'] = kwa.get('headers', {})
        kwa['cookies'] = kwa.get('cookies', {})
        kwa['cookies'].update(self._cookiejar)
        return kwa

    def _update_cookies(self, resp):
        self._cookiejar.update(requests.utils.dict_from_cookiejar(resp.cookies))
        # Lets go through all the history as well.
        for history in resp.history:
            self._cookiejar.update(
                requests.utils.dict_from_cookiejar(history.cookies))

    def get(self, name, **kwa):
        kwa = self._prep_kwargs(**kwa)
        url = self._get_url(name)
        kwa['headers']['user-agent'] = CHROME_HEADER
        time.sleep(THROTTLE) # This won't do shit once async
        resp = requests.get(url, **kwa)
        self._update_cookies(resp)
        return resp

    def post(self, name, **kwa):
        kwa = self._prep_kwargs(**kwa)
        url = self._get_url(name)
        kwa['headers']['referer'] = url # This might not always be the case...
        kwa['headers']['origin'] = self.config.main['base_url']
        kwa['headers']['content-type'] = 'application/x-www-form-urlencoded'
        kwa['headers']['user-agent'] = CHROME_HEADER
        time.sleep(THROTTLE) # This won't do shit once async
        resp = requests.post(url, **kwa)
        self._update_cookies(resp)
        return resp

    def login(self, user=None, passw=None):
        if user is None or passw is None:
            user = self.config.auth.get('user')
            passw = self.config.auth.get('pass')

        if user is None or passw is None:
            raise Exception("We have no way to authenticate.")

        payload = {'action': '1',
                   'username': user,
                   'password': passw,
                   'submit': 'Login'}
        print(payload)
        resp = self.post('login', data=payload)

        # We're expecting our SID now.
        if self.sid:
            return True
        else:
            raise Exception("Login failed...")

    def api(self, method, **kwa):
        """Pepare and execute user API call to Scrypt."""
        kwa['params'] = kwa.get('params', {})
        kwa['params'].update(self.config.api_methods[method])
        
        kwa['params']['r'] = random.random()
        kwa['headers'] = kwa.get('headers', {})
        kwa['headers']['referer'] = self._get_url('home')
        kwa['headers']['x-requested-with'] = 'XMLHttpRequest'

        return self.get('api', **kwa)


class Subsection:
    """All API sub-sections will subclass from this. (Mining, Tracking, etc.)"""
    pagecount_pattern = re.compile(r'(\d+)\[\]')

    def __init__(self, connection):
        self._c = connection

    def _get_pagecount(self, body):
        """
        Returns tuple of (pagecount, stripped_body)
        """
        match = self.pagecount_pattern.match(body)
        if match:
            pagecount = match.groups()[0]
        else:
            raise Exception("API did not respond with a pagecount.")
        return (int(pagecount), body[match.end():])