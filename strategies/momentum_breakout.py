"""
Momentum ve Zirve Kırılım Stratejisi (High-Velocity Breakout Strategy)
Mark Minervini ve Stan Weinstein prensipleriyle BIST hisselerinde en hızlı yükselen,
hacim destekli zirve kırılımlarını yakalar.
"""
import pandas as pd
from strategies.base import BaseStrategy
from indicators import (
    add_moving_averages,
    add_momentum_indicators,
    add_donchian_breakout,
    add_volume_features,
    add_rsi
)

class MomentumBreakoutStrategy(BaseStrategy):
    def __init__(
        self,
        breakout_window: int = 20,
        min_roc_10: float = 2.5,
        min_vol_ratio: float = 1.3
    ):
        super().__init__(name="BIST Momentum & Zirve Kırılım Stratejisi")
        self.breakout_window = breakout_window
        self.min_roc_10 = min_roc_10
        self.min_vol_ratio = min_vol_ratio

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df = add_moving_averages(df, windows=(21, 50))
        df = add_momentum_indicators(df, roc_windows=(10, 21))
        df = add_donchian_breakout(df, window=self.breakout_window)
        df = add_volume_features(df, window=20)
        df = add_rsi(df, window=14)

        df["Signal"] = 0
        df["Reason"] = ""

        # Koşullar
        # 1. Zirve Kırılımı (Bugünkü kapanış son 20 günün zirvesini kırdı ve dün kırmamıştı)
        fresh_breakout = df["Breakout_20d"] & (~df["Breakout_20d"].shift(1).fillna(False).astype(bool))

        # 2. Güçlü İvme (10 günlük getiri hızı > eşik değer)
        strong_momentum = df["ROC_10"] >= self.min_roc_10

        # 3. Hacim Onayı (20 günlük hacim ortalamasının üzerinde)
        volume_surge = df["Vol_Ratio"] >= self.min_vol_ratio

        # 4. Trend Uyumu (Fiyat > EMA 21 > EMA 50)
        trend_aligned = (df["Close"] > df["EMA_21"]) & (df["EMA_21"] > df["EMA_50"])

        # 5. Aşırı Alım Filtresi (RSI 75 üzerinde olmasın, taze kırılım olsun)
        healthy_rsi = df["RSI"] <= 75.0

        # AL Sinyali
        buy_cond = fresh_breakout & strong_momentum & volume_surge & trend_aligned & healthy_rsi

        # SAT / Çıkış Sinyali
        # Kapanış EMA 21'in altına sarkarsa veya RSI 82 üstünde tepe yapıp dönerse
        trend_broken = (df["Close"] < df["EMA_21"]) & (df["Close"].shift(1) >= df["EMA_21"].shift(1))
        rsi_exhaustion = (df["RSI"] < 75.0) & (df["RSI"].shift(1) >= 80.0)

        sell_cond = trend_broken | rsi_exhaustion

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = "20G Zirve Kırılımı + Hacimli Momentum İvmesi"

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "Momentum Kaybı / EMA 21 Desteği Kırıldı"

        return df
