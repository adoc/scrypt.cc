"""Just some general utils for use by `scryptcc`.

* All from other libraries with citations.
"""

__all__ = ('asbool', 'asint', 'aslist', 'asdict', 'RepeatingTimer',
            'PosixFlushStdin')




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
# Where is this in the django code?? Can't find it.
# Or did I write this mess??
def asdict(obj, expect_lists = True, list_sep = ',', dict_type=dict):
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
        return dict_type((k, v) for k, v in split_object())


import time
import threading


THROTTLE = 0.01


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
        self.__timer = None

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
        # Note: Instead of joining the timer, we handle our own loop
        #   that watches it.
        while self.iskilled is not True:
            if self.__timer is None or self.__timer.is_alive() is False:
                self.__timer = threading.Timer(self.interval, self.callback)
                self.__timer.start()
            time.sleep(THROTTLE)

    def cancel(self):
        if self.__timer is not None:
            self.__timer.cancel()
        self.kill()


import os
import sys
import fcntl
import termios


class PosixFlushStdin:
    """
    Refactored version of the original. (Credit to original author.)
    https://docs.python.org/2/faq/library.html#how-do-i-get-a-single-keypress-at-a-time
    """
    def __init__(self, ):
        self.__fd = sys.stdin.fileno()
        self.__oldterm = termios.tcgetattr(self.__fd)

    def flush(self):
        newattr = termios.tcgetattr(self.__fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(self.__fd, termios.TCSANOW, newattr)
        self.__oldflags = fcntl.fcntl(self.__fd, fcntl.F_GETFL)
        fcntl.fcntl(self.__fd, fcntl.F_SETFL, self.__oldflags | os.O_NONBLOCK)

    def block(self):
        termios.tcsetattr(self.__fd, termios.TCSAFLUSH, self.__oldterm)
        fcntl.fcntl(self.__fd, fcntl.F_SETFL, self.__oldflags)