import re
import math
import time
import datetime
import bs4
import pytz
import scryptcc



# http://stackoverflow.com/a/947789
non_decimal = lambda v: re.sub(r'[^\d.]+', '', v)


class Mining(scryptcc.Subsection):
    """Mining API Wrapper. (Mining Transasctions)"""

    @staticmethod
    def timestamp(d):
        return datetime.datetime.strptime(d, Mining.datetime_pattern)

    datetime_pattern = '%Y-%m-%d %H:%M:%S'
    columns = {'datetime': timestamp.__func__,
                'type': str,
                'balance': float,
                'comment': str}
    columns_order = ('datetime', 'type', 'balance', 'comment')
    record_demarc = """<div id="b3"></div>"""

    def _transactions(self, **kwa):
        params = {}
        params['p'] = kwa.get('page', '1')

        response = self._c.api('mining_transactions', params=params)
        pagecount, body = self._get_pagecount(response.text)

        records_html = body.split(self.record_demarc)

        # This can be a method on the class.
        def breakout_record(record):
            
            soup = bs4.BeautifulSoup(record)
            for k, v in zip(self.columns_order, soup.children):
                type_ = self.columns[k]
                if type_ is float:
                    val = type_(non_decimal(v.string))
                    yield (k, val)
                elif type_ is Mining.timestamp:
                    dt = type_(v.string)
                    ldt = self._c.tz.localize(dt) # Localize the timestamp to the known timezone.
                    utc = (ldt-ldt.utcoffset()).replace(tzinfo=pytz.utc) # Get and localize the UTC.
                    yield 'ts_raw', v.string # String received from scryptcc.
                    yield 'ts_localized', ldt # Localized datetime.
                    yield 'ts_epoch', math.ceil(utc.timestamp())
                    yield 'ts_utc', utc
                else:
                    val = type_(v.string)
                    yield k, val

        for record in records_html:
            rec_dict = dict(breakout_record(record))
            if rec_dict:
                yield pagecount, rec_dict

    def all(self, **kwa):
        # Get first page of transactions along with count.
        for count, transaction in self._transactions(**kwa):
            yield transaction

        for p in range(2,count+1):
            kwa['page'] = p
            for count, transaction in self._transactions(**kwa):
                yield transaction