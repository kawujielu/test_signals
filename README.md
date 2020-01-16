# test_signals
    策略说明：
    用python实现 通过计算市场的波动率，把市场划分为震荡和趋势两种走势
    入场条件：
    震荡市中，采用开盘区间突破进场
    趋势市中，采用布林通道突破进场
    出场条件：
    震荡市中，出场为反手信号和ATR保护性止损
    趋势市中，出场为反手信号和均线出场
    系统要素：
    1、波动率
    2、关键价格
    3、布林通道
    4、真实波幅
    5、出场均线

    其他说明：
    回测数据采用huobi币币交易对ETH/USDT
    
    数据文件是 ethusdt.h5
    策略逻辑在 Signals.py 文件中
    指标在 Target.py 文件中
    回测指标在 Return2.py 文件中
    运行Return_swing.py和Return_trend.py可以展示策略回测结果。在文件中，可以修改42行来修改K线周期，修改46行来修改策略参数
    运行huobi_swing.py和huobi_trend.py可以实盘运行策略，需要在37、38行添加账户apikey和secret
    
    已通过实盘测试
    
    
