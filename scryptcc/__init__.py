import re
import time
import threading
import collections
import math
import random
import datetime
import logging
import configparser
import urllib.parse
import requests
import bs4
import pytz
import scryptcc.util

__all__ = ('ppr', 'Section', 'Config', 'Connection')


logger = logging.getLogger(__name__)

# Unfortunately we have to pretend to be Chrome. :(
CHROME_HEADER = ("""Mozilla/5.0 (Windows NT 6.1; WOW64) """
                 """AppleWebKit/537.36 (KHTML, like Gecko) """
                 """Chrome/34.0.1847.116 Safari/537.36""")

THROTTLE = 0.1


# http://stackoverflow.com/a/947789
_non_decimal_pattern = re.compile(r'[^\d.]+')
non_decimal = lambda v: _non_decimal_pattern.sub('', v)


def ppr(body, do_print=True):
    """Pretty print or return a response body. Mainly used for debug or
    adding new API methods.
    """
    soup = bs4.BeautifulSoup(body)
    if do_print is True:
        print(soup.prettify())
    else:
        return soup.prettify()


def Regex(regex):
    """Pseudo-type"""
    return re.compile(regex)


def timestamp(self, dt):
    return datetime.datetime.strptime(dt,
                self.local_config['datetime_pattern'])

# Expected Config sections, params and types.
CONFIG_SECTIONS = {
        'main': {
            'base_url': str,
            'timezone': str,
            'debug': bool,
            'logging': str
        },
        'persistence': {
            'url': str,
            'namespace': str
        },
        'auth': {
            'sid': str,
            'user': str,
            'pass': str
        },
        'uris': {
            'login': str,
            'home': str,
            'api': str
        },
        'api_defaults': {
            'pagecount_pattern': Regex,
            'record_demarc': str,
            'datetime_pattern': str,
            'tracking_interval': int,
            'post_params': dict,
            'get_params': dict,
            'columns': dict,
        },
        'login_api': {
            'post_params': dict
        }
    }

CONFIG_SECTIONS['orders_api'] = CONFIG_SECTIONS['mining_api'] = CONFIG_SECTIONS['api_defaults']


class Config:
    """Wierd configurator."""

    __parser__ = configparser.RawConfigParser

    def __init__(self, parser_config, template=CONFIG_SECTIONS):
        # Expects a ConfigParser instance.
        assert isinstance(parser_config, self.__parser__), \
            "Expected `config` to be a ConfigParser object."
        self.__parsed = self.parse_config(parser_config, template)

    @classmethod
    def from_fp(cls, fp, **kwa):
        config = cls.__parser__()
        config.readfp(fp)
        return cls(config, **kwa).parsed

    @classmethod
    def from_fn(cls, fn, **kwa):
        config = cls.__parser__()
        config.read(fn)
        return cls(config, **kwa).parsed

    @classmethod
    def from_string(cls, string, **kwa):
        config = cls.__parser__()
        config.read_string(string).parsed
        return cls(config, **kwa)

    @property
    def parsed(self):
        return self.__parsed

    @staticmethod
    def parse_config(parser_config, template):
        zdict = collections.OrderedDict
        def breakout_section(section):
            for item_key, item_val in parser_config[section].items():
                item_type = template[section][item_key]
                value = parser_config[section][item_key].strip()

                if item_type is dict and item_key=='columns':
                    eval_whitelist = ('timestamp', 'str', 'bool', 'int',
                                      'float', 'dict')
                    items = scryptcc.util.asdict(value, dict_type=zdict).items()
                    yield (item_key, zdict(
                            (k, eval(v)) for k, v in items
                                if v in eval_whitelist))
                elif item_type is dict:
                    yield item_key, scryptcc.util.asdict(value)
                elif item_type is bool:
                    yield item_key, scryptcc.util.asbool(value)
                elif item_type is int:
                    yield item_key, scryptcc.util.asint(value)
                elif item_type is list:
                    yield item_key, scryptcc.util.aslist(value)
                elif item_type is scryptcc.Regex:
                    yield item_key, Regex(value)
                elif item_type is str:
                    yield item_key, value
                else:
                    raise Exception("Section %s Key %s with unknown type "
                                    "%s." % (section, item_key, item_type))

        def breakout_config(parser_config):
            for section in parser_config.sections():
                try:
                    sec_dict = dict(breakout_section(section))

                    yield section, sec_dict
                except KeyError:
                    raise KeyError("Encountered section %s not in template." %
                                   (section))

        return dict(breakout_config(parser_config))


class Connection:
    """ """
    def __init__(self, config, init_root=False, login=False, debug=False):
        """
        """
        self.__config = config
        self.__tz = None
        self.__cookiejar = {}
        self.__debug =  debug or self.config['main'].get('debug', False)

        self.sid = self.config['auth'].get('sid')

        if init_root is True:
            # This will get the '__cfduid' cookie though unsure if that is
            # required for further operation. 'sid' is the cookie that is
            # the most important.
            self.get('root')

        if not self.sid and login is True:
            self.login()

    # Protected props.
    @property
    def config(self):
        return self.__config

    @property
    def debug(self):
        return self.__debug

    @property
    def sid(self):
        return self.__cookiejar.get('sid')

    @sid.setter
    def sid(self, val):
        self.__cookiejar['sid'] = val

    @property
    def tz(self):
        if self.__tz is None:
            self.__tz = pytz.timezone(self.config['main']['timezone'])
        return self.__tz

    def _gen_url(self, name):
        return urllib.parse.urljoin(self.config['main']['base_url'],
                        self.config['uris'][name])

    def _prep_kwargs(self, **kwa):
        kwa['verify'] = True
        kwa['headers'] = kwa.get('headers', {})
        kwa['cookies'] = kwa.get('cookies', {})
        kwa['cookies'].update(self.__cookiejar)
        return kwa

    def _update_cookies(self, response):
        request_cookies = requests.utils.dict_from_cookiejar(response.cookies)
        logger.debug("Update cookiejar from request cookies: %s" % request_cookies)
        self.__cookiejar.update(request_cookies)
        # Lets go through all the history as well and handle cookies set on
        # redirects.
        for history in response.history:
            history_cookies = requests.utils.dict_from_cookiejar(history.cookies)
            logger.debug("Update cookiejar from historical cookies: %s" % history_cookies)
            self.__cookiejar.update(history_cookies)

    def get(self, uri_name, **kwa):
        """Get one of the configured "uris"."""
        kwa = self._prep_kwargs(**kwa)
        url = self._gen_url(uri_name)
        kwa['headers']['referer'] = self.config['main']['base_url']
        kwa['headers']['origin'] = self.config['main']['base_url']
        kwa['headers']['user-agent'] = CHROME_HEADER
        time.sleep(THROTTLE) # Just a debug precaution so we don't slam Scrypt.
                             # This won't do anything once async.
        response = requests.get(url, **kwa)
        self._update_cookies(response)
        return response

    def post(self, name, **kwa):
        kwa = self._prep_kwargs(**kwa)
        url = self._gen_url(name)
        kwa['headers']['referer'] = url # Usually posts are from it self.
        kwa['headers']['origin'] = self.config['main']['base_url']
        kwa['headers']['content-type'] = 'application/x-www-form-urlencoded'
        kwa['headers']['user-agent'] = CHROME_HEADER
        time.sleep(THROTTLE) # Just a debug precaution so we don't slam Scrypt.
                             # This won't do anything once async.
        response = requests.post(url, **kwa)
        self._update_cookies(response)
        return response

    def login(self, user=None, passw=None):
        if user is None or passw is None:
            user = self.config['auth'].get('user')
            passw = self.config['auth'].get('pass')

        if user is None or passw is None:
            raise Exception("We have no way to authenticate.")

        payload = {'action': '1',
                   'username': user,
                   'password': passw,
                   'submit': 'Login'}

        response = self.post('login', data=payload)

        if self.sid: # We're expecting our SID now.
            return True
        else:
            raise Exception("Login failed...")


class Section(Connection):
    """All API sections"""

    __sections__ = ('mining_api', 'orders_api')

    def __init__(self, section, *args, **kwa):
        Connection.__init__(self, *args, **kwa)
        if section not in self.__sections__:
            raise Exception("`section` must be one of %s." % self.__sections__)
        self.__section = section

    # Protected Props.
    @property
    def section(self):
        return self.__section

    @property
    def local_config(self):
        _c = {}
        _c.update(self.config['api_defaults']) # Apply API defaults.
        _c.update(self.config[self.section]) # Get section config.
        return _c

    @property
    def columns(self):
        return self.local_config['columns']

    @property
    def get_params(self):
        return self.local_config['get_params']

    @property
    def post_params(self):
        return self.local_config['post_params']

    def _parse_pagecount(self, body):
        """
        Returns tuple of (pagecount, stripped_body)
        """
        match = self.local_config['pagecount_pattern'].match(body)
        if match:
            pagecount = match.groups()[0]
        else:
            raise Exception("API did not respond with a pagecount.")
        return (int(pagecount), body[match.end():])

    def _breakout_record(self, parsed_columns):
        """Breaks in to a single "record" line from the Scrypt.cc API.
        Parse values in to expected data types based on `columns`
        attribute and yield the key/value pairs.
        """
        # This is an ordereddict, so keys should be ordered.
        for k, v in zip(self.columns.keys(), parsed_columns):
            type_ = self.columns[k]
            if type_ is float:
                val = type_(non_decimal(v))
                yield k, val
            elif type_ is timestamp:
                dt = type_(self, v)
                # This can be slow if PYTZ is in a zipped egg.
                ldt = self.tz.localize(dt) # Localize the timestamp to the known timezone.
                utc = (ldt-ldt.utcoffset()).replace(tzinfo=pytz.utc) # Get and localize the UTC.
                yield 'ts_raw', v # String received from scryptcc.
                yield 'ts_localized', ldt # Localized datetime.
                yield 'ts_epoch', math.ceil(utc.timestamp())
                yield 'ts_utc', utc
            else:
                val = type_(v)
                yield k, val

    def _transactions(self, **kwa):
        params = {}
        params['p'] = kwa.get('page', '1')
        response = self.api(params=params)
        pagecount, body = self._parse_pagecount(response.text)
        records_html = body.split(self.local_config['record_demarc'])
        # Iterate and break out the records.
        for record in records_html:
            soup = bs4.BeautifulSoup(record)
            rec_dict = dict(
                            self._breakout_record(
                                tuple(v.string for v in soup.children)))
            if rec_dict:
                yield pagecount, rec_dict

    def api(self, **kwa):
        """Pepare and execute an API Request.
        """
        kwa['params'] = kwa.get('params', {})
        kwa['params'].update(self.get_params) # Get params from config.
        kwa['params']['r'] = random.random() # Backend probably doesn't check
                                             # this, and we're not caching,
                                             # but let's do it anyway.
        kwa['headers'] = kwa.get('headers', {})
        kwa['headers']['referer'] = self._gen_url('home')
        kwa['headers']['x-requested-with'] = 'XMLHttpRequest' # Lies!
        return self.get('api', **kwa)

    def all(self, **kwa):
        # Get first page of transactions along with count.
        for count, transaction in self._transactions(**kwa):
            yield transaction

        for p in range(2,count+1):
            kwa['page'] = p
            for count, transaction in self._transactions(**kwa):
                yield transaction