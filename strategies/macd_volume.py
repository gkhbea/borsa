"""
MACD ve Hacim Patlaması (Volume Breakout) Stratejisi
BIST hisselerinde kurumsal para girişini ve momentum dönüşünü tespit eder.
"""
import pandas as pd
from strategies.base import BaseStrategy
from indicators import add_macd, add_volume_features, add_moving_averages

class MACDVolumeStrategy(BaseStrategy):
    def __init__(
        self,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        vol_window: int = 20,
        vol_multiplier: float = 1.3
    ):
        super().__init__(name="MACD + Hacim Patlaması Stratejisi")
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.vol_window = vol_window
        self.vol_multiplier = vol_multiplier

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = add_macd(df, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        df = add_volume_features(df, window=self.vol_window)
        df = add_moving_averages(df, windows=(50,))

        df["Signal"] = 0
        df["Reason"] = ""

        # MACD yukarı kesişim
        macd_cross_up = (df["MACD"] > df["MACD_Signal"]) & (df["MACD"].shift(1) <= df["MACD_Signal"].shift(1))
        # Hacim teyidi
        vol_surge = df["Vol_Ratio"] >= self.vol_multiplier
        # Trend filtresi (Fiyat EMA 50'nin çok altında olmasın)
        trend_ok = df["Close"] >= df["EMA_50"] * 0.97

        buy_cond = macd_cross_up & vol_surge & trend_ok

        # MACD aşağı kesişim
        macd_cross_down = (df["MACD"] < df["MACD_Signal"]) & (df["MACD"].shift(1) >= df["MACD_Signal"].shift(1))
        sell_cond = macd_cross_down

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = "MACD Pozitif Kesişim + Güçlü Hacim Onayı"

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "MACD Negatif Kesişim (Stop/Çıkış)"

        return df
