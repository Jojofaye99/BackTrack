import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# 设置中文字体和负号显示
matplotlib.rcParams['font.family'] = 'SimHei'
matplotlib.rcParams['axes.unicode_minus'] = False


def analyze_results(result_df: pd.DataFrame, save_path: str = None):
    """
    分析回测结果：
    - 累计收益（净值）
    - 胜率
    - 最大回撤
    - 总收益、平均收益、交易次数
    - 可视化账户净值曲线
    """
    if result_df.empty:
        print("⚠️ 回测结果为空，无法分析")
        return {
            "总收益": 0,
            "平均单笔收益": 0,
            "最大回撤": 0,
            "胜率": 0,
            "交易次数": 0
        }

    # === 使用 balance_after 计算累计净值曲线
    result_df['cumulative_return'] = result_df['balance_after']

    # === 计算基础指标 ===
    trade_count = len(result_df)

    # 总收益 = 最终余额 - 初始资金
    initial_balance = 1500
    total_return = result_df['balance_after'].iloc[-1] - initial_balance

    # 平均收益（从 return 字段取，如果不存在则用 diff(balance_after)）
    if 'return' in result_df.columns:
        avg_return = result_df['return'].mean()
        win_rate = (result_df['return'] > 0).mean()
    else:
        returns = result_df['balance_after'].diff().dropna()
        avg_return = returns.mean()
        win_rate = (returns > 0).mean()

    # 最大回撤
    equity_curve = result_df['balance_after']
    drawdowns = equity_curve - equity_curve.cummax()
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0

    # === 绘图 ===
    plt.figure(figsize=(12, 6))
    plt.plot(result_df['exit_time'], result_df['balance_after'], label='账户净值', color='blue')
    plt.title('账户净值曲线')
    plt.xlabel('时间')
    plt.ylabel('余额')
    plt.grid(True)
    plt.legend()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path)
    plt.close()

    # === 返回统计数据 ===
    stats = {
        "总收益": round(total_return, 4),
        "平均单笔收益": round(avg_return, 4),
        "最大回撤": round(max_drawdown, 4),
        "胜率": round(win_rate * 100, 2),
        "交易次数": trade_count
    }

    return stats
