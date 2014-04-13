import re
from bs4 import BeautifulSoup

class Subsection:
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
        return (pagecount, body[match.end():])


import datetime

# http://stackoverflow.com/a/947789
non_decimal = lambda v: re.sub(r'[^\d.]+', '', v)

import functools



class Mining(Subsection):

    datetime_pattern = '%Y-%m-%d %H:%M:%S %z'

    @staticmethod
    def timestamp(d):
        return datetime.datetime.strptime(d, Mining.datetime_pattern)

    columns = {'timestamp': timestamp.__func__,
                'type': str,
                'balance': float,
                'comment': str}
    columns_order = ('timestamp', 'type', 'balance', 'comment')
    record_demarc = """<div id="b3"></div>"""

    # We're calling this "class" here, but currently scrypt.cc uses "id"
    # incorrectly.
    html_class_map = {}

    def _transactions(self, **kwa):
        params = {}
        params['p'] = kwa.get('page', '1')

        response = self._c.api('mining_transactions', params=params)
        pagecount, body = self._get_pagecount(response.text)

        records_html = body.split(self.record_demarc)

        def breakout_record(record):
            soup = BeautifulSoup(record)
            for k, v in zip(self.columns_order, soup.children):
                type_ = self.columns[k]
                if type_ is float:
                    val = type_(non_decimal(v.string))
                    yield (k, val)
                elif type_ is Mining.timestamp:
                    val = type_(v.string+' '+self._c.config.main.get('tzoffset', '+0000'))
                    yield ('raw_timestamp', v.string)
                    yield (k, val)
                else:
                    val = type_(v.string)
                    yield (k, val)

        def parse_records():
            for record in records_html:
                yield dict(breakout_record(record))

        print(list(parse_records()))


        #    yield {k: v.string for k,v in zip(self.columns.keys, soup.children)}



