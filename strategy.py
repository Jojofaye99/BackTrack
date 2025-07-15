import numpy as np
import pandas as pd
from indicators import calc_macd_hist, calc_atr
from scipy.signal import argrelextrema

def simulate_trades(df, use_cross_margin=True):
    """
    模拟交易函数：MACD 背离 + 关键K线 策略，支持做多/做空，止盈止损。
    """

    trades = []
    position = None
    entry_price = stop_loss = take_profit = None
    entry_time = None
    leverage = 100

    df['macd_hist'] = calc_macd_hist(df)
    df['atr'] = calc_atr(df)

    peaks = argrelextrema(df['macd_hist'].values, np.greater)[0]
    troughs = argrelextrema(df['macd_hist'].values, np.less)[0]

    i = 2
    while i < len(peaks):
        if position is not None:
            # 当前有持仓，不允许开新仓
            i += 1
            continue

        # ===== 顶背离（做空） =====
        idx1, idx2, idx3 = peaks[i - 2], peaks[i - 1], peaks[i]
        high1, high2, high3 = df['high'].iloc[[idx1, idx2, idx3]]
        hist1, hist2, hist3 = df['macd_hist'].iloc[[idx1, idx2, idx3]]

        if high1 < high2 < high3 and hist1 > hist2 > hist3 > 0:
            diff1 = abs((hist2 - hist1) / (abs(hist1) + 1e-9))
            diff2 = abs((hist3 - hist2) / (abs(hist2) + 1e-9))
            if diff1 >= 0.3 and diff2 >= 0.3:
                # 寻找关键K线（hist 由深变浅）
                for j in range(idx3, min(idx3 + 5, len(df) - 1)):
                    if df['macd_hist'].iloc[j] < df['macd_hist'].iloc[j - 1] and df['macd_hist'].iloc[j - 1] > 0:
                        key_idx = j
                        entry_idx = key_idx + 1
                        if entry_idx >= len(df):
                            break
                        entry_price = df['open'].iloc[entry_idx]
                        entry_time = df['datetime'].iloc[entry_idx]
                        stop_loss = df['high'].iloc[key_idx] + df['atr'].iloc[key_idx]
                        take_profit = entry_price - (stop_loss - entry_price)

                        trades.append({
                            'type': 'short',
                            'price': entry_price,
                            'time': entry_time,
                            'reason': '双顶背离+关键K线'
                        })
                        position = 'short'
                        break

        # ===== 底背离（做多） =====
        idx1, idx2, idx3 = troughs[i - 2], troughs[i - 1], troughs[i]
        low1, low2, low3 = df['low'].iloc[[idx1, idx2, idx3]]
        hist1, hist2, hist3 = df['macd_hist'].iloc[[idx1, idx2, idx3]]

        if low1 > low2 > low3 and hist1 < hist2 < hist3 < 0:
            diff1 = abs((hist2 - hist1) / (abs(hist1) + 1e-9))
            diff2 = abs((hist3 - hist2) / (abs(hist2) + 1e-9))
            if diff1 >= 0.3 and diff2 >= 0.3:
                for j in range(idx3, min(idx3 + 5, len(df) - 1)):
                    if df['macd_hist'].iloc[j] > df['macd_hist'].iloc[j - 1] and df['macd_hist'].iloc[j - 1] < 0:
                        key_idx = j
                        entry_idx = key_idx + 1
                        if entry_idx >= len(df):
                            break
                        entry_price = df['open'].iloc[entry_idx]
                        entry_time = df['datetime'].iloc[entry_idx]
                        stop_loss = df['low'].iloc[key_idx] - df['atr'].iloc[key_idx]
                        take_profit = entry_price + (entry_price - stop_loss)

                        trades.append({
                            'type': 'long',
                            'price': entry_price,
                            'time': entry_time,
                            'reason': '双底背离+关键K线'
                        })
                        position = 'long'
                        break

        i += 1

        # ===== 检查是否需要平仓 =====
        if position:
            for idx in range(entry_idx, len(df)):
                ts = df['datetime'].iloc[idx]
                liq_price = entry_price * (1 - 1 / leverage) if position == 'long' else entry_price * (1 + 1 / leverage)

                if position == 'long':
                    if not use_cross_margin and df['low'].iloc[idx] <= liq_price:
                        trades.append({'type': 'close', 'price': liq_price, 'time': ts, 'reason': 'liquidation'})
                        position = None
                        break
                    elif df['low'].iloc[idx] <= stop_loss:
                        trades.append({'type': 'close', 'price': stop_loss, 'time': ts, 'reason': 'stop_loss'})
                        position = None
                        break
                    elif df['high'].iloc[idx] >= take_profit:
                        trades.append({'type': 'close', 'price': take_profit, 'time': ts, 'reason': 'take_profit'})
                        position = None
                        break

                elif position == 'short':
                    if not use_cross_margin and df['high'].iloc[idx] >= liq_price:
                        trades.append({'type': 'close', 'price': liq_price, 'time': ts, 'reason': 'liquidation'})
                        position = None
                        break
                    elif df['high'].iloc[idx] >= stop_loss:
                        trades.append({'type': 'close', 'price': stop_loss, 'time': ts, 'reason': 'stop_loss'})
                        position = None
                        break
                    elif df['low'].iloc[idx] <= take_profit:
                        trades.append({'type': 'close', 'price': take_profit, 'time': ts, 'reason': 'take_profit'})
                        position = None
                        break

    return trades

'''
好的，以下是你目前所用的策略的**完整描述**，包括开仓逻辑、背离判断条件、止盈止损规则、以及资金管理与风险控制等。

---

## 🧠 策略名称：**MACD 双重背离 + 关键K线策略（高杠杆量化交易）**

---

### 📌 一、策略核心逻辑

本策略基于 **MACD柱状图的底/顶背离** 与 **K线结构识别关键K线** 的共振信号，结合 ATR 设置止盈止损，进行双向交易（做多/做空）。

---

### 📈 二、开仓逻辑

#### **1. 做多信号（多头建仓）**

需同时满足以下 3 个条件：

1. **K线低点连续创新低**
   最近两个低点价格逐渐降低（形成“下移”结构）。

2. **MACD 底背离确认**

   * MACD柱状图在**0轴下方**（负值）；
   * 最近两个红柱**波峰逐步抬高**；
   * 且后一个波峰较前一个至少**增加30%以上**（表示背离明显）。

3. **关键K线出现**

   * MACD柱子由深红色（背离前）变为浅红色（背离减弱）；
   * 第一个变浅的柱子所对应的K线，即为关键K线；
   * **下一根K线开盘价**作为开仓价格。

---

#### **2. 做空信号（空头建仓）**

需同时满足以下 3 个条件：

1. **K线高点连续创新高**
   最近两个高点价格逐渐抬高（形成“上移”结构）。

2. **MACD 顶背离确认**

   * MACD柱状图在**0轴上方**（正值）；
   * 最近两个绿柱**波峰逐步降低**；
   * 且后一个波峰较前一个**下降30%以上**。

3. **关键K线出现**

   * MACD柱子由深绿色变为浅绿色；
   * 第一个变浅的柱子所对应的K线即为关键K线；
   * **下一根K线开盘价**作为开仓价。

---

### 🎯 三、止盈 / 止损策略

#### 做多仓位：

* 止损价 = 关键K线最低点 - 当前周期 ATR
* 止盈价 = 开仓价 + (开仓价 - 止损价)  ⇒  固定 **1:1 风报比**

#### 做空仓位：

* 止损价 = 关键K线最高点 + 当前周期 ATR
* 止盈价 = 开仓价 - (止损价 - 开仓价)

---

### 🧮 四、资金管理与交易设置

* 初始本金：2000 USDT
* 每次开仓金额：**2% 本金**（即 40 USDT）
* 杠杆倍数：**100 倍**
* 进场手续费（市价单）：**0.6%**
* 出场手续费（限价单）：**0.2%**
* 强平费率：0.05%（仅逐仓模式下计算）
* 资金费率：0.0005% 每小时
* 最小成交量：0.0001 BTC

---

### 🔒 五、风险控制限制

* **仅允许一个仓位**同时存在（即平仓后才能再次开仓）。
* **背离必须连续发生两次**且满足背离强度差异条件：

  * 即两次连续背离波峰间 MACD 值差异需**大于 30%**；
  * 避免震荡区的弱背离信号干扰。

---

### 📊 六、回测记录输出字段

每笔交易记录包含：

* `entry_type`: long / short
* `entry_price`, `exit_price`
* `entry_time`, `exit_time`
* `qty`: 实际开仓张数
* `pnl`: 盈亏（未扣手续费）
* `net`: 实际盈亏（扣手续费、资金费）
* `balance`: 每笔交易后账户余额

---



'''