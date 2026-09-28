"""
BIST Alpha Master Stratejisi (Kurumsal Broker Rejim & Trend Motoru)
Testere piyasasında parayı koruyan (ADX & EMA 200 Filtresi),
Trend yakalandığında ise kârı erken kesmeyip (ATR Chandelier Trailing Stop)
büyük dalgaları sonuna kadar süren kurumsal algoritma.
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy
from indicators import add_moving_averages, add_atr, add_supertrend, add_volume_features
from takas_analyzer import calculate_chaikin_money_flow

def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """ADX (Ortalama Yönsel Endeks) - Testere / Trend Ayrım Filtresi."""
    df = df.copy()
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    df_atr = add_atr(df, window=period)
    atr = df_atr["ATR"]

    plus_di = 100.0 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100.0 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1.0/period, adjust=False).mean() / atr.replace(0, np.nan))

    dx = 100.0 * (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan))
    df["ADX"] = dx.ewm(alpha=1.0/period, adjust=False).mean().fillna(15.0)
    df["Plus_DI"] = plus_di.fillna(20.0)
    df["Minus_DI"] = minus_di.fillna(20.0)
    return df

class BISTAlphaMasterStrategy(BaseStrategy):
    def __init__(
        self,
        min_adx: float = 20.0,
        use_ema200_filter: bool = True
    ):
        super().__init__(name="BIST Alpha Master (Rejim + Trend Takip)")
        self.min_adx = min_adx
        self.use_ema200_filter = use_ema200_filter

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = add_moving_averages(df, windows=(21, 50, 200))
        df = add_adx(df, period=14)
        df = add_atr(df, window=14)
        df = add_supertrend(df, period=10, multiplier=2.5)
        df = add_volume_features(df, window=20)
        df["CMF"] = calculate_chaikin_money_flow(df, period=20)

        df["Signal"] = 0
        df["Reason"] = ""

        # FILTRE 1: Rejim Kontrolü (Testere Piyasasında ALIM YASAK)
        # ADX > 20 ise piyasa trenddedir, testerede değil.
        is_trending = df["ADX"] >= self.min_adx

        # FILTRE 2: Ana Trend Filtresi (Fiyat EMA 200 üzerinde ve EMA 21 > EMA 50)
        if self.use_ema200_filter and "EMA_200" in df.columns:
            macro_bull = (df["Close"] > df["EMA_200"]) & (df["EMA_21"] > df["EMA_50"])
        else:
            macro_bull = df["EMA_21"] > df["EMA_50"]

        # FILTRE 3: Para Akışı (CMF >= -0.02, kurumsal kaçış olmamalı)
        money_ok = df["CMF"] >= -0.02

        # TETIKLEYICI (TRIGGER): SuperTrend yeni yeşile döndü VEYA Fiyat EMA 21 üzerine attı
        st_bull = df["SuperTrend_Direction"] == 1
        st_fresh_bull = st_bull & (df["SuperTrend_Direction"].shift(1) == -1)
        ema_cross_up = (df["Close"] > df["EMA_21"]) & (df["Close"].shift(1) <= df["EMA_21"].shift(1))

        # AL Sinyali
        buy_cond = is_trending & macro_bull & money_ok & (st_fresh_bull | (st_bull & ema_cross_up))

        # SAT Sinyali (Trend Bittiğinde / Yapı Bozulduğunda)
        # 1. SuperTrend kırmızıya döndü
        # 2. VEYA Fiyat EMA 50 altına sarktı
        st_bear = df["SuperTrend_Direction"] == -1
        st_fresh_bear = st_bear & (df["SuperTrend_Direction"].shift(1) == 1)
        close_below_ema50 = (df["Close"] < df["EMA_50"]) & (df["Close"].shift(1) >= df["EMA_50"].shift(1))

        sell_cond = st_fresh_bear | close_below_ema50

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = "Alpha Rejim Onayı + SuperTrend Boğa"

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "Trend Sonu / EMA 50 & SuperTrend Kırılımı"

        return df
