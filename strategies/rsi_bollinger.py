"""
RSI ve Bollinger Bantları Ortalama Dönüş (Mean Reversion) Stratejisi
Yatay ve dalgalı BIST piyasalarında dipten toplama ve zirveden kâr alma üzerine odaklanır.
"""
import pandas as pd
from strategies.base import BaseStrategy
from indicators import add_rsi, add_bollinger_bands

class RSIBollingerStrategy(BaseStrategy):
    def __init__(
        self,
        rsi_window: int = 14,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 68.0,
        bb_window: int = 20,
        bb_std: float = 2.0
    ):
        super().__init__(name="RSI + Bollinger Ortalama Dönüş Stratejisi")
        self.rsi_window = rsi_window
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_window = bb_window
        self.bb_std = bb_std

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = add_rsi(df, window=self.rsi_window)
        df = add_bollinger_bands(df, window=self.bb_window, num_std=self.bb_std)

        df["Signal"] = 0
        df["Reason"] = ""

        # Koşullar
        # Dip Tespiti:
        # Fiyat Bollinger alt bandının altında veya hemen üzerinde VE RSI aşırı satım bölgesinden yukarı dönüyor
        rsi_rebound = (df["RSI"] > self.rsi_oversold) & (df["RSI"].shift(1) <= self.rsi_oversold)
        near_lower_bb = df["Low"] <= df["BB_Lower"] * 1.01

        buy_cond = rsi_rebound & near_lower_bb

        # Zirve / Kâr Alma:
        # RSI aşırı alım bölgesini gördü veya Fiyat üst banda çarptı
        rsi_top = (df["RSI"] >= self.rsi_overbought) & (df["RSI"].shift(1) < self.rsi_overbought)
        hit_upper_bb = df["High"] >= df["BB_Upper"]

        sell_cond = rsi_top | hit_upper_bb

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = "Aşırı Satım Bollinger Alt Bant Tepkisi"

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "Aşırı Alım Bollinger Üst Bant Kâr Realizasyonu"

        return df
