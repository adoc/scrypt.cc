import json

start_bal = 1.0
khs_market = 0.001366

tot_khs = sum(json.loads(c.hgetall(k)[b'quant_khs'].decode()) for k in c.keys('*order_transactions:record*'))
tot_khs_value = tot_khs * khs_market


tot_orders = sum(json.loads(c.hgetall(k)[b'total_btc'].decode()) for k in c.keys('*order_transactions:record*'))

tot_mining = sum(json.loads(c.hgetall(k)[b'balance'].decode()) for k in c.keys('*mining_transactions:record*'))


balance = start_bal - tot_orders + tot_mining


showing_balance = 0.18720046

print((balance-showing_balance)/55.96506356)

print("Start Bal:       %0.8f" % start_bal)
print("Total Orders:    %0.8f" % tot_orders)
print("Total Mining:    %0.8f" % tot_mining)
print("KH/s:            %s" % tot_khs)
print("~KH/s Value:     %0.8f" % tot_khs_value)
print("Balance:         %0.8f" % balance)

print("Grand Total:     %0.8f" % (balance + tot_khs_value))


#########

Missing Order @ approx 2014-04-16 01:18:04
55.96506356 @ 0.001378BTC

raw_record = ('04/16/2014 01:18:04', 'Buy', '0.0014034983062918825', '55.96506356', '0.07714337361168566')