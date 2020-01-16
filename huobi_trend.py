"""
自动交易流程
 
通过while语句，不断的循环。每次循环中需要做的操作步骤
1. 用ccxt连接huobi交易所
2. 获取历史数据，并转换成指定格式
3. 完成交易策略的编写，回测
4. 更新账户信息
5. 获取实时数据
6. 根据最新数据计算买卖信号 
7. 根据目前仓位、买卖信息，结束本次循环，或者进行交易
8. 交易

huobi杠杆规则：
1、利息按日结算，即使只借了5分钟，也按照一天来收利息

"""

import ccxt
import time
import datetime
import pandas as pd
import logging
from Trade import next_run_time, get_exchange_candle_data, place_order, send_dingding_msg
from Signals import signal_swing, signal_trend, real_time_signal_swing, real_time_signal_trend
pd.set_option('expand_frame_repr', False)   # 不换行
pd.set_option('display.max_rows', 10)      # 显示的最大行数


# 主程序
def main():
    chicang = 0             # 持仓标识-1，0，1
    chicang_amount = 0      # 持仓数量
    while True:
        # 参数
        exchange = ccxt.huobipro()      # 创建交易所
        exchange.apiKey = ''
        exchange.secret = ''
        exchange.load_markets()

        symbol = 'ETH/USDT'      # 交易品种
        base_coin = symbol.split('/')[-1]       # 基础货币
        trade_coin = symbol.split('/')[0]       # 交易货币

        strategy = real_time_signal_trend         # 策略名称
        strategy2 = 'real_time_signal_trend'      # 策略名称
        para = [20, 6, 20, 2, 2, 50]             # 策略参数
        time_interval = '1m'    # 运行间隔时间

        # 第一步：更新账户信息      成功
        while True:
            try:
                balance = exchange.fetch_balance()    # 获取普通exchange交易账户数据
                # print(balance)
                break
            except:
                continue
        base_coin_amount = float(balance[base_coin]['total'])
        trade_coin_amount = float(balance[trade_coin]['total'])
        print('当前资产:\n', base_coin, base_coin_amount, trade_coin, trade_coin_amount)    # 也就相当于现货账户的持仓
        for i in exchange.fetch_accounts():
            if i['type'] == 'spot':             # 现货账户号
                spot_id = i['id']
            if i['type'] == 'super-margin':           # 杠杆账户号
                margin_id = i['id']
        balance_margin = exchange.fetch_balance({'id':margin_id})
        
        total_btc = balance_margin['total']['BTC']          # BTC总量
        total_usdt = balance_margin['total']['USDT']        # USDT总量
        use_btc = balance_margin['used']['BTC']             # BTC已用数量
        use_usdt = balance_margin['used']['USDT']           # USDT已用数量
        free_btc = balance_margin['free']['BTC']            # BTC可用数量
        free_usdt = balance_margin['free']['USDT']          # USDT可用数量
        
        # 第二步：获取实时数据
        # sleep直到运行时间
        run_time = next_run_time(time_interval)
        print('睡眠:',((run_time - datetime.datetime.now()).seconds),'秒')
        time.sleep(max(0, (run_time - datetime.datetime.now()).seconds))      # 若sleep时间小于0，则会报错，这里是为了不报错
        # 这个方法非常经典
        while True:
            if datetime.datetime.now() < run_time:
                continue
            else:
                break

        # 获取实时数据
        n = 0
        while True:
            df = get_exchange_candle_data(exchange, symbol, time_interval)
            # 判断是否包含最新的数据
            _temp = df[df['candle_begin_time_GTM8'] == (run_time-datetime.timedelta(minutes=int(time_interval.strip('m'))))]     # 因为当前时间的K线的开始时间是time_interval分钟之前  
            if _temp.empty and n < 10:
                n += 1
                continue
            else:
                print('获取到最新数据')
                break
        if n == 10:
            print('最近'+time_interval+'周期没有数据')
        
        # 第三步：实盘获取实盘交易信号
        signal = real_time_signal_trend(chicang, df, para)     # 参数:当前持仓方向-1、0、1；止损比例；数据；策略参数(可选)
        print('最新信号是：', signal)

        # 获取当前持仓数量
        print('币币账户当前持仓品种：', base_coin, '持仓数量：', base_coin_amount)
        print('币币账户当前持仓品种：', trade_coin, '持仓数量：', trade_coin_amount)
        # print('杠杆账户当前持仓品种：', base_coin, '持仓数量：', total_usdt)
        # print('杠杆账户当前持仓品种：', trade_coin, '持仓数量：', total_btc)
        # exit()

        # signal = 1    # 测试用
        # chicang = 0   # 测试用
        # chicang_amount = 0.01         # 默认交易数量
        # 开多单
        if signal == 1:
            if chicang == 0:        # 若没有持仓
                print("开多单")
                # 获取最新卖一价格
                buy_price = exchange.fetch_ticker(symbol)['ask']
                # 计算买入数量，数量是指BTC的数量，不是USDT的数量
                # buy_amount = base_coin_amount / buy_price * 3.3 * 0.1 # 按比例开仓
                buy_amount = 0.01
                # 下单,只限于币币交易
                place_order(exchange, order_type='exchange limit', buy_or_sell='buy', symbol=symbol, price=round(buy_price*1.001, 2), amount=buy_amount)
                print(symbol, '155开多单 价格：'+str(buy_price)+' 数量：'+str(buy_amount))
                send_dingding_msg('开仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n开多单 价格：'+str(buy_price)+' \n数量：'+str(buy_amount))
                chicang_amount = buy_amount
                # exit()
            elif chicang == -1:     # 若有空单持仓
                print("平空单，开多单")
                # 平仓
                buy_price = exchange.fetch_ticker(symbol)['ask']    # 获取卖一价格
                print(symbol, '166开多单 价格：'+str(buy_price)+' 数量：'+str(chicang_amount))
                place_order(exchange, order_type='exchange limit', buy_or_sell='buy', symbol=symbol, price=round(buy_price*1.005, 2), amount=chicang_amount)
                send_dingding_msg('平仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n平空单 价格：'+str(buy_price)+' \n数量：'+str(chicang_amount))
                # 获取账户信息
                while True:
                    try:
                        # balance = exchange.fetch_balance()      # 获取普通exchange交易账户数据
                        balance_margin = exchange.fetch_balance({'type':'trading'})    # 获取margin账户资产，这是bitfinex交易所特有的
                        break
                    except:
                        continue
                base_coin_amount = float(balance_margin[base_coin]['total'])
                # 获取最新买一价格
                buy_price = exchange.fetch_ticker(symbol)['ask']
                # 计算买入数量
                # buy_amount = base_coin_amount / buy_price * 3.3 * 0.1
                buy_amount = 0.01
                # 开仓
                place_order(exchange, order_type='exchange limit', buy_or_sell='buy', symbol=symbol, price=round(buy_price*1.005, 2), amount=buy_amount)
                print(symbol, '185开多单 价格：'+str(buy_price)+' 数量：'+str(buy_amount))
                send_dingding_msg('开仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n开多单 价格：'+str(buy_price)+' \n数量：'+str(buy_amount))
                chicang_amount = buy_amount
            chicang = 1         # 持仓标记为持有多单
        
        # 开空单
        if signal == -1:
            if chicang == 0:        # 若没有持仓
                print("开空单")
                # 获取最新买一价格
                sell_price = exchange.fetch_ticker(symbol)['bid']
                # 计算卖出数量，这里的计算方式需要优化
                # sell_amount = base_coin_amount / buy_price * 3.3 * 0.1
                sell_amount = 0.01
                # 下单开仓
                place_order(exchange, order_type='exchange limit', buy_or_sell='sell', symbol=symbol, price=round(sell_price*0.995, 2), amount=sell_amount)
                print(symbol, '200开空单 价格：'+str(sell_price)+' 数量：'+str(sell_amount))
                send_dingding_msg('开仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n开空单 价格：'+str(sell_price)+' \n数量：'+str(sell_amount))
                chicang_amount = sell_amount
            elif chicang == 1:     # 若有多单持仓
                print("平多单，开空单")
                # 获取最新买一价格
                sell_price = exchange.fetch_ticker(symbol)['bid']
                # 下单平仓
                place_order(exchange, order_type='exchange limit', buy_or_sell='sell', symbol=symbol, price=round(sell_price*0.995, 2), amount=chicang_amount)
                print(symbol, '206平多单 价格：'+str(sell_price)+' 数量：'+str(chicang_amount))
                send_dingding_msg('平仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n平多单 价格：'+str(sell_price)+' \n数量：'+str(chicang_amount))
                # 获取账户信息
                while True:
                    try:
                        # balance = exchange.fetch_balance()      # 获取普通exchange交易账户数据
                        balance_margin = exchange.fetch_balance({'type':'trading'})    # 获取margin账户资产，这是bitfinex交易所特有的
                        break
                    except:
                        continue
                base_coin_amount = float(balance_margin[base_coin]['total'])
                # 获取最新买一价格
                sell_price = exchange.fetch_ticker(symbol)['bid']
                # 计算买入数量
                # sell_amount = base_coin_amount / buy_price * 3.3 * 0.1
                sell_amount = 0.01
                # 开仓
                place_order(exchange, order_type='exchange limit', buy_or_sell='sell', symbol=symbol, price=round(sell_price*0.995, 2), amount=sell_amount)
                print(symbol, '224开空单 价格：'+str(sell_price)+' 数量：'+str(sell_amount))
                send_dingding_msg('开仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n开空单 价格：'+str(sell_price)+' \n数量：'+str(sell_amount))
                chicang_amount = sell_amount
            chicang = -1        # 持仓标记为持有空单

        # 平仓
        if signal == 0:
            if chicang == 1:     # 若有多单持仓
                print('平多单')
                # 获取最新买一价格
                sell_price = exchange.fetch_ticker(symbol)['bid']
                # 下单
                place_order(exchange, order_type='exchange limit', buy_or_sell='sell', symbol=symbol, price=round(sell_price*0.995, 2), amount=chicang_amount)
                print(symbol, '236平多仓 价格：'+str(sell_price)+' 数量：'+str(chicang_amount))
                send_dingding_msg('平仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n平多单 价格：'+str(sell_price)+' \n数量：'+str(chicang_amount))
            if chicang == -1:     # 若有空单持仓
                print('平空单')
                # 获取最新卖一价格
                buy_price = exchange.fetch_ticker(symbol)['ask']
                # 下单
                place_order(exchange, order_type='exchange limit', buy_or_sell='buy', symbol=symbol, price=round(buy_price*1.005, 2), amount=chicang_amount)
                print(symbol, '244平空仓 价格：'+str(buy_price)+' 数量：'+str(chicang_amount))
                send_dingding_msg('平仓报告：\n策略名称：'+strategy2+'\n交易对：'+symbol+'\n平空单 价格：'+str(buy_price)+' \n数量：'+str(chicang_amount))
            chicang = 0         # 持仓标记为没有持仓

        # 本次交易结束
        print('=====本次运行完毕\n')



if __name__ == '__main__':
    main()
