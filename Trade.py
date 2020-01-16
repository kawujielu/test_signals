'''
    1、睡眠时间函数
    2、获取K线数据
    3、下单函数
    4、发送钉钉消息
'''

import time
import datetime
import pandas as pd
import json
import requests
import urllib

'''
    计算sleep的时间间隔
'''
def next_run_time(time_interval, ahead_time=1):
    if time_interval.endswith('m'):         # 如果是分钟级别的时间间隔
        now_time = datetime.datetime.now()
        time_interval = int(time_interval.strip('m'))       # 去掉右边的m

        next_time = (int(now_time.minute / time_interval)+1) * time_interval     # 下一次执行的分钟
        # print(next_time)
        if next_time < 60:
            target_time = now_time.replace(minute=next_time, second=0, microsecond=0)   # 更新时间
            # print(target_time)
        else:
            if now_time.hour == 23:
                target_time = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
                target_time += datetime.timedelta(days=1)        # 日期+1
            else:
                target_time = now_time.replace(hour=now_time.hour+1, minute=0, second=0, microsecond=0)

        # sleep直到靠近目标时间之前
        if (target_time-datetime.datetime.now()).seconds < ahead_time+1:
            print('距离target_time不足', ahead_time, '秒，下下个周期再运行')
            target_time += datetime.timedelta(minutes=time_interval)
        print('下次运行时间', target_time)
        return target_time

'''
    获取交易所的实时K线数据
'''
def get_exchange_candle_data(exchange, symbol, time_interval):
    for i in range(10):
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe=time_interval, limit=500,
                                        params = dict(sort=-1, end = int(datetime.datetime.now().timestamp()*1000)))  # limit是指抓取数据的数量
            # 整理数据
            df = pd.DataFrame(data, dtype=float)
            df.rename(columns={0:'time',1:'open',2:'high',3:'low',4:'close',5:'volume'}, inplace=True)
            df['candle_begin_time'] = pd.to_datetime(df['time'], unit='ms')    # unit='ms'不写这个，时间就是从1970年开始的
            df['candle_begin_time_GTM8'] = df['candle_begin_time'] + datetime.timedelta(hours=8)
            df = df[['candle_begin_time_GTM8', 'open', 'high', 'low', 'close', 'volume']]
            return df
        except Exception as e:
            print('未获取到K线数据', e)
            send_dingding_msg('网络错误：\n未获取到K线数据'+str(e))
            time.sleep(1)
    print('获取K线数据报错次数超过10次，请检查网络，程序终止')
    exit()

'''
    统一下单函数
'''
def place_order(exchange, order_type, buy_or_sell, symbol, price, amount):
    """
        :param exchange: 交易所
        :param order_type: limit, market
        :param buy_or_sell: buy, sell
        :param symbol: 买卖品种
        :param price: 当market订单的时候，price无效
        :param amount: 买卖量
        :return:
    """
    # 下单类型：
    # market：margin交易市价单
    # limit：margin交易限价单
    # exchange market：exchange交易市价单
    # exchange limit：exchange交易限价单
    for i in range(5):
        try:
            # 币币账户
            if order_type == 'exchange limit':
                if buy_or_sell == 'buy':
                    order_info = exchange.create_limit_buy_order(symbol, amount, price)      # 买单
                elif buy_or_sell == 'sell':
                    order_info = exchange.create_limit_sell_order(symbol, amount, price)     # 卖单
            
            print('下单成功：', order_type, buy_or_sell, symbol, price, amount)
            print('下单信息：', order_info, '\n')
            return order_info

        except Exception as e:
            print('下单错误，1s后重试', e)
            send_dingding_msg('下单错误：'+str(e))
            time.sleep(1)
    
    print('下单报错次数超过5次，程序终止')
    exit()

'''
    发送钉钉消息，id填上使用的机器人的id
'''
def send_dingding_msg(content, robot_id='d9c1250a225508d17c684bb5a4199ef8b0257422f60217587ff61911988e3571'):
    try:
        msg = {
            "msgtype": "text",
            "text": {"content": content + '\n' + datetime.datetime.now().strftime("%m-%d %H:%M:%S")}}
        headers = {"Content-Type": "application/json;charset=utf-8"}
        url = 'https://oapi.dingtalk.com/robot/send?access_token=' + robot_id
        body = json.dumps(msg)
        requests.post(url, data=body, headers=headers)
        print('成功发送钉钉')
        print(content)
    except Exception as e:
        print("发送钉钉失败:", e)


# send_dingding_msg('测试！开仓报告')
