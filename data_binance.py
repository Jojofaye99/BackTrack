import requests
import pandas as pd
import time
import os
from datetime import datetime

# 已经作废 币安api

# ETH
# ETHUSDT 15m 已经抓取
# ETHUSDT 30m 已经抓取
# ETHUSDT 1h 已经抓取
# ETHUSDT 2h 已经抓取
# ETHUSDT 4h 已经抓取

# BTC
#

symbol = 'BTCUSDT'
interval = '4h'
limit = 1000
start_datetime = datetime(2021, 1, 1)
end_datetime = datetime(2025, 6, 15)
csv_file = 'btcusdt_4h_20210101_20250615.csv'


def get_timestamp(dt):
    return int(dt.timestamp() * 1000)


def fetch_klines(symbol, interval, start_ts, end_ts):
    url = 'https://api.binance.com/api/v3/klines'
    all_data = []
    page = 1

    while start_ts < end_ts:
        for attempt in range(3):  # 最多重试3次
            try:
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit,
                    'startTime': start_ts
                }
                readable_time = datetime.fromtimestamp(start_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[第 {page} 页] 正在抓取：{readable_time} 开始的 1000 条数据...")

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data:
                    print("✅ 已无更多数据可抓取，结束。")
                    return

                # 转换为 DataFrame
                df = pd.DataFrame(data, columns=[
                    'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
                    'Close time', 'Quote asset volume', 'Number of trades',
                    'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
                ])
                df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
                df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
                float_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                df[float_cols] = df[float_cols].astype(float)

                # 保存
                mode = 'a' if os.path.exists(csv_file) else 'w'
                header = not os.path.exists(csv_file)
                df.to_csv(csv_file, mode=mode, index=False, header=header)

                # 更新时间
                last_time = data[-1][6]
                start_ts = last_time + 1
                page += 1
                time.sleep(0.3)
                break  # 成功就退出 retry 循环

            except Exception as e:
                print(f"⚠ 第 {attempt + 1} 次请求失败，错误：{e}")
                time.sleep(5)
        else:
            print("❌ 连续三次失败，终止程序")
            break

# ✅ 如果 CSV 存在，自动读取最后一条时间作为断点
if os.path.exists(csv_file):
    existing_df = pd.read_csv(csv_file)
    if not existing_df.empty:
        last_close_time = pd.to_datetime(existing_df['Close time'].iloc[-1])
        start_datetime = last_close_time + pd.Timedelta(milliseconds=1)
        print(f"📌 断点续传，从上次结束时间继续抓：{start_datetime}")

start_ts = get_timestamp(start_datetime)
end_ts = get_timestamp(end_datetime)
fetch_klines(symbol, interval, start_ts, end_ts)

print("✅ 全部抓取完成。")
