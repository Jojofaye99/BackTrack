import os
import time
import random
import requests
import pandas as pd
from datetime import datetime

BASE_URL = 'https://www.okx.com'
KLINE_ENDPOINT = '/api/v5/market/history-candles'


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
        except (requests.exceptions.RequestException) as e:
            wait_time = 2 + random.random() * 3
            print(f"[WARN] 请求失败（{e}），重试 {attempt+1}/{max_retries}，等待 {wait_time:.1f}s...")
            time.sleep(wait_time)

    raise Exception(f"[ERROR] 多次重试后仍请求失败: {url}")


def data_to_df(data):
    columns = ['ts', 'open', 'high', 'low', 'close', 'vol', 'volCcy', 'volCcyQuote', 'confirm']
    df = pd.DataFrame(data, columns=columns)
    df['ts'] = df['ts'].astype('int64')
    df['datetime'] = pd.to_datetime(df['ts'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'vol', 'volCcy', 'volCcyQuote']:
        df[col] = df[col].astype(float)
    df['confirm'] = df['confirm'].astype(int)
    df = df.sort_values('ts').reset_index(drop=True)
    return df


def fetch_kline_until(inst_id, bar, start_datetime, temp_filename):
    print(f"\n>>> 开始拉取 {inst_id} - {bar} K线数据，直到 {start_datetime} ...")
    all_dfs = []

    # 先判断是否存在中断的临时文件
    if os.path.exists(temp_filename):
        print(f"[INFO] 检测到上次中断记录，读取临时文件继续拉取：{temp_filename}")
        df_temp = pd.read_csv(temp_filename, parse_dates=['datetime'])
        all_dfs.append(df_temp)
        after_ts = int(df_temp['datetime'].min().timestamp() * 1000) - 1
    else:
        after_ts = int(datetime.now().timestamp() * 1000)

    start_ts = int(start_datetime.timestamp() * 1000)

    try:
        while True:
            data = fetch_kline(inst_id, bar, after=after_ts, limit=100)
            if not data:
                print("[INFO] 没有更多数据，停止拉取。")
                break

            df = data_to_df(data)
            all_dfs.append(df)

            earliest_ts = df['ts'].min()
            print(f"[INFO] 拉取数据范围: {df['datetime'].min()} ~ {df['datetime'].max()}，条数：{len(df)}")

            if earliest_ts <= start_ts:
                print("[INFO] 已达到起始时间，停止拉取。")
                break

            after_ts = earliest_ts - 1
            time.sleep(1)  # 降低频率，避免封锁

            # 实时保存中间文件
            df_temp = pd.concat(all_dfs).drop_duplicates(subset=['ts']).sort_values('ts').reset_index(drop=True)
            df_temp.to_csv(temp_filename, index=False)
    except Exception as e:
        print(f"[ERROR] 拉取过程中出现异常：{e}")
        print(f"[INFO] 当前已拉取数据已保存到临时文件：{temp_filename}")
        return None

    if all_dfs:
        df_all = pd.concat(all_dfs).drop_duplicates(subset=['ts']).sort_values('ts').reset_index(drop=True)
        df_all = df_all.drop(columns=['ts'])
        return df_all
    else:
        return pd.DataFrame()


def save_df(df, inst_id, bar, temp_filename):
    os.makedirs("data", exist_ok=True)
    filename = f"data/{inst_id.replace('-', '_')}_{bar}.csv"
    df.to_csv(filename, index=False)
    print(f"[OK] 数据保存到 {filename}")
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        print(f"[OK] 清理临时文件：{temp_filename}")


if __name__ == "__main__":
    inst_id = 'BTC-USDT-SWAP'
    bars = ['5m']
    start_datetime = datetime(2024, 6, 1)

    for bar in bars:
        temp_filename = f"data/{inst_id.replace('-', '_')}_{bar}_temp.csv"
        df = fetch_kline_until(inst_id, bar, start_datetime, temp_filename)
        if df is not None and not df.empty:
            save_df(df, inst_id, bar, temp_filename)
        else:
            print(f"[WARN] {bar} 无数据或拉取失败，请稍后重试。")
