"""
"""
import io
import configparser
import threading

# =============================================================================
# Source: paste.deploy.converters
# Notes: Changed `basestring` usage to `str` (Py 2 -> 3)
# -------------------------------
# (c) 2005 Ian Bicking and contributors; written for Paste
#   (http://pythonpaste.org)
# Licensed under the MIT license:
#   http://www.opensource.org/licenses/mit-license.php

def asbool(obj):
    if isinstance(obj, str):
        obj = obj.strip().lower()
        if obj in ['true', 'yes', 'on', 'y', 't', '1']:
            return True
        elif obj in ['false', 'no', 'off', 'n', 'f', '0']:
            return False
        else:
            raise ValueError("String is not true/false: %r" % obj)
    return bool(obj)


def asint(obj):
    try:
        return int(obj)
    except (TypeError, ValueError):
        raise ValueError("Bad integer value: %r" % obj)


def aslist(obj, sep=None, strip=True):
    if isinstance(obj, str):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return obj
    elif obj is None:
        return []
    else:
        return [obj]
# =============================================================================


# Source: codalib.paste.converters
# Where is this in the django code?? Or did I write this??
# This should be recursive
def asdict(obj, expect_lists = True, list_sep = ','):
    """Simple Dictionary Converter using the Django method.
    **There are error and assert cases that should be included in this method."""

    if isinstance(obj, str):
        def split_object():
            for item in obj.split('\n'):
                try:
                    key, val = item.split('=')
                except ValueError:
                    # Why just pass??
                    pass
                else:
                    key, val = key.strip(), val.strip()

                    if list_sep in val and expect_lists:
                        val = aslist(val, sep=list_sep)
                        val = filter(None, val)

                    yield key, val

        return {k:v for k, v in split_object()}

def asdict(obj, expect_lists = True, list_sep = ','):
    """Simple Dictionary Converter using the Django method.
    **There are error and assert cases that should be included in this method."""

    if isinstance(obj, str):
        def split_object():
            for item in obj.split('\n'):
                try:
                    key, val = item.split('=')
                except ValueError:
                    # Bad or empty line, just pass for now.
                    pass
                else:
                    key, val = key.strip(), val.strip()
                    if list_sep in val and expect_lists:
                        val = aslist(val, sep=list_sep)
                        val = filter(None, val)

                    yield key, val
        return {k:v for k, v in split_object()}


class Config:
    """Wierd config class that uses class attributes for type/default
    when retrieving from configparser.
    """
    #TODO: Perhaps instead of using the class attrs, maybe use a dict
    #   for clarity.

    main = {'base_url': '',
            'debug': False,
            'timezone': ''}
    auth = {'sid': '',
            'user': '',
            'pass': ''}
    api = {'uris': {}}
    api_methods = {'*': {}}
    redis = {'url': '',
             'namespace': '',
             'user': '',
             'pass': ''}

    def __init__(self, raw_config):
        self.__parsed = None
        self.__raw_config = raw_config
        self._parse_config()

    @property
    def config(self):
        """Returns previously parsed config or parses the `raw_config`
        if it's a string or file.
        """
        if self.__parsed is not None:
            return self.__parsed
        elif isinstance(self.__raw_config, io.IOBase):
            attr = 'readfp'
        elif isinstance(self.__raw_config, str):
            attr = 'read_string'
        else:
            raise Exception("Expected the raw config to be a file or a string.")
        self.__parsed = configparser.ConfigParser()
        read = getattr(self.__parsed, attr) # Get read or read_string
        read(self.__raw_config)
        return self.__parsed

    def _parse_config(self):
        for section in self.config.sections():
            if hasattr(self, section):
                section_attr = getattr(self, section)
                section = self.config[section]

                for item_key, item_val in section.items():
                    # Attempt to get the item, otherwise check for a '*'
                    # key.
                    item_attr = section_attr.get(item_key,
                                section_attr.get('*', ''))
                    value = section.get(item_key, type(item_attr)())

                    if isinstance(item_attr, dict):
                        section_attr[item_key] = asdict(value)
                    elif isinstance(item_attr, bool):
                        section_attr[item_key] = asbool(value)
                    elif isinstance(item_attr, int):
                        section_attr[item_key] = asint(value)
                    elif isinstance(item_attr, list):
                        section_attr[item_key] = aslist(value)
                    else:
                        section_attr[item_key] = value.strip()
            else:
                raise Exception("Encountered invalid section %s." % (section))



# Source: codalib.procs
class KillableThread(threading.Thread):
    """Subclass of threading.Thread with kill signal functionality.
    """

    def __init__(self, *args, **kwa):
        """Constructs a KillableThread object."""
        threading.Thread.__init__(self, *args, **kwa)
        self.__kill_event = threading.Event()

    def kill(self):
        """Sets kill signal for the thread.
        """
        self.__kill_event.set()

    def __iskilled(self):
        return self.__kill_event.isSet()

    @property
    def iskilled(self):
        """Returns True if this thread has been sent a kill signal.
        """
        return self.__iskilled()


class RepeatingTimer(KillableThread):
    """Simple repeating timer.

    param:pass_timer - pass Timer instance to the callback.
    """

    def __init__(self, interval, callback, pass_timer=False, halt_on_exc=False):
        KillableThread.__init__(self)
        self.__interval = interval
        self.__callback = callback
        self.__pass_timer = pass_timer
        self.__halt_on_exc = halt_on_exc

    # Protected props.
    @property
    def interval(self):
        return self.__interval

    @property
    def pass_timer(self):
        return self.__pass_timer

    @property
    def halt_on_exc(self):
        return self.__halt_on_exc

    def callback(self):
        try:
            if self.pass_timer is True:
                return self.__callback(self)
            else:
                return self.__callback()
        except:
            if self.halt_on_exc:
                self.cancel()
            raise

    def run(self):
        while self.iskilled is not True:
            timer = threading.Timer(self.interval, self.callback)
            timer.start()
            timer.join()
            # Don't forget to join() in future implementations! (???)

    def cancel(self):
        self.kill()