# -*- coding:utf-8 -*-
'''
    回测专用
    合并数据周期，并计算交易信号    
'''

import pandas as pd
from Signals import signal_swing, signal_trend

pd.set_option('expand_frame_repr', False)       # 列太多时，不换行
pd.set_option('display.max_rows', 100)          # 最多显示100行


'''
    将1分钟的数据，转换成指定周期的数据
'''
def transfer_period(data, period):
    # 转化数据周期
    df = data.resample(rule=period, on='candle_begin_time', base=0, label='left', closed='left').agg({
        'open':'first',
        'high':'max',
        'low':'min',
        'close':'last',
        'volume':'sum',
    })
    df.dropna(subset=['open'], inplace=True)  # 去除一天都没有交易的周期
    df = df[df['volume'] > 0]                 # 去除成交量为0的交易周期
    df.reset_index(inplace=True)     # 写这一句索引是1、2、3的数字，不写的话索引是candle_begin_time。不写的话，后面计算资金曲线的步骤就会报错
    df = df[['candle_begin_time', 'open', 'high', 'low', 'close', 'volume']]
    df = df[df['candle_begin_time'] >= pd.to_datetime('2017-01-01')]        # 设定数据起始时间，根据需要修改数据起始时间
    # df = df[df['candle_begin_time'] <= pd.to_datetime('2018-01-01')]        # 设定数据结束时间，用来区分样本内和样本外数据
    df.reset_index(inplace=True, drop=True)

    return df
    


if __name__ == "__main__":
    df = pd.read_hdf('ethusdt.h5')
    # 转换数据周期

    new_data = transfer_period(df, '60T')
    new_data = new_data[new_data['candle_begin_time'] >= pd.to_datetime('2017-01-01')]      # 设定起始时间
    new_data = new_data[new_data['candle_begin_time'] <= pd.to_datetime('2019-09-01')]      # 设定结束时间，后面时间作为样本外测试
    # new_data.reset_index(inplace=True, drop=True)       # 当数据不是从第一行开始，需要重新设定索引
    # para = [20, 6, 14, 50, 50, 2]      # signal_swing参数
    para = [20, 6, 20, 2, 2, 50]       # signal_trend参数
    # 计算交易信号
    signal_data = signal_trend(new_data, para)
    # signal_data.to_hdf('btc_atr_signal.h5', key='all_data', mode='w')
    print('交易信号计算完成')


    # 直接计算结果
    from Return2 import back_index      # 计算回测指标
    from Evaluate import equity_curve_with_long_and_short       # 计算资金曲线

    df = equity_curve_with_long_and_short(signal_data, leverage_rate=3, c_rate=5.0 / 1000)
    print(df.iloc[-1]['equity_curve'])

    index = back_index()        # 计算回测结果指标,初始化

    index.base_info(df)
    index.all_interest(df)
    index.simple_interest(df)
    index.max_retracement(df)
    index.win_rate(df)
    index.profit_loss_ratio(df)
    index.rate_risk_return(df)
    index.sharpe_ratio(df)
    index.max_profit(df)
    index.max_loss(df)
    index.max_continuous_loss(df)
    index.max_continuous_win(df)
    index.ave_have_time(df)