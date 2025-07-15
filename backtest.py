import os
import math
import pandas as pd
from strategy import simulate_trades
from utils import analyze_results

def load_data(fp, start_date=None):
    df = pd.read_csv(fp, parse_dates=['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)
    if start_date:
        df = df[df['datetime'] >= pd.to_datetime(start_date)]
    return df

def run_backtest(name, fp, start_date=None, use_cross_margin=True):
    df = load_data(fp, start_date)
    trades = simulate_trades(df, use_cross_margin=use_cross_margin)

    initial_balance = 2000.0
    balance = initial_balance
    open_amount = 40.0
    leverage = 100
    fee_e = 0.006  # 开仓手续费（0.6%）
    fee_x = 0.002  # 平仓手续费（0.2%）
    fund_rate = 0.000005  # 每小时资金费率
    min_qty = 0.0001

    records = []
    liq_count = 0
    max_drawdown_duration = 0
    drawdown_start_time = None

    win_trades, loss_trades = [], []
    consecutive_losses = 0
    max_consecutive_losses = 0

    for i in range(0, len(trades) - 1, 2):
        e, x = trades[i], trades[i + 1]

        cap = open_amount
        effective_cap = cap / (1 + fee_e)
        qty = math.floor((effective_cap * leverage) / e['price'] / min_qty) * min_qty
        if qty < min_qty:
            continue

        notional = qty * e['price']
        fe = notional * fee_e
        fx = qty * x['price'] * fee_x
        dur = (x['time'] - e['time']).total_seconds() / 3600
        ff = notional * fund_rate * dur

        pnl = (x['price'] - e['price']) * qty if e['type'] == 'long' else (e['price'] - x['price']) * qty

        liq_price = e['price'] * (1 - 1 / leverage) if e['type'] == 'long' else e['price'] * (1 + 1 / leverage)
        is_liq = (e['type'] == 'long' and x['price'] <= liq_price) or (e['type'] == 'short' and x['price'] >= liq_price)
        if is_liq and not use_cross_margin:
            pnl = -cap
            fx = qty * x['price'] * 0.005
            x['reason'] = 'liquidation'
            liq_count += 1

        net = pnl - fx - ff
        balance += net

        if net > 0:
            win_trades.append(net)
            consecutive_losses = 0
        else:
            loss_trades.append(abs(net))
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        entry_time = pd.to_datetime(e['time'])
        exit_time = pd.to_datetime(x['time'])

        records.append({
            'entry_type': e['type'],
            'exit_reason': x['reason'],
            'entry_price': e['price'],
            'exit_price': x['price'],
            'entry_time': entry_time,
            'exit_time': exit_time,
            'qty': qty,
            'pnl': round(pnl, 4),
            'net': round(net, 4),
            'balance': round(balance, 4)
        })

    df_r = pd.DataFrame(records)
    if df_r.empty:
        print(f"⚠️ 无交易: {name}")
        return

    # 盈亏比
    avg_win = sum(win_trades) / len(win_trades) if win_trades else 0
    avg_loss = sum(loss_trades) / len(loss_trades) if loss_trades else 0
    profit_factor = round(avg_win / avg_loss, 2) if avg_loss > 0 else float('inf')

    # 净值回撤时间统计
    eq = df_r['balance']
    max_balance = eq[0]
    drawdown_time = 0
    current_duration = 0
    for t, b in zip(df_r['exit_time'], eq):
        if b >= max_balance:
            max_balance = b
            current_duration = 0
        else:
            current_duration += 1
            drawdown_time = max(drawdown_time, current_duration)

    total = df_r['net'].sum()
    avg = df_r['net'].mean()
    win = (df_r['net'] > 0).mean() * 100
    dd = (df_r['balance'] - df_r['balance'].cummax()).min()

    stats = {
        '模式': '全仓（Cross）' if use_cross_margin else '逐仓（Isolated）',
        '初始本金': initial_balance,
        '交易次数': len(df_r),
        '总收益': round(total, 4),
        '平均盈亏': round(avg, 4),
        '胜率': f"{win:.2f}%",
        '最大回撤': round(dd, 4),
        '最大连续亏损次数': max_consecutive_losses,
        '最大回撤周期数': drawdown_time,
        '盈亏比（Profit Factor）': profit_factor,
        '爆仓次数': liq_count,
    }

    os.makedirs('results', exist_ok=True)
    df_r.to_csv(f"results/{name}_results.csv", index=False)

    try:
        analyze_results(df_r, save_path=f"results/{name}_equity.png")
    except Exception as e:
        print(f"⚠️ 净值图失败：{e}")

    print(f"\n✅ 完成回测：{name}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()

def run_all(start_date='2024-07-01', use_cross_margin=True):
    periods = ['5m']
    for p in periods:
        filepath = f'data/BTC_USDT_SWAP_{p}_UTC.csv'
        name = f'btc_{p}'
        if os.path.exists(filepath):
            run_backtest(name, filepath, start_date=start_date, use_cross_margin=use_cross_margin)
        else:
            print(f"❌ 缺失数据文件：{filepath}")

if __name__ == '__main__':
    run_all(start_date='2024-07-01', use_cross_margin=True)