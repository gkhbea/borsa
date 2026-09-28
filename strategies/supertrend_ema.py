"""
SuperTrend ve EMA Trend Takip Stratejisi
Borsa İstanbul'un güçlü trend yapan hisselerinde (THYAO, ASELS, TUPRS vb.) yüksek başarı oranına sahiptir.
"""
import pandas as pd
import numpy as np
from strategies.base import BaseStrategy
from indicators import add_supertrend, add_moving_averages

class SuperTrendEMAStrategy(BaseStrategy):
    def __init__(
        self,
        st_period: int = 10,
        st_multiplier: float = 3.0,
        fast_ema: int = 21,
        slow_ema: int = 50
    ):
        super().__init__(name="SuperTrend + EMA Ribbon Trend Stratejisi")
        self.st_period = st_period
        self.st_multiplier = st_multiplier
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # İndikatörleri hesapla
        df = add_supertrend(df, period=self.st_period, multiplier=self.st_multiplier)
        df = add_moving_averages(df, windows=(self.fast_ema, self.slow_ema))

        fast_col = f"EMA_{self.fast_ema}"
        slow_col = f"EMA_{self.slow_ema}"

        # Sinyal ve Gerekçe sütunları
        df["Signal"] = 0
        df["Reason"] = ""

        # Koşullar
        # AL: SuperTrend Yeşile Döndüğünde veya (SuperTrend Yeşil VE EMA 21 > EMA 50 VE Kapanış > EMA 21)
        st_bull = df["SuperTrend_Direction"] == 1
        st_bear = df["SuperTrend_Direction"] == -1
        ema_bull = df[fast_col] > df[slow_col]
        close_above_fast = df["Close"] > df[fast_col]

        # Bir önceki bar koşulları (kesişim tespiti için)
        prev_st_bear = df["SuperTrend_Direction"].shift(1) == -1
        prev_ema_bear = (df[fast_col].shift(1) <= df[slow_col].shift(1))

        # AL Sinyali:
        # 1. SuperTrend yeni yeşile döndü VE Fiyat EMA50 üzerinde
        # 2. VEYA EMA 21 yeni 50'yi yukarı kesti VE SuperTrend yeşil
        buy_cond = (
            (st_bull & prev_st_bear & (df["Close"] > df[slow_col])) |
            (st_bull & ema_bull & prev_ema_bear)
        )

        # SAT Sinyali:
        # SuperTrend Kırmızıya Döndü VEYA EMA 21, EMA 50'yi aşağı kesti
        sell_cond = (
            (st_bear & (df["SuperTrend_Direction"].shift(1) == 1)) |
            (~ema_bull & (df[fast_col].shift(1) >= df[slow_col].shift(1)))
        )

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = "SuperTrend Boğa / EMA Kesişimi"

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "SuperTrend Ayı / EMA Negatif Kesişim"

        return df
