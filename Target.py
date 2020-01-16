'''
   API文档http://www.ta-lib.org/function.html
'''

import talib
import numpy as np
import pandas as pd
pd.set_option('display.max_rows', 10)

class TargetClass(object):

    def __init__(self):
        pass

    # MA算数移动平均线
    def ma(self, data, para):
        '''
            timeperiod是均线周期
        '''
        ma = talib.MA(data, timeperiod = para)
        # print(ma)
        return ma

    # boll布林线
    def boll(self, data, timeperiod=20, nbdevup=2, nbdevdn=2):
        '''
            timeperiod是均线周期，nbdevup是上轨标准差倍数，nvdevdn下轨标准差倍数，matype是ma的类型，默认是算数平均值ma
            跟bitfinex和自己计算出来的代码的差别是，精确度更小，小数点后8位，自己计算的是小数点后6位
        '''
        upperband, middleband, lowerband = talib.BBANDS(data, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        return upperband, middleband, lowerband

    # ATR真实波动率
    def atr(self, data, para=14):
        '''
            timeperiod是均线周期
        '''
        atr = talib.ATR(data['high'], data['low'], data['close'], timeperiod=para)
        # print(atr)
        return atr

    # DMI指标
    def dmi(self, data, n=20, p=6):
        '''
            n 表示pdm和ndm周期
            p 表示dx周期
        '''
        # 计算tr
        data['v1'] = data['high'] - data['low']
        data['v2'] = abs(data['high'] - data['close'].shift(1))
        data['v3'] = abs(data['low'] - data['close'].shift(1))
        data['tr'] = data[['v1', 'v2', 'v3']].max(axis=1)

        # 计算+DM值和-DM值
        data['+dm'] = data['high'] - data['high'].shift(1)
        data['-dm'] = data['low'].shift(1) - data['low']
        data.dropna(inplace=True)
        data.reset_index(drop=True, inplace=True)

        data['pdm'] = np.where((data['+dm'] > 0) & (data['+dm'] > data['-dm']), data['+dm'], 0)
        data['ndm'] = np.where((data['-dm'] > 0) & (data['-dm'] > data['+dm']), data['-dm'], 0)

        data['pdm_n'] = data['pdm'].rolling(n, min_periods=1).sum()
        data['ndm_n'] = data['ndm'].rolling(n, min_periods=1).sum()
        data['tr_n'] = data['tr'].rolling(n, min_periods=1).sum()

        data['pdi'] = data['pdm_n'] / data['tr_n'] * 100
        data['mdi'] = data['ndm_n'] / data['tr_n'] * 100

        data['dx'] = abs(data['pdi'] - data['mdi']) / (data['pdi'] + data['mdi']) * 100
        adx = data['dx'].rolling(p, min_periods=1).mean()

        return adx

if __name__ == '__main__':
    # 测试
    df = pd.read_hdf('ethusdt.h5')
    target = TargetClass()
    target.boll(df['close'])
    
