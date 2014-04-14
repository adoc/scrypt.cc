"""Let's track and persist transactions!"""

import sys
import time
import math
import threading
import thredis
import thredis.model
import logging
import scryptcc
import scryptcc.util
import scryptcc.mining


def process_transactions(api, records, identities):
    def do_process(timer, resync=False):
        logger = logging.getLogger('tracker.process_transactions')
        logger.debug('Executed by timer %s.' % timer)
        transaction_iter = api.all()
        i = 0
        for transaction in transaction_iter:
            timestamp = transaction['ts_epoch']

            if resync is False and identities.ismember(timestamp):
                logger.info('Reached last recorded transaction after %s iterations.' % i)
                break
            else:
                identities.add(timestamp)
                transaction['ts_created'] = math.ceil(time.time())
                logger.info('Adding transaction %s to persistance.' % transaction)
                records.set(timestamp, transaction)
                records.session.execute() # This executes the entire pipeline for this thread.
            i += 1

        # Let's just make sure...
        ident_count = identities.count()
        rec_count = len(records.session.client.keys(records.gen_key("*")))
        assert ident_count==rec_count, "identities: %s != records: %s" % (ident_count, rec_count)
    return do_process


def fire(config, resync=False):

    # Set up Redis connection.
    r_session = thredis.UnifiedSession.from_url(config.redis['url'])
    
    # Ident is the epoch timestamp of the transaction (in utc)
    r_ident = thredis.model.Set(config.redis['namespace'], 's', 'ident',
                            session=r_session)

    # The key of the hash is the epoch timestamp of the transaction.
    r_rec = thredis.model.Hash(config.redis['namespace'], 'h', 'records',
                            session=r_session)



    # Set up scrypt.cc API connection
    conn = scryptcc.Connection(config)
    mining_api = scryptcc.mining.Mining(conn)

    # Set up timer/thread.
    callback = process_transactions(mining_api, r_rec, r_ident)
    timer = scryptcc.util.RepeatingTimer(300, callback,
                pass_timer=True, halt_on_exc=True)
    callback(timer, resync=resync) # Run immediately!
    timer.start()
    timer.join()


def loadconfig(config_file):
    return scryptcc.util.Config(open(config_file, 'r'))


def main(*argv):
    fire(loadconfig(argv[1]), resync='--resync' in argv)


if __name__ == '__main__':
    main(*sys.argv)