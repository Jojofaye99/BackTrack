# ✅ 完整 backtest.py，满足你的所有规则说明：
# - 开仓手续费计入 1% 资金上限；
# - 平仓、持仓、强平手续费不计入保证金；
# - 加入 balance_after 字段；
# - 支持设置起始时间（如从 2024 年开始回测）；
# - 输出净值曲线及统计数据。

import os
import math
import pandas as pd
from indicators import calc_ma10, calc_ema_of_ma, calc_rsi
from strategy import simulate_trades
from utils import analyze_results


def load_and_prepare(filepath):
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)

    df['MA10'] = calc_ma10(df)
    df['EMA10'] = calc_ema_of_ma(df)
    df['RSI'] = calc_rsi(df)

    df.dropna(inplace=True)
    return df

def run_backtest_for_period(name, filepath, start_date=None):
    df = load_and_prepare(filepath)

    if start_date:
        df = df[df['datetime'] >= pd.to_datetime(start_date)].reset_index(drop=True)

    trades = simulate_trades(df)

    results = []
    initial_balance = 1500
    balance = initial_balance
    leverage = 100
    open_percent = 0.005
    min_qty = 0.0001
    liquidation_threshold = 0.01

    entry_fee_rate = 0.0006
    exit_fee_rate = 0.0006
    liquidation_fee_rate = 0.0005
    funding_rate_hourly = 0.000005

    partial_count = 0
    full_count = 0

    i = 0
    while i < len(trades) - 1:
        entry = trades[i]
        exit_ = trades[i + 1]

        entry_price = entry['price']
        exit_price = exit_['price']
        direction = entry['type']
        entry_time = entry['time']
        exit_time = exit_['time']
        reason = exit_.get('reason', 'strategy')
        duration_hours = (exit_time - entry_time).total_seconds() / 3600

        capital = balance * open_percent
        max_contract_value = (capital / (1 + entry_fee_rate)) * leverage
        qty = math.floor((max_contract_value / entry_price) / min_qty) * min_qty
        if qty < min_qty:
            i += 2
            continue

        notional = qty * entry_price
        fee_entry = notional * entry_fee_rate
        fee_exit = qty * exit_price * exit_fee_rate
        fee_funding = notional * funding_rate_hourly * duration_hours

        is_liquidated = False
        if direction == 'long':
            pnl = (exit_price - entry_price) * qty
            if exit_price <= entry_price * (1 - liquidation_threshold):
                is_liquidated = True
        else:
            pnl = (entry_price - exit_price) * qty
            if exit_price >= entry_price * (1 + liquidation_threshold):
                is_liquidated = True

        if is_liquidated:
            pnl = -capital
            fee_exit = notional * liquidation_fee_rate
            reason = "liquidation"

        net_pnl = pnl - fee_exit - fee_funding

        # ✅ 部分止盈
        if 'partial' in reason:
            net_pnl /= 2
            partial_count += 1
        else:
            full_count += 1

        balance += net_pnl

        results.append({
            "entry_time": entry_time,
            "exit_time": exit_time,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": qty,
            "contract_value": notional,
            "fee_entry": fee_entry,
            "fee_exit": fee_exit,
            "total_fee": fee_entry + fee_exit,
            "return": net_pnl,
            "reason": reason,
            "balance_after": balance
        })

        i += 2

    # === 结果处理 ===
    result_df = pd.DataFrame(results)
    trade_count = len(result_df)

    if trade_count == 0:
        print(f"⚠️ 无交易记录：{name}")
        return

    # === 回测统计 ===
    if 'return' in result_df.columns:
        total_return = result_df['return'].sum()
        avg_return = result_df['return'].mean()
        win_rate = (result_df['return'] > 0).mean()
    else:
        # 使用 balance_after 差值近似
        returns = result_df['balance_after'].diff().dropna()
        total_return = returns.sum()
        avg_return = returns.mean() if not returns.empty else 0
        win_rate = (returns > 0).mean() if not returns.empty else 0

    equity_curve = result_df['balance_after']
    drawdowns = equity_curve - equity_curve.cummax()
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0

    liquidation_count = (result_df['reason'] == 'liquidation').sum()
    liquidation_ratio = liquidation_count / trade_count if trade_count > 0 else 0

    total_fees = result_df['fee_entry'].sum() + result_df['fee_exit'].sum()

    stats = {
        "总收益": round(total_return, 4),
        "平均单笔收益": round(avg_return, 4),
        "最大回撤": round(max_drawdown, 4),
        "胜率": round(win_rate * 100, 2),
        "交易次数": trade_count,
        "爆仓次数": liquidation_count,
        "爆仓占比": f"{round(liquidation_ratio * 100, 2)}%",
        "部分止盈次数": partial_count,
        "完全止盈次数": full_count,
        "总进出场手续费": round(total_fees, 4)
    }

    # === 保存结果 ===
    os.makedirs("backtest_results", exist_ok=True)
    result_df.to_csv(f"backtest_results/{name}_results.csv", index=False)

    try:
        analyze_results(result_df, save_path=f"backtest_results/{name}_equity.png")
    except Exception as e:
        print(f"⚠️ 净值图绘制失败：{e}")

    print(f"\n✅ 完成回测：{name}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()


def run_all(start_date='2024-07-01'):  # 2025-06-16
    periods = ['5m']
    # periods = ['15m', '30m', '1H', '2H', '4H']
    for p in periods:
        filepath = f'data/BTC_USDT_SWAP_{p}_UTC.csv'
        #filepath = f'data/BTC_USDT_SWAP_{p}.csv'
        name = f'btc_{p}'
        if os.path.exists(filepath):
            run_backtest_for_period(name, filepath, start_date=start_date)
        else:
            print(f"❌ 缺失数据文件：{filepath}")


if __name__ == '__main__':
    run_all()
