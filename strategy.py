import numpy as np
import pandas as pd
from indicators import calc_macd_hist, calc_atr
from scipy.signal import argrelextrema

def simulate_trades(df, use_cross_margin=True, sl_factor=1, tp_factor=1):
    trades = []
    position = None
    entry_price = stop_loss = take_profit = None
    entry_time = None
    entry_idx = None
    leverage = 100

    # === 计算指标 ===
    df['macd_hist'] = calc_macd_hist(df)
    df['atr'] = calc_atr(df)

    peaks = argrelextrema(df['macd_hist'].values, np.greater)[0]
    troughs = argrelextrema(df['macd_hist'].values, np.less)[0]

    # 标记所有满足开仓条件的索引点
    short_signals = []
    long_signals = []

    # === 预处理空头信号 ===
    for i in range(2, len(peaks)):
        try:
            idx1, idx2, idx3 = peaks[i - 2], peaks[i - 1], peaks[i]
            high1, high2, high3 = df['high'].iloc[[idx1, idx2, idx3]]
            hist1, hist2, hist3 = df['macd_hist'].iloc[[idx1, idx2, idx3]]

            if high1 < high2 < high3 and hist1 > hist2 > hist3 > 0:
                diff1 = abs((hist2 - hist1) / (abs(hist1) + 1e-9))
                diff2 = abs((hist3 - hist2) / (abs(hist2) + 1e-9))
                if diff1 >= 0.3 and diff2 >= 0.3:
                    for j in range(idx3, min(idx3 + 5, len(df))):
                        if df['macd_hist'].iloc[j] < df['macd_hist'].iloc[j - 1] and df['macd_hist'].iloc[j - 1] > 0:
                            short_signals.append(j + 1)
                            break
        except:
            continue

    # === 预处理多头信号 ===
    for i in range(2, len(troughs)):
        try:
            idx1, idx2, idx3 = troughs[i - 2], troughs[i - 1], troughs[i]
            low1, low2, low3 = df['low'].iloc[[idx1, idx2, idx3]]
            hist1, hist2, hist3 = df['macd_hist'].iloc[[idx1, idx2, idx3]]

            if low1 > low2 > low3 and hist1 < hist2 < hist3 < 0:
                diff1 = abs((hist2 - hist1) / (abs(hist1) + 1e-9))
                diff2 = abs((hist3 - hist2) / (abs(hist2) + 1e-9))
                if diff1 >= 0.3 and diff2 >= 0.3:
                    for j in range(idx3, min(idx3 + 5, len(df))):
                        if df['macd_hist'].iloc[j] > df['macd_hist'].iloc[j - 1] and df['macd_hist'].iloc[j - 1] < 0:
                            long_signals.append(j + 1)
                            break
        except:
            continue

    # === 主循环 ===
    i = 0
    while i < len(df):
        # === 当前持仓 ===
        if position:
            ts = df['datetime'].iloc[i]
            h = df['high'].iloc[i]
            l = df['low'].iloc[i]
            liq_price = entry_price * (1 - 1 / leverage) if position == 'long' else entry_price * (1 + 1 / leverage)

            # 强平
            if not use_cross_margin:
                if (position == 'long' and l <= liq_price) or (position == 'short' and h >= liq_price):
                    trades.append({'type': 'close', 'price': liq_price, 'time': ts, 'reason': 'liquidation'})
                    position = None
                    continue

            # 止盈止损
            if position == 'long':
                if l <= stop_loss:
                    trades.append({'type': 'close', 'price': stop_loss, 'time': ts, 'reason': 'stop_loss'})
                    position = None
                elif h >= take_profit:
                    trades.append({'type': 'close', 'price': take_profit, 'time': ts, 'reason': 'take_profit'})
                    position = None
            elif position == 'short':
                if h >= stop_loss:
                    trades.append({'type': 'close', 'price': stop_loss, 'time': ts, 'reason': 'stop_loss'})
                    position = None
                elif l <= take_profit:
                    trades.append({'type': 'close', 'price': take_profit, 'time': ts, 'reason': 'take_profit'})
                    position = None
            i += 1
            continue

        # === 无持仓时检查开仓信号 ===
        if i in short_signals:
            entry_idx = i
            if entry_idx >= len(df): break
            entry_price = df['open'].iloc[entry_idx]
            entry_time = df['datetime'].iloc[entry_idx]
            atr = df['atr'].iloc[entry_idx - 1]
            stop_loss = df['high'].iloc[entry_idx - 1] + atr * sl_factor
            take_profit = entry_price - (stop_loss - entry_price) * (tp_factor / sl_factor)

            trades.append({'type': 'short', 'price': entry_price, 'time': entry_time, 'reason': 'MACD 顶背离 + 关键K线'})
            position = 'short'

        elif i in long_signals:
            entry_idx = i
            if entry_idx >= len(df): break
            entry_price = df['open'].iloc[entry_idx]
            entry_time = df['datetime'].iloc[entry_idx]
            atr = df['atr'].iloc[entry_idx - 1]
            stop_loss = df['low'].iloc[entry_idx - 1] - atr * sl_factor
            take_profit = entry_price + (entry_price - stop_loss) * (tp_factor / sl_factor)

            trades.append({'type': 'long', 'price': entry_price, 'time': entry_time, 'reason': 'MACD 底背离 + 关键K线'})
            position = 'long'

        i += 1

    return trades
