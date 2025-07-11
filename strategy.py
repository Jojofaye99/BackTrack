def simulate_trades(df):
    trades = []
    position = None
    entry_price = entry_time = stop_loss = take_profit = None
    leverage = 100

    fast = df['MA10']     # 快线
    slow = df['EMA10']    # 慢线
    rsi = df['RSI']

    retraced_long = False
    retraced_short = False

    golden_cross_active = False
    golden_cross_index = -1
    dead_cross_active = False
    dead_cross_index = -1

    for i in range(2, len(df) - 1):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        next_row = df.iloc[i + 1]

        open_, high, low, close = row['open'], row['high'], row['low'], row['close']
        ma = fast.iloc[i]
        ema = slow.iloc[i]
        rsi_val = rsi.iloc[i]

        body_high = max(open_, close)
        body_low = min(open_, close)

        golden_cross = fast.iloc[i - 1] <= slow.iloc[i - 1] and fast.iloc[i] > slow.iloc[i]
        dead_cross = fast.iloc[i - 1] >= slow.iloc[i - 1] and fast.iloc[i] < slow.iloc[i]

        # 检测交叉信号
        if golden_cross:
            golden_cross_active = True
            golden_cross_index = i
            retraced_long = False

        if dead_cross:
            dead_cross_active = True
            dead_cross_index = i
            retraced_short = False

        # 保持交叉状态，只要趋势未反转
        if golden_cross_index >= 0 and i > golden_cross_index:
            golden_cross_active = fast.iloc[i] > slow.iloc[i]

        if dead_cross_index >= 0 and i > dead_cross_index:
            dead_cross_active = fast.iloc[i] < slow.iloc[i]

        # Debug 打印
        # if str(row['datetime']) in ['2025-07-01 10:40:00']:
        #     print(f"\n===== Debug @ {row['datetime']} =====")
        #     print(f"open={open_}, close={close}, high={high}, low={low}")
        #     print(f"MA10(fast): prev={fast.iloc[i-1]:.2f}, curr={ma:.2f}")
        #     print(f"EMA10(slow): prev={slow.iloc[i-1]:.2f}, curr={ema:.2f}")
        #     print(f"RSI={rsi_val:.2f}")
        #     print(f"body_low={body_low}, body_high={body_high}")
        #     print(f"is_bullish_candle={close > open_}")
        #     print(f"golden_cross={golden_cross}, dead_cross={dead_cross}")
        #     print(f"golden_cross_active={golden_cross_active}, dead_cross_active={dead_cross_active}")
        #     print(f"retraced_long={retraced_long}, retraced_short={retraced_short}")
        #     print(f"above_ma_ema={body_low > ma and body_low > ema}")
        #     print(f"below_ma_ema={body_high < ma and body_high < ema}")
        #     print(f"RSI in 50-70={50 <= rsi_val <= 70}, RSI in 30-50={30 <= rsi_val <= 50}")
        #     print(f"position={position}")

        # ================= 多单逻辑 =================
        if position is None and golden_cross_active and i > golden_cross_index:
            cond1_long = close > open_ and body_low > ma and body_low > ema and 50 <= rsi_val <= 70
            cond2_long = retraced_long and close > open_ and body_low > ma and body_low > ema and 50 <= rsi_val <= 70

            if cond1_long or cond2_long:
                position = 'long'
                entry_price = next_row['open']
                entry_time = next_row['datetime']
                stop_loss = ma
                take_profit = entry_price + 1.5 * (entry_price - stop_loss)
                trades.append({
                    'type': 'long', 'price': entry_price, 'time': entry_time,
                    'entry_reason': 'condition_1' if cond1_long else 'condition_2'
                })
                golden_cross_active = False
                retraced_long = False
                dead_cross_active = False
                retraced_short = False
                continue

            if fast.iloc[i - 1] > slow.iloc[i - 1] and fast.iloc[i] > slow.iloc[i] and close < ema:
                retraced_long = True

        # ================= 空单逻辑 =================
        if position is None and dead_cross_active and i > dead_cross_index:
            cond1_short = close < open_ and body_high < ma and body_high < ema and 30 <= rsi_val <= 50
            cond2_short = retraced_short and close < open_ and body_high < ma and body_high < ema and 30 <= rsi_val <= 50

            if cond1_short or cond2_short:
                position = 'short'
                entry_price = next_row['open']
                entry_time = next_row['datetime']
                stop_loss = ma
                take_profit = entry_price - 1.5 * (stop_loss - entry_price)
                trades.append({
                    'type': 'short', 'price': entry_price, 'time': entry_time,
                    'entry_reason': 'condition_1' if cond1_short else 'condition_2'
                })
                golden_cross_active = False
                retraced_long = False
                dead_cross_active = False
                retraced_short = False
                continue

            if fast.iloc[i - 1] < slow.iloc[i - 1] and fast.iloc[i] < slow.iloc[i] and close > ema:
                retraced_short = True

        # ================= 持仓中止损止盈爆仓处理 =================
        if position:
            next_price = next_row['open']
            next_time = next_row['datetime']
            liq_price = entry_price * (1 - 1 / leverage) if position == 'long' else entry_price * (1 + 1 / leverage)

            if (position == 'long' and row['low'] <= liq_price) or (position == 'short' and row['high'] >= liq_price):
                trades.append({'type': 'close', 'price': liq_price, 'time': next_time, 'reason': 'liquidation'})
                position = None
                continue

            if (position == 'long' and row['low'] <= stop_loss) or (position == 'short' and row['high'] >= stop_loss):
                trades.append({'type': 'close', 'price': stop_loss, 'time': next_time, 'reason': 'stop_loss'})
                position = None
                continue

            if (position == 'long' and row['high'] >= take_profit) or (position == 'short' and row['low'] <= take_profit):
                trades.append({'type': 'close', 'price': take_profit, 'time': next_time, 'reason': 'take_profit'})
                position = None
                continue

    return trades