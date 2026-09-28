"""
BIST Sniper Stratejisi (Kurumsal Düzeltme & Trend Sürüş Motoru)
Broker Hatalarından Çıkarılan Derslerle Sıfırdan İnşa Edildi:
1. Zirveden sahte kırılıma (Fakeout) girmeyi YASAKLAR.
2. Yükseliş trendindeki hissenin EMA 21 / SuperTrend desteğine yaptığı 'Hacimsiz Düzeltmeyi' (Pullback) yakalar.
3. Stop seviyesini sabit yüzde yerine ATR volatilitesine göre dinamik ayarlar (Gürültüde patlamaz).
4. Kâr tavanı koymaz; Chandelier Trailing Stop ile büyük dalgayı sonuna kadar sürer.
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy
from indicators import add_moving_averages, add_atr, add_supertrend, add_rsi, add_volume_features
from strategies.bist_alpha_master import add_adx

class BISTSniperStrategy(BaseStrategy):
    def __init__(
        self,
        atr_stop_mult: float = 2.0,
        atr_trail_mult: float = 3.0,
        min_adx: float = 16.0
    ):
        super().__init__(name="BIST Sniper (Pullback & Trend Sürüş)")
        self.atr_stop_mult = atr_stop_mult
        self.atr_trail_mult = atr_trail_mult
        self.min_adx = min_adx

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = add_moving_averages(df, windows=(21, 50, 200))
        df = add_atr(df, window=14)
        df = add_adx(df, period=14)
        df = add_rsi(df, window=14)
        df = add_supertrend(df, period=10, multiplier=2.5)
        df = add_volume_features(df, window=20)

        df["Signal"] = 0
        df["Reason"] = ""

        # ==========================================
        # 1. MAKRO TREND & SAĞLIK FİLTRESİ
        # ==========================================
        trend_bull = (df["Close"] > df["EMA_50"]) & (df["EMA_21"] > df["EMA_50"])
        is_trending = df["ADX"] >= self.min_adx

        # ==========================================
        # 2. İKİLİ TETİKLEYİCİ (DUAL ENGINE)
        # ==========================================
        # Tetikleyici A: Desteğe Pullback (Düzeltme) Dönüşü
        pullback = (
            (df["Low"] <= df["EMA_21"] * 1.02) &
            (df["Close"] > df["Open"]) &
            (df["Close"] > df["EMA_21"]) &
            (df["RSI"] <= 68.0)
        )
        
        # Tetikleyici B: Hacimli Zirve Kırılımı (Breakout)
        from indicators import add_donchian_breakout
        df = add_donchian_breakout(df, window=20)
        breakout = (df["Breakout_20d"]) & (df["Vol_Ratio"] >= 1.3) & (df["RSI"] <= 72.0)

        # SuperTrend Boğa Modunda Olmalı
        st_bull = df["SuperTrend_Direction"] == 1

        buy_cond = trend_bull & is_trending & (pullback | breakout) & st_bull

        # ==========================================
        # 3. ÇIKIŞ / TREND SONU ŞARTI
        # ==========================================
        st_bear = df["SuperTrend_Direction"] == -1
        close_below_ema50 = df["Close"] < df["EMA_50"]

        sell_cond = st_bear | close_below_ema50

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = "Sniper Dual Giriş (Pullback/Kırılım)"

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "Trend Çıkışı (EMA 50 / SuperTrend)"

        return df
