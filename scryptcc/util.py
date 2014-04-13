"""
"""
import configparser

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
    main = {'base_url': '',
            'debug': False,
            'tzoffset': ''}
    auth = {'sid': '',
            'user': '',
            'pass': ''}
    api = {'uris': {}}
    api_methods = {'*': {}}

    def __init__(self, raw_config):
        self._raw_config = raw_config
        self._parse_config()

    def _parse_config(self):
        config = configparser.ConfigParser()
        config.read_string(self._raw_config)
        
        for section in config.sections():
            if hasattr(self, section):
                section_attr = getattr(self, section)
                section = config[section]

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