import datetime
import re
import bs4
import scryptcc


# http://stackoverflow.com/a/947789
non_decimal = lambda v: re.sub(r'[^\d.]+', '', v)


class Mining(scryptcc.Subsection):
    """Mining API Wrapper. (Mining Transasctions)"""

    @staticmethod
    def timestamp(d):
        return datetime.datetime.strptime(d, Mining.datetime_pattern)

    datetime_pattern = '%Y-%m-%d %H:%M:%S %z'
    columns = {'timestamp': timestamp.__func__,
                'type': str,
                'balance': float,
                'comment': str}
    columns_order = ('timestamp', 'type', 'balance', 'comment')
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
                    val = type_(v.string+' '+
                                    self._c.config.main.get('tzoffset', '+0000'))
                    yield 'raw_datetime', v.string
                    yield k, val
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