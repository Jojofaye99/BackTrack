import os
import time
import requests
import pandas as pd
from datetime import datetime

BASE_URL = 'https://www.okx.com'
KLINE_ENDPOINT = '/api/v5/market/history-candles'


# def fetch_kline(inst_id, bar='15m', after=None, limit=100):
#     params = {
#         'instId': inst_id,
#         'bar': bar,
#         'limit': str(limit),
#     }
#     if after:
#         params['after'] = str(after)  # 请求此时间戳之前更早的数据
#
#     url = BASE_URL + KLINE_ENDPOINT
#     resp = requests.get(url, params=params)
#     result = resp.json()
#     if result['code'] != '0':
#         raise Exception(f"API error: {result['msg']}")
#     return result['data']

import random

def fetch_kline(inst_id, bar='15m', after=None, limit=100, max_retries=5):
    params = {
        'instId': inst_id,
        'bar': bar,
        'limit': str(limit),
    }
    if after:
        params['after'] = str(after)

    url = BASE_URL + KLINE_ENDPOINT

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=10)
            result = resp.json()
            if result['code'] != '0':
                raise Exception(f"API error: {result['msg']}")
            return result['data']
        except (requests.exceptions.SSLError, requests.exceptions.RequestException) as e:
            wait_time = 2 + random.random() * 3
            print(f"[WARN] 请求失败（{e}），重试 {attempt+1}/{max_retries}，等待 {wait_time:.1f}s...")
            time.sleep(wait_time)

    raise Exception(f"[ERROR] 多次重试后仍请求失败: {url}")

def data_to_df(data):
    # 按官方文档列名完整写出
    columns = ['ts', 'open', 'high', 'low', 'close', 'vol', 'volCcy', 'volCcyQuote', 'confirm']
    df = pd.DataFrame(data, columns=columns)
    # 时间戳转int64
    df['ts'] = df['ts'].astype('int64')
    # 转为datetime格式列
    df['datetime'] = pd.to_datetime(df['ts'], unit='ms')
    # 数值列转float
    for col in ['open', 'high', 'low', 'close', 'vol', 'volCcy', 'volCcyQuote']:
        df[col] = df[col].astype(float)
    df['confirm'] = df['confirm'].astype(int)
    df = df.sort_values('ts').reset_index(drop=True)
    return df


def fetch_kline_until(inst_id, bar, start_datetime):
    print(f"\n>>> 开始拉取 {inst_id} - {bar} K线数据，直到 {start_datetime} ...")
    all_dfs = []

    # 初始 after_ts 设置为当前时间戳毫秒，表示从最新开始往更早拉
    after_ts = int(datetime.now().timestamp() * 1000)
    start_ts = int(start_datetime.timestamp() * 1000)

    while True:
        data = fetch_kline(inst_id, bar, after=after_ts, limit=100)
        if not data:
            print("[INFO] 没有更多数据，停止拉取。")
            break

        df = data_to_df(data)
        all_dfs.append(df)

        # 找当前批次最早时间戳
        earliest_ts = df['ts'].min()

        print(f"[INFO] 拉取数据范围: {df['datetime'].min()} ~ {df['datetime'].max()}，条数：{len(df)}")

        # 如果最早时间戳已经小于等于目标时间戳，停止拉取
        if earliest_ts <= start_ts:
            print("[INFO] 已达到起始时间，停止拉取。")
            break

        # 更新 after_ts，向更早的数据拉取，取最早时间戳减1毫秒
        after_ts = earliest_ts - 1

        # 避免请求过快被限流
        time.sleep(0.2)

    if all_dfs:
        # 合并所有批次数据，去重，按时间排序
        df_all = pd.concat(all_dfs).drop_duplicates(subset=['ts']).sort_values('ts').reset_index(drop=True)
        # 删除原ts列，保留datetime作为时间列
        df_all = df_all.drop(columns=['ts'])
        return df_all
    else:
        return pd.DataFrame()


def save_df(df, inst_id, bar):
    os.makedirs("data", exist_ok=True)
    filename = f"data/{inst_id.replace('-', '_')}_{bar}.csv"
    df.to_csv(filename, index=False)
    print(f"[OK] 数据保存到 {filename}")


if __name__ == "__main__":
    inst_id = 'BTC-USDT-SWAP'

    # bars = ['15m', '30m', '1H', '2H', '4H']
    bars = ['5m']
    start_datetime = datetime(2024, 6, 1)

    for bar in bars:
        df = fetch_kline_until(inst_id, bar, start_datetime)
        if not df.empty:
            save_df(df, inst_id, bar)
        else:
            print(f"[WARN] {bar} 无数据或拉取失败。")
