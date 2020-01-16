'''
    回测策略
    signal_rsi
    实盘策略
    real_time_signal_rsi
'''

import datetime
import math
import pandas as pd
import numpy as np
from Target import TargetClass
pd.set_option('expand_frame_repr', False)
pd.set_option('display.max_rows', 10)

'''
    震荡策略，回测代码
'''
def signal_swing(df, para=[20, 6, 14, 50, 50, 2]):
    n = para[0]     # pdm和ndm周期
    p = para[1]     # dx周期
    tr = para[2]    # ATR周期
    h = para[3]     # h周期最高价的最高点
    l = para[4]     # l周期最低价的最低点
    s = para[5]     # ATR保护性止损倍数
    tc = TargetClass()

    # 计算adx指标
    df['adx'] = tc.dmi(df.copy(), n, p)

    # 计算ATR真实波动率
    df['atr'] = tc.atr(df.copy(), tr)

    # 计算开盘区间高低点
    df['hh'] = df['high'].rolling(h, min_periods=1).max()       # h周期最高价的最高点
    df['ll'] = df['low'].rolling(l, min_periods=1).min()        # l周期最低价的最低点

    # 做多信号
    condition1 = df['adx'] < 20                                 # 震荡
    condition2 = df['close'] > df['hh'].shift(1)                # 价格突破前期高点
    df.loc[condition1 & condition2, 'signal_swing_long'] = 1    # 标记为震荡做多

    # 平仓信号
    condition1 = df['close'] < df['ll'].shift(1)                # 反手信号
    df['swing_long_stop_atr'] = df['close'] - df['atr']*s
    condition2 = df['close'] < df['swing_long_stop_atr']        # ATR保护性止损
    df.loc[condition1 | condition2, 'signal_swing_long'] = 0    # 标记为震荡平多

    # 做空信号
    condition1 = df['adx'] < 20                                 # 震荡
    condition2 = df['close'] < df['ll'].shift(1)                # 价格突破前期低点
    df.loc[condition1 & condition2, 'signal_swing_short'] = -1  # 标记为震荡做空

    # 平仓信号
    condition1 = df['close'] > df['hh'].shift(1)                # 反手信号
    df['swing_short_stop_atr'] = df['close'] + df['atr']*s
    condition2 = df['close'] > df['swing_short_stop_atr']       # ATR保护性止损
    df.loc[condition1 | condition2, 'signal_swing_short'] = 0   # 标记为震荡平空

    # ===防止因为没有产生signal而报错
    df['signal'] = np.nan
    # ===记录之前交易信号，或称为持仓状态
    info_dict = {'pre_signal':0}

    # 逐行遍历df，考察每一行的交易信号
    for i in range(df.shape[0]):
        # 如果之前是空仓
        if info_dict['pre_signal'] == 0:
            # 当本周期有做多信号
            if df.at[i, 'signal_swing_long'] == 1:
                df.at[i, 'signal'] = 1
                # 记录当前状态
                pre_signal = 1              # 信号
                info_dict = {'pre_signal':pre_signal}
            # 当本周期有做空信号
            elif df.at[i, 'signal_swing_short'] == -1:
                df.at[i, 'signal'] = -1
                # 记录当前状态
                pre_signal = -1             # 信号
                info_dict = {'pre_signal':pre_signal}
            # 无信号
            else:
                # 记录相关信息
                info_dict = {'pre_signal':0}
        
        # 如果之前是多头仓位
        elif info_dict['pre_signal'] == 1:
            # 当本周期有平多仓信号，或者需要止损
            if df.at[i,'signal_swing_long'] == 0:
                df.at[i,'signal'] = 0
                # 记录相关信息
                info_dict = {'pre_signal':0}
            
            # 当本周期有平多仓并且还要开空仓
            if df.at[i, 'signal_swing_short'] == -1:
                df.at[i, 'signal'] = -1
                # 记录相关信息
                pre_signal = -1      # 信号
                info_dict = {'pre_signal':pre_signal}

        # 如果之前是空头仓位
        elif info_dict['pre_signal'] == -1:
            # 当本周期有平空仓信号，或者需要止损
            if df.at[i, 'signal_swing_short'] == 0:
                df.at[i, 'signal'] = 0      # 将真实信号设置为0
                # 记录相关信息
                info_dict = {'pre_signal':0}

            # 当本周期有平空仓并且还要开多仓
            if df.at[i, 'signal_swing_long'] == 1:
                df.at[i, 'signal'] = 1      # 将真实信号设置1
                # 记录相关信息
                pre_signal = 1      # 信号
                info_dict = {'pre_signal':pre_signal}

        # 其他情况
        else:
            raise ValueError('不可能出现其他的情况，如果出现，说明代码逻辑有误，报错！')
    
    # 删除无关变量
    df.drop(['hh', 'll'], axis=1, inplace=True)

    # ===由signal计算出实际的每天持有仓位
    # signal的计算运用了收盘价，是每根K线收盘之后产生的信号，到第二根开盘的时候才买入，仓位才会改变。
    df['pos'] = df['signal'].shift()
    df['pos'].fillna(method='ffill', inplace=True)
    df['pos'].fillna(value=0, inplace=True)     # 将初始行数的position补全为0

    return df

'''
    震荡策略，实盘代码
'''
def real_time_signal_swing(now_pos, df, para=[20, 6, 14, 50, 50, 2]):
    n = para[0]     # pdm和ndm周期
    p = para[1]     # dx周期
    tr = para[2]    # ATR周期
    h = para[3]     # h周期最高价的最高点
    l = para[4]     # l周期最低价的最低点
    s = para[5]     # ATR保护性止损倍数
    tc = TargetClass()

    # 计算adx指标
    df['adx'] = tc.dmi(df.copy(), n, p)

    # 计算ATR真实波动率
    df['atr'] = tc.atr(df.copy(), tr)

    # 计算开盘区间高低点
    df['hh'] = df['high'].rolling(h, min_periods=1).max()       # h周期最高价的最高点
    df['ll'] = df['low'].rolling(l, min_periods=1).min()        # l周期最低价的最低点

    adx = df['adx'].iloc[-1]
    atr = df['atr'].iloc[-1]
    hh = df['hh'].iloc[-2]
    ll = df['ll'].iloc[-2]
    close_price = df['close'].iloc[-1]

    # 现在是多头仓位
    if now_pos == 1:
        # 依次计算是否要直接开空仓、平仓、止盈、止损
        if close_price < close_price-atr*s or close_price < ll:
            target_pos = 0
        elif adx < 20 and close_price < ll:
            target_pos = -1
        else:
            target_pos = 1
        
    # 现在是空头仓位
    elif now_pos == -1:
        # 依次计算是否要直接开空仓、平仓、止损
        if close_price > close_price+atr*s or close_price > hh:
            target_pos = 0
        elif adx < 20 and close_price > hh:
            target_pos = 1
        else:
            target_pos = -1
    
    # 现在无仓位
    elif now_pos == 0:
        # 计算是否要开多仓还是开空仓
        if adx < 20 and close_price > hh:     # 开多仓
            target_pos = 1
        elif adx < 20 and close_price < ll:    # 开空仓
            target_pos = -1
        else:
            target_pos = 0
    
    # 其他情况报错
    else:
        raise ValueError('当前仓位变量now_pos数值只能是1，-1，0，但目前是', now_pos)
    
    return target_pos


'''
    趋势策略，回测代码
'''
def signal_trend(df, para=[20, 6, 20, 2, 2, 50]):
    n = para[0]     # pdm和ndm周期
    p = para[1]     # dx周期
    t = para[2]     # bolling周期
    up = para[3]    # 上轨标准差倍数
    dn = para[4]    # 下轨标准差倍数
    m = para[5]     # 出场均线周期
    tc = TargetClass()

    # 计算adx指标
    df['adx'] = tc.dmi(df.copy(), n, p)

    # 计算bolling指标
    df['upperband'], df['middleband'], df['lowerband'] = tc.boll(df.copy()['close'], t, up, dn)

    # 计算ma均线
    df['ma'] = tc.ma(df.copy()['close'], m)

    # 做多信号
    condition1 = df['adx'] > 20                                 # 趋势
    condition2 = df['close'] > df['upperband']                  # 价格突破bolling上轨
    df.loc[condition1 & condition2, 'signal_trend_long'] = 1    # 标记为趋势做多

    # 平仓信号
    condition1 = df['close'] < df['lowerband']                  # 反手信号
    condition2 = df['close'] < df['ma']                         # 均线出场
    df.loc[condition1 | condition2, 'signal_trend_long'] = 0    # 标记为趋势平多

    # 做空信号
    condition1 = df['adx'] > 20                                 # 趋势
    condition2 = df['close'] < df['lowerband']                  # 价格跌破bolling下轨
    df.loc[condition1 & condition2, 'signal_trend_short'] = -1  # 标记为趋势做空

    # 平仓信号
    condition1 = df['close'] > df['upperband']                  # 反手信号
    condition2 = df['close'] > df['ma']                         # 均线出场
    df.loc[condition1 | condition2, 'signal_trend_short'] = 0   # 标记为趋势平空

    # ===防止因为没有产生signal而报错
    df['signal'] = np.nan
    # ===记录之前交易信号，或称为持仓状态
    info_dict = {'pre_signal':0}

    # 逐行遍历df，考察每一行的交易信号
    for i in range(df.shape[0]):
        # 如果之前是空仓
        if info_dict['pre_signal'] == 0:
            # 当本周期有做多信号
            if df.at[i, 'signal_trend_long'] == 1:
                df.at[i, 'signal'] = 1
                # 记录当前状态
                pre_signal = 1              # 信号
                info_dict = {'pre_signal':pre_signal}
            # 当本周期有做空信号
            elif df.at[i, 'signal_trend_short'] == -1:
                df.at[i, 'signal'] = -1
                # 记录当前状态
                pre_signal = -1             # 信号
                info_dict = {'pre_signal':pre_signal}
            # 无信号
            else:
                # 记录相关信息
                info_dict = {'pre_signal':0}
        
        # 如果之前是多头仓位
        elif info_dict['pre_signal'] == 1:
            # 当本周期有平多仓信号，或者需要止损
            if df.at[i,'signal_trend_long'] == 0:
                df.at[i,'signal'] = 0
                # 记录相关信息
                info_dict = {'pre_signal':0}
            
            # 当本周期有平多仓并且还要开空仓
            if df.at[i, 'signal_trend_short'] == -1:
                df.at[i, 'signal'] = -1
                # 记录相关信息
                pre_signal = -1      # 信号
                info_dict = {'pre_signal':pre_signal}

        # 如果之前是空头仓位
        elif info_dict['pre_signal'] == -1:
            # 当本周期有平空仓信号，或者需要止损
            if df.at[i, 'signal_trend_short'] == 0:
                df.at[i, 'signal'] = 0      # 将真实信号设置为0
                # 记录相关信息
                info_dict = {'pre_signal':0}

            # 当本周期有平空仓并且还要开多仓
            if df.at[i, 'signal_trend_long'] == 1:
                df.at[i, 'signal'] = 1      # 将真实信号设置1
                # 记录相关信息
                pre_signal = 1      # 信号
                info_dict = {'pre_signal':pre_signal}

        # 其他情况
        else:
            raise ValueError('不可能出现其他的情况，如果出现，说明代码逻辑有误，报错！')

    # ===由signal计算出实际的每天持有仓位
    # signal的计算运用了收盘价，是每根K线收盘之后产生的信号，到第二根开盘的时候才买入，仓位才会改变。
    df['pos'] = df['signal'].shift()
    df['pos'].fillna(method='ffill', inplace=True)
    df['pos'].fillna(value=0, inplace=True)     # 将初始行数的position补全为0

    return df

'''
    趋势策略，实盘代码
'''
def real_time_signal_trend(now_pos, df, para=[20, 6, 20, 2, 2, 50]):
    n = para[0]     # pdm和ndm周期
    p = para[1]     # dx周期
    t = para[2]     # bolling周期
    up = para[3]    # 上轨标准差倍数
    dn = para[4]    # 下轨标准差倍数
    m = para[5]     # 出场均线周期
    tc = TargetClass()

    # 计算adx指标
    df['adx'] = tc.dmi(df.copy(), n, p)

    # 计算bolling指标
    df['upperband'], df['middleband'], df['lowerband'] = tc.boll(df.copy()['close'], t, up, dn)

    # 计算ma均线
    df['ma'] = tc.ma(df.copy()['close'], m)

    adx = df['adx'].iloc[-1]
    ma = df['ma'].iloc[-1]
    upperband = df['upperband'].iloc[-1]        # 上轨
    lowerband = df['lowerband'].iloc[-1]        # 下轨
    close_price = df['close'].iloc[-1]          # 最新价格

    # 现在是多头仓位
    if now_pos == 1:
        # 依次计算是否要直接开空仓、平仓、止盈、止损
        if close_price < lowerband or close_price < ma:
            target_pos = 0
        elif adx > 20 and close_price < lowerband:
            target_pos = -1
        else:
            target_pos = 1
        
    # 现在是空头仓位
    elif now_pos == -1:
        # 依次计算是否要直接开空仓、平仓、止损
        if close_price > upperband or close_price > ma:
            target_pos = 0
        elif adx > 20 and close_price > upperband:
            target_pos = 1
        else:
            target_pos = -1
    
    # 现在无仓位
    elif now_pos == 0:
        # 计算是否要开多仓还是开空仓
        if adx > 20 and close_price > upperband:     # 开多仓
            target_pos = 1
        elif adx > 20 and close_price < lowerband:    # 开空仓
            target_pos = -1
        else:
            target_pos = 0
    
    # 其他情况报错
    else:
        raise ValueError('当前仓位变量now_pos数值只能是1，-1，0，但目前是', now_pos)
    
    return target_pos



# 测试用
if __name__ == '__main__':
    all_data = pd.read_hdf('ethusdt.h5')
    # print(all_data)
    a = signal_trend(all_data)
    print(a)