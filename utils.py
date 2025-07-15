import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

matplotlib.rcParams['font.family'] = 'SimHei'
matplotlib.rcParams['axes.unicode_minus'] = False

def analyze_results(result_df: pd.DataFrame, save_path: str = None):
    if result_df.empty:
        print("⚠️ 回测结果为空，无法分析")
        return {}

    if 'balance' not in result_df.columns or 'exit_time' not in result_df.columns:
        raise ValueError("缺少必要字段: balance 或 exit_time")

    # 净值曲线
    plt.figure(figsize=(12, 6))
    plt.plot(result_df['exit_time'], result_df['balance'], label='账户净值', color='blue')
    plt.title('账户净值曲线')
    plt.xlabel('时间')
    plt.ylabel('余额')
    plt.grid(True)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M'))
    plt.gcf().autofmt_xdate()
    if save_path:
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path)
        except Exception as e:
            print(f"❌ 净值图保存失败: {e}")
    plt.close()

    # 每笔交易盈亏柱状图
    plt.figure(figsize=(12, 4))
    result_df['net'].plot(kind='bar', color=result_df['net'].apply(lambda x: 'g' if x > 0 else 'r'))
    plt.title("每笔交易盈亏")
    plt.ylabel("盈亏")
    plt.grid(True)
    plt.tight_layout()
    if save_path:
        bar_path = save_path.replace("_equity.png", "_trades.png")
        plt.savefig(bar_path)
    plt.close()

    # 收益分布直方图
    plt.figure(figsize=(8, 4))
    result_df['net'].hist(bins=50, color='skyblue', edgecolor='black')
    plt.title("收益分布直方图")
    plt.xlabel("盈亏")
    plt.ylabel("频次")
    plt.grid(True)
    plt.tight_layout()
    if save_path:
        hist_path = save_path.replace("_equity.png", "_hist.png")
        plt.savefig(hist_path)
    plt.close()

    return {
        "总收益": round(result_df['net'].sum(), 4),
        "平均收益": round(result_df['net'].mean(), 4),
        "最大回撤": round((result_df['balance'] - result_df['balance'].cummax()).min(), 4),
        "胜率": round((result_df['net'] > 0).mean() * 100, 2),
        "交易次数": len(result_df)
    }