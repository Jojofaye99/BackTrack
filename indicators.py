import pandas as pd
import ta


# BBI (默认：8, 13, 21, 34)
def calc_bbi(df: pd.DataFrame, windows=(8, 13, 21, 34)) -> pd.Series:
    bbi = sum(df['close'].rolling(w).mean() for w in windows) / len(windows)
    return bbi


# MACD
def calc_macd(df: pd.DataFrame):
    macd = ta.trend.MACD(close=df['close'])  # 默认 fast=12, slow=26, signal=9
    return macd.macd(), macd.macd_signal()


# KDJ (默认 n=21, k=3, d=3)
def calc_kdj(df: pd.DataFrame, n=21, k_period=3, d_period=3):
    low_min = df['low'].rolling(window=n).min()
    high_max = df['high'].rolling(window=n).max()
    rsv = 100 * (df['close'] - low_min) / (high_max - low_min)
    k = rsv.ewm(alpha=1 / k_period).mean()
    d = k.ewm(alpha=1 / d_period).mean()
    j = 3 * k - 2 * d
    return k, d, j


# CCI (默认 window=84)
def calc_cci(df: pd.DataFrame, window=84):
    return ta.trend.cci(high=df['high'], low=df['low'], close=df['close'], window=window)


# ATR (默认 window=14)
def calc_atr(df: pd.DataFrame, window=14) -> pd.Series:
    atr = ta.volatility.AverageTrueRange(
        high=df['high'], low=df['low'], close=df['close'], window=window
    )
    return atr.average_true_range()


# MA 均线（默认 MA24、MA52）
def calc_ma(df: pd.DataFrame, periods=(24, 52)) -> pd.DataFrame:
    ma_df = pd.DataFrame(index=df.index)
    for p in periods:
        ma_df[f"MA{p}"] = df['close'].rolling(window=p).mean()
    return ma_df


# ✅ 快线 MA10（简单移动平均）
def calc_ma10(df: pd.DataFrame) -> pd.Series:
    return df['close'].rolling(window=10).mean()


# ✅ 慢线 EMA(MA10, 10)：对 MA10 进行 EMA 平滑
def calc_ema_of_ma(df: pd.DataFrame) -> pd.Series:
    ma10 = calc_ma10(df)
    return ma10.ewm(span=10).mean()


# ✅ RSI(close, 14)
def calc_rsi(df: pd.DataFrame, window=14) -> pd.Series:
    return ta.momentum.RSIIndicator(close=df['close'], window=window).rsi()

def calc_macd_hist(df: pd.DataFrame) -> pd.Series:
    macd = ta.trend.MACD(close=df['close'], window_slow=34, window_fast=13, window_sign=9)
    return macd.macd_diff()
