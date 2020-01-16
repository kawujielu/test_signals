'''
    回测专用
    策略回测（非优化）
    计算资金曲线
    计算回测指标
'''

# 永久复用代码
import pandas as pd
import math
import matplotlib.pyplot as plt
pd.set_option('expand_frame_repr', False)       # 当列太多时，不换行
pd.set_option('display.max_rows', 100)          # 只显示100行数据,如果数字太大，会不显示内容

'''
    close
'''

def return2():
    # 导入数据
    # df = data
    # print(df)
    # exit()
    df = pd.read_hdf('btc_atr_signal.h5', key='all_data')
    # print(len(df))
    # exit()

    # 选取时间段
    df = df[df['candle_begin_time'] >= pd.to_datetime('2017-01-01')]
    df = df[df['candle_begin_time'] < pd.to_datetime('2019-09-01')]
    df.reset_index(inplace=True, drop=True)         # inplace=True表示重新计算index，drop=True表示将之前的index删除掉

    # 计算涨跌幅
    df['change'] = df['close'].pct_change(1)                              # 根据收盘价计算涨跌幅，pct_change表示当前元素与先前元素的相差百分比
    df['buy_at_open_change'] = df['close']/df['open']-1                   # 从今天开盘买入，到今天收盘的涨跌幅。开仓用
    df['sell_next_open_change'] = df['open'].shift(-1)/df['close']-1      # 从今天收盘到明天开盘的涨跌幅。平仓用
    df.at[len(df) - 1, 'sell_next_open_change'] = 0                       # 将最后一列的最后一个值设为0。条件是数据的index必须是数字，不能是日期

    # 选择开平仓条件
    tiaojian1 = df['pos'] != 0                      # 开仓条件1：不是0，是1或-1
    tiaojian2 = df['pos'] != df['pos'].shift(1)     # 开仓条件2：pos与上一个pos值不同
    open_pos_condition = tiaojian1 & tiaojian2

    tiaojian1 = df['pos'] != 0
    tiaojian2 = df['pos'] != df['pos'].shift(-1)
    close_pos_condition = tiaojian1 & tiaojian2

    # 对每组交易进行分组
    df.loc[open_pos_condition, 'start_time'] = df['candle_begin_time']   # bool类型可以当作行，真强大
    df['start_time'].fillna(method='ffill', inplace=True)       # 向上补全数据。不加inplace=True，则数据没有任何变化
    df.loc[df['pos'] == 0, 'start_time'] = pd.NaT               # 将没有持仓的行，start_time列变成None


    # 基本参数
    leverage_rate = 3       # 杠杆倍数
    init_cash = 100         # 初始资金
    c_rate = 4/1000         # 手续费
    min_margin_rate = 0.15  # 最低保证金比例，必须占到借来资产的15%。这里一定要搞明白！！！
    min_margin = init_cash * leverage_rate * min_margin_rate        # 最低保证金，资金小于这个值，会被强制平仓

    # 计算仓位变动
    # 开仓时的仓位,position是表示持仓的比例——仓位
    df.loc[open_pos_condition, 'position'] = init_cash * leverage_rate * (1 + df['buy_at_open_change'] * 0.1)   # init_cash * 0.1   # 开仓10% #      # 开仓之后，第一根K线结束之后，我们的仓位还剩多少
    # print(df['position'])
    # exit()
    # print(df[['start_time','pos','position']])
    # 开仓后每天的仓位变动
    group_num = len(df.groupby('start_time'))
    # print(group_num)
    if group_num > 1:
        t = df.groupby('start_time')
        # print(t)  # 这是一个DataFrameGroupBy类型的对象
        t = df.groupby('start_time').apply(lambda x:x['close']/x.iloc[0]['close'] * x.iloc[0]['position'])  # apply()不懂，后面的lambda计算公式大致明白了
        # print(t)  # 这个一个二维的Series对象
        t = t.reset_index(level=[0])        # 这里为什么只有一列？而且这一列的名称是close？
        # print(t)  # 这是一个DataFrame对象
        df['position'] = t['close']    # 计算出来的结果，是最终收盘时候的position（位置，状况）
    # print(df[['start_time','pos','close','position']])

    # 每根K线仓位的最大值和最小值，针对最高价和最低价
    df['position_max'] = df['position'] * df['high'] / df['close']
    df['position_min'] = df['position'] * df['low'] / df['close']
    # print(df[['candle_begin_time','pos','position']])

    # 重新精确计算平仓时的资金净值
    df.loc[close_pos_condition,'position'] *= (1 + df.loc[close_pos_condition, 'sell_next_open_change'])    # 用开盘价计算净值比收盘价更准确
    # print(df[['candle_begin_time','pos','position']])

    # 每天实际资金的变化
    # 计算持仓利润，profit表示每天的盈亏金额
    df['profit'] = (df['position'] - init_cash*leverage_rate) * df['pos']   # 盈利或亏损的金额。这个计算方法很可疑？？？？？
    # 计算持仓过程中的最小值,用来计算是否爆仓
    df.loc[df['pos'] == 1, 'profit_min'] = (df['position_min'] - init_cash*leverage_rate) * df['pos']   # 做多时的资金最小值
    df.loc[df['pos'] == -1, 'profit_min'] = (df['position_max'] - init_cash*leverage_rate) * df['pos']  # 做空时的资金最小值

    # 计算实际资金量，cash表示账户剩余金额
    df['cash'] = init_cash + df['profit']               # 实际资金
    df['cash'] -= init_cash * leverage_rate * c_rate    # 减去开仓时的手续费
    df['cash_min'] = df['cash'] - (df['profit'] - df['profit_min'])       # 这个计算公式完全没有弄明白？？？？？？？？？
    # 实际最小资金，放在平仓手续费前，是因为爆仓肯定先于平仓
    df.loc[close_pos_condition, 'cash'] -= df.loc[close_pos_condition, 'position'] * c_rate      # 减去平仓时的手续费，为什么是用position减去？
    # print(df[['candle_begin_time','pos','start_time','position','profit','cash','cash_min']])

    # 计算资金曲线
    df['equity_change'] = df['cash'].pct_change(1)   # 计算每一天cash的涨跌幅比例
    df.loc[open_pos_condition, 'equity_change'] = df.loc[open_pos_condition, 'cash'] / init_cash -1    # 开仓当天的涨跌幅
    df['equity_change'].fillna(value=0, inplace=True)
    df['equity_curve'] = (1 + df['equity_change']).cumprod()    # 求矩阵的累计乘积

# ===删除不必要的数据
    # df.drop(['change', 'buy_at_open_change', 'sell_next_open_change', 'start_time', 'position', 'position_max',
    #      'position_min', 'profit', 'profit_min', 'cash', 'cash_min'], axis=1, inplace=True)
# print(df[['candle_begin_time','open','high','low','close','volume','signal','pos','equity_curve']])
# print(len(df))

# 只看开平仓记录
# df = df[df['pos'] != df['pos'].shift()]
    print(df[['candle_begin_time','pos','close','position','cash','equity_change','equity_curve']])
# print(len(df))
    # return df

# exit()



'''
    记录所有需要的回测指标
    总收益率                                            all_interest
    年化单利
    月化单利
    最大回撤
    胜率（盈利次数，亏损次数，总交易次数）
    盈亏比（平均每笔盈利，平均每笔亏损）
    夏普比率
    单笔最大盈利
    单笔最大亏损
    最大连续回测次数
    最大连续盈利次数
    平均持仓时长（平均盈利持仓时长，平均亏损持仓时长）
    ……
    多单盈利次数，亏损次数
    空单盈利次数，亏损次数，用来优化多空策略不同的参数

    需要增加的回测指标：
    信息比率
    卡马比率
'''

class back_index:
    
    def __init__(self):
        self.all_interest_num = 0
        self.simple_interest_num = 0
        # …………
        self.win_num = 0               # 盈利次数
        self.loss_num = 0              # 亏损次数
        self.all_num = 0               # 总交易次数
        self.all_time = 0              # 总持仓时间
        self.profit_time = 0           # 盈利持仓总时间
        self.loss_time = 0             # 亏损持仓总时间
        self.profit_loss_ratio_num = 0 # 盈亏比
        self.win_rate_num = 0          # 胜率


    # 回测天数和K线数目
    def base_info(self, data):
        date_num = data.iloc[-1]['candle_begin_time'] - data.iloc[0]['candle_begin_time']
        print('测试天数：', date_num)
        candle_num = len(data['candle_begin_time'])
        print('测试周期数：', candle_num)

        # return date_num, candle_num

    # 总收益率
    def all_interest(self, data):
        all_interest_num = round((data.iloc[-1]['equity_curve'] - 1)*100, 3)
        print('总收益率：', all_interest_num, '%')
        # return all_interest_num
    
    # 总收益率-最大盈利
    def all_interest_without_max_profit(self, data):
        all_interest_num = round((data.iloc[-1]['equity_curve'] - 1)*100, 3)
        print('总收益率：', all_interest_num, '%')
        # return all_interest_num

    # 年化单利
    def simple_interest(self, data):
        # （投资收益 / 本金）/ （测试天数 / 365）
        shouyilv = (data.iloc[-1]['equity_curve']-1)/1      # 投资收益 / 本金
        tianshu = data.iloc[-1]['candle_begin_time'] - data.iloc[0]['candle_begin_time']
        tianshu = (tianshu.days + 1)/365                    # 测试天数 / 365, +1是因为取整天数，收益率也会更小，更实际
        simple_interest_num = round(shouyilv/tianshu*100, 3)
        print('年化单利：', simple_interest_num, '%')
        # return simple_interest_num

    # 月化单利
    def simple_interest_month(self, data):
        # （投资收益 / 本金）/ （测试天数 / 30）
        shouyilv = (data.iloc[-1]['equity_curve']-1)/1      # 投资收益 / 本金
        tianshu = data.iloc[-1]['candle_begin_time'] - data.iloc[0]['candle_begin_time']
        tianshu = (tianshu.days + 1)/30                    # 测试天数 / 365, +1是因为取整天数，收益率也会更小，更实际
        simple_interest_month_num = round(shouyilv/tianshu*100, 3)
        print('月化单例：', simple_interest_month_num, '%')
        # return simple_interest_month_num

    # 最大回撤
    def max_retracement(self, data):
        # 计算每一笔交易平仓后的净值与其他净值相比，留下最大和最小值，用净值最大值-最小值 / 最大值
        max_num = 1                                     # 净值最大值
        min_num = 100                                   # 净值最小值
        final_num = data.iloc[-1]['equity_curve']       # 最终净值
        max_retracement_num = 0                         # 最大回撤
        for i in data['equity_curve']:
            if i > max_num:
                max_num = i
            elif i < min_num:
                min_num = i
                max_retracement_num = round((max_num-min_num)/max_num*100, 3)
        # print('净值最大值：', max_num)
        # print('净值最小值：', min_num)
        # print('最终净值：', final_num)
        print('最大回撤：', max_retracement_num, '%')
        # return max_retracement_num

    # 胜率
    def win_rate(self, data):
        # 盈利交易次数 / 总交易次数
        # win_num = 0             # 盈利次数
        # loss_num = 0            # 亏损次数
        data = data[data['pos'] != data['pos'].shift()]         # 只获取开平仓的行
        # 当非多既空的开平仓条件时，是没有pos=0的值的，这里的逻辑要优化
        # 只获取平仓行数据,这里要准确的统计出平仓的次数
        data = data.copy()
        data['temp'] = data['pos'] + data['pos'].shift()
        tj11 = data['pos'] == 0
        tj12 = data['temp'] == 0                   
        tj1 = tj11 | tj12
        tj2 = data['equity_curve'] - data['equity_curve'].shift() > 0      # 盈利
        tj3 = data['equity_curve'] - data['equity_curve'].shift() < 0      # 亏损
        win = tj1 & tj2
        loss = tj1 & tj3
        for i in win:
            if i is True:
                self.win_num += 1
        for i in loss:
            if i is True:
                self.loss_num += 1
        self.all_num = self.win_num + self.loss_num
        self.win_rate_num = round(self.win_num / self.all_num * 100, 3)
        print('盈利次数：', self.win_num)
        print('亏损次数：', self.loss_num)
        print('总交易次数：', self.all_num)
        print('胜率：', self.win_rate_num, '%')
        # return win_rate_num

    # 盈亏比
    def profit_loss_ratio(self, data):
        # 平均每次盈利 / 平均每次亏损
        win_num = 0             # 盈利次数
        loss_num = 0            # 亏损次数
        profit = 0              # 盈利金额
        loss = 0                # 亏损金额
        data = data[data['pos'] != data['pos'].shift()]         # 只获取开平仓的行
        # pos = data['pos'] == 0                                  # pos值为0的行，标记为True
        # data['profit_loss'] = data['equity_curve'] - data['equity_curve'].shift()     # 计算盈亏金额，这样写有警告
        # data['profit_loss'] = data['equity_curve'].diff(1)                              # 这样写也有警告
        # data.loc[:, 'profit_loss'] = data['equity_curve'].diff(1)                       # 这样写也有警告
        data = data.copy()                                      # 先copy一下，然后再赋值就不会报错
        data['profit_loss'] = data['equity_curve'].diff(1)      # https://blog.csdn.net/qq_42711381/article/details/90451301 有写详细的原因
        data['profit_loss'].fillna(value=0, inplace=True)       # 将所有profit_loss值为NaN的值，替换为0
        # 只获取平仓行数据
        data['temp'] = data['pos'] + data['pos'].shift()
        tj11 = data['pos'] == 0
        tj12 = data['temp'] == 0                   
        tj1 = tj11 | tj12
        tj2 = data['equity_curve'] - data['equity_curve'].shift() > 0      # 盈利
        tj3 = data['equity_curve'] - data['equity_curve'].shift() < 0      # 亏损
        win_tag = tj1 & tj2
        loss_tag = tj1 & tj3
        for i in data.loc[win_tag, 'profit_loss']:
            profit += i                  # 盈利总额
        for i in data.loc[loss_tag, 'profit_loss']:
            loss += i                    # 亏损总额
        for i in win_tag:
            if i is True:
                win_num += 1             # 盈利次数
        for i in loss_tag:
            if i is True:
                loss_num += 1            # 盈利次数
        ave_profit = profit / win_num    # 平均每笔盈利
        ave_loss = loss / loss_num       # 平均每笔亏损
        self.profit_loss_ratio_num = abs(round(ave_profit / ave_loss, 2))
        print('盈亏比：', self.profit_loss_ratio_num)
        # return profit_loss_ratio_num
    
    # 风报比（风险报酬比）
    '''
        胜率*预期盈利百分比 / 败率*预期亏损百分比
        越大越好，一般大于2就可以应用了
    '''
    def rate_risk_return(self, data):
        rate_risk_return_num = round(self.win_rate_num/100 * self.profit_loss_ratio_num / (1-self.win_rate_num/100) * 1, 2)
        print('风报比：', rate_risk_return_num)
        # return rate_risk_return_num

    # 夏普比率
    '''
        问题：
        由于无风险利率的存在，明明赚钱的交易，也可能是负的夏普比率。
        比如：每次固定开仓初始金额的1%资金量，一年盈利总资金量的1.5%，减去3%无风险利率，导致超额回报率<0，夏普比率<0
    '''
    def sharpe_ratio(self, data):
        # (年化收益率 - 无风险收益率) / 年化波动率    数学公式是这样，但计算方法不是。需要验证，不确定是否正确
        #计算超额回报率
        data['exReturn'] = data['equity_change']-0.03/365       # 无风险利率按照年化3%计算
        #计算夏普比率
        sharpe_ratio_num = math.sqrt(365)*data['exReturn'].mean()/data['exReturn'].std()
        sharpe_ratio_num = round(sharpe_ratio_num, 3)
        print('夏普比率：', sharpe_ratio_num)
        # return sharpe_ratio_num

    # 最大单笔盈利
    '''
        很可能还是有问题,用金额来计算会不会更符合真实情况一点呢？
        固定金额开仓，用盈亏百分比计算没有问题
        按比例开仓，则必须用金额来计算
    '''
    def max_profit(self, data):
        data = data[data['pos'] != data['pos'].shift()]
        data = data.copy()
        data['profit'] = data['equity_curve'] - data['equity_curve'].shift(1)
        max_profit_num = round(data['profit'].max()*100, 3)
        print('单笔最大盈利：', max_profit_num, '%')
        # return max_profit_num

    # 最大单笔亏损
    # 问题同上
    def max_loss(self, data):
        data = data[data['pos'] != data['pos'].shift()]
        data = data.copy()
        data['profit'] = data['equity_curve'] - data['equity_curve'].shift(1)
        max_loss_num = round(data['profit'].min()*100, 3)
        print('单笔最大亏损：', max_loss_num, '%')
        # return max_loss_num

    # 最大连续亏损
    def max_continuous_loss(self, data):
        max_continuous_loss_num = 0                             # 连续亏损次数
        temp_loss_num = 0                                       # 临时记录连续数目
        tag = 0                                                 # 上一次交易是否亏损，亏损标记-1
        data = data.copy()
        data = data[data['pos'] != data['pos'].shift()]         # 只获取开平仓的行
        # 只获取平仓的行，需要考虑非多即空的策略
        data['temp'] = data['pos'] + data['pos'].shift()
        tj1 = data['pos'] == 0
        tj2 = data['temp'] == 0
        pos = tj1 | tj2
        data['profit_loss'] = data['equity_curve'].diff(1)      # 每次开平仓的盈亏之
        data = data[pos]                                        # 只保留平仓行
        for i in data['profit_loss']:
            if i < 0:
                if tag == -1:
                    temp_loss_num += 1
                if tag != -1:
                    temp_loss_num = 1
                    tag = -1
            else:
                if temp_loss_num > max_continuous_loss_num:
                    max_continuous_loss_num = temp_loss_num
                    temp_loss_num = 0
                else:
                    temp_loss_num = 0
        print('最大连续亏损：', max_continuous_loss_num, '次')
        # return max_continuous_loss_num

    # 最大连续盈利
    def max_continuous_win(self, data):
        max_continuous_win_num = 0                              # 连续亏损次数
        temp_win_num = 0                                        # 临时记录连续数目
        tag = 0                                                 # 上一次交易是否亏损，亏损标记-1
        data = data.copy()
        data = data[data['pos'] != data['pos'].shift()]         # 只获取开平仓的行
        # 只获取平仓的行，需要考虑非多即空的策略
        data['temp'] = data['pos'] + data['pos'].shift()
        tj1 = data['pos'] == 0
        tj2 = data['temp'] == 0
        pos = tj1 | tj2
        data['profit_loss'] = data['equity_curve'].diff(1)
        data = data[pos]                                        # 只保留平仓行
        for i in data['profit_loss']:
            if i > 0:
                if tag == -1:
                    temp_win_num += 1
                if tag != -1:
                    temp_win_num = 1
                    tag = -1
            else:
                if temp_win_num > max_continuous_win_num:
                    max_continuous_win_num = temp_win_num
                    temp_win_num = 0
                else:
                    temp_loss_num = 0
        print('最大连续盈利：', max_continuous_win_num, '次')
        # return max_continuous_win_num

    # 平均持仓时长
    def ave_have_time(self, data):
        data = data[data['pos'] != data['pos'].shift()]                  # 只获取开平仓的行
        # 只获取平仓的行，需要考虑非多即空的策略
        data = data.copy()
        data['temp'] = data['pos'] + data['pos'].shift()
        tj1 = data['pos'] == 0
        tj2 = data['temp'] == 0
        pos = tj1 | tj2
        date_time = data['candle_begin_time'].diff(1)                    # 计算时间差
        data.loc[pos, 'date_time'] = date_time                           # 赋值给新列

        tj2 = data['equity_curve'] - data['equity_curve'].shift() > 0    # 盈利
        tj3 = data['equity_curve'] - data['equity_curve'].shift() < 0    # 亏损
        win_tag = pos & tj2
        loss_tag = pos & tj3

        self.profit_time = data.loc[win_tag, 'date_time'].sum()          # 盈利持仓总时间
        self.loss_time = data.loc[loss_tag, 'date_time'].sum()           # 亏损持仓总时间
        self.all_time = data['date_time'].sum()                          # 总持仓时间
        print('总持仓时间：', self.all_time)
        print('盈利持仓总时间：', self.profit_time)
        print('亏损持仓总时间：', self.loss_time)
        ave_profit_time = self.profit_time / self.win_num                # 盈利持仓总时间 / 盈利次数
        ave_loss_time = self.loss_time / self.loss_num                   # 亏损持仓总时间 / 亏损次数
        print('盈利平均持仓时间：', ave_profit_time)
        print('亏损平均持仓时间：', ave_loss_time)
        # return ave_have_time_num
    
    # 整体资金曲线图
    def view(self, data):
        xlabel = data['candle_begin_time']
        ylabel = data['equity_curve']
        plt.plot(xlabel, ylabel, color='r')
        plt.show()

# df = return2()          # 计算策略收益
index = back_index()    # 计算回测结果指标

# index.base_info(df)
# index.all_interest(df)
# index.simple_interest(df)
# index.simple_interest_month(df)
# index.max_retracement(df)
# index.win_rate(df)
# index.profit_loss_ratio(df)
# index.rate_risk_return(df)
# index.sharpe_ratio(df)
# index.max_profit(df)
# index.max_loss(df)
# index.max_continuous_loss(df)
# index.max_continuous_win(df)
# index.ave_have_time(df)

# index.view(df)
