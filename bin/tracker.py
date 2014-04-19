"""Let's track and persist transactions!"""

# TODO:
#   Synchronize the timer with the last record gotten!

import sys
import time
import math
import threading
import thredis
import thredis.model
import logging
import scryptcc
import scryptcc.util

# To BTC.
SATOSHIO = 100000000
uBTC = 1000000
mBTC = 1000





def process_transactions(api, records, identities):
    def do_process(timer, resync=False):
        logger = logging.getLogger('tracker.process_transactions')
        logger.info('Checking API...')
        logger.debug('Executed by timer %s.' % timer)

        try:
            transaction_iter = api.all()
            i = 0
            for transaction in transaction_iter:
                timestamp = transaction['ts_epoch']

                if resync is False and identities.ismember(timestamp):
                    logger.info('No new records...')
                    logger.debug('Reached last recorded transaction after %s iterations.' % i)
                    break
                else:
                    identities.add(timestamp)
                    transaction['ts_created'] = math.ceil(time.time())

                    if api.section == 'mining_api':
                        logger.warn('Processing MINING transaction that occured at %s '
                            '(%s satoshis).' % (
                                transaction['ts_utc'].strftime('%Y-%m-%d %H:%M:%S %Z'),
                                int(transaction['balance']*SATOSHIO)))
                    elif api.section == 'orders_api':
                        logger.warn('Processing %s ORDER transaction that occured at %s '
                            '(%0.6fBTC x %sKHS = %0.6fBTC Total).' % (
                                transaction['type'],
                                transaction['ts_utc'].strftime('%Y-%m-%d %H:%M:%S %Z'),
                                transaction['unit_btc'],
                                transaction['quant_khs'],
                                transaction['total_btc']))
                    logger.debug('Adding transaction %s to persistance.' % transaction)
                    records.set(timestamp, transaction)
                    records.session.execute() # This executes the entire pipeline for this thread.
                i += 1

            # Let's just make sure... Maybe only if debug??
            ident_count = identities.count()
            rec_count = len(records.session.client.keys(records.gen_key("*")))
            assert ident_count==rec_count, "identities: %s != records: %s" % (ident_count, rec_count)
        finally:
            logger.warn('Press (Q) to end.')
    return do_process


class Fire:
    def __init__(self, config, resync=False):
        self.__resync = resync
        self.__config = config


def _do(session, namespace, resync=False):
    # Set up mining transactions.
    # The key of the hash is the epoch timestamp of the transaction.
    records = thredis.model.Hash(config['persistence']['namespace'], 'h',
            'mining_transactions','record', session=r_session)
    # Ident is the epoch timestamp of the transaction (in utc)
    ident = thredis.model.Set(config['persistence']['namespace'], 's',
            'mining_transactions','ident', session=r_session)
    # Set up scrypt.cc API connection
    api = scryptcc.Section('mining_api', config=config)
    return process_transactions(api, records, ident)


def fire(config, resync=False):
    # Set up Redis connection.
    r_session = thredis.UnifiedSession.from_url(config['persistence']['url'])
    
    # Set up mining transactions.
    # The key of the hash is the epoch timestamp of the transaction.
    r_rec = thredis.model.Hash(config['persistence']['namespace'], 'h',
            'mining_transactions','record', session=r_session)
    # Ident is the epoch timestamp of the transaction (in utc)
    r_ident = thredis.model.Set(config['persistence']['namespace'], 's',
            'mining_transactions','ident', session=r_session)
    # Set up scrypt.cc API connection
    mining_api = scryptcc.Section('mining_api', config=config)
    mining_callback = process_transactions(mining_api, r_rec, r_ident)

    #Set up order transactions.
    r_rec = thredis.model.Hash(config['persistence']['namespace'], 'h',
            'order_transactions','record', session=r_session)
    r_ident = thredis.model.Set(config['persistence']['namespace'], 's',
            'order_transactions','ident', session=r_session)
    orders_api = scryptcc.Section('orders_api', config=config)
    orders_callback = process_transactions(orders_api, r_rec, r_ident)

    # Set up timer/thread.
    
    mining_timer = scryptcc.util.RepeatingTimer(600, mining_callback,
                pass_timer=True, halt_on_exc=True)
    orders_timer = scryptcc.util.RepeatingTimer(600, orders_callback,
                pass_timer=True, halt_on_exc=True)

    mining_callback(mining_timer, resync=resync) # Run immediately!
    orders_callback(orders_timer, resync=resync)

    mining_timer.start()
    orders_timer.start()

    loop(mining_timer, orders_timer) # Instead of joining, we run our own loop.


def loop(*timers):
    # src: https://docs.python.org/2/faq/library.html#how-do-i-get-a-single-keypress-at-a-time
    # Most of this is just who-knows-what since "fcntl" scares me a lot. :D
    import termios, fcntl, sys, os
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    try:
        while timers[0].iskilled is False:
            try:
                c = sys.stdin.read(1)
                if c.lower() == 'q':
                    logging.warn("Exiting upon request...")
                    logging.debug("Canceling API timer.")
                    for timer in timers:
                        timer.cancel()
            except IOError: pass
            # Throttle the loop.
            time.sleep(0.2)
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


def setuplogging(config):
    levels = ('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL')
    logging.basicConfig()
    logging_level = config['main'].get('logging', 'WARN').upper()
    assert logging_level in levels, \
        "Only 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL' accepted for logging levels."

    level = getattr(logging, logging_level, 'WARN')

    logging.getLogger().setLevel(level)

    if logging_level is 'DEBUG':
        logger.debug("Enabled Debugging Output")


def main(*argv):
    config = scryptcc.Config.from_fn(argv[1])
    setuplogging(config)
    
    fire(config, resync='--resync' in argv)


if __name__ == '__main__':
    main(*sys.argv)