# 将okx 拉下的数据往后延8小时
import pandas as pd
from datetime import timedelta
import os

def shift_kline_datetime(file_path, hours=8, output_suffix='_UTC'):
    # 读取原CSV
    df = pd.read_csv(file_path, parse_dates=['datetime'])

    # 将时间减去指定小时数（默认8小时）
    df['datetime'] = df['datetime'] + timedelta(hours=hours)

    # 生成新文件名
    base, ext = os.path.splitext(file_path)
    output_path = base + output_suffix + ext

    # 保存新CSV
    df.to_csv(output_path, index=False)
    print(f"[OK] 调整后的数据保存为：{output_path}")

# 使用示例
if __name__ == "__main__":
    input_file = 'E:/Python_study/BTC/data/BTC_USDT_SWAP_5m.csv'  # 替换为你的实际文件路径
    shift_kline_datetime(input_file)
