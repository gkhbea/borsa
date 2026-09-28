"""
Çoklu İndikatör Topluluk (Ensemble) Stratejisi
Trend, Momentum, Volatilite ve Hacim göstergelerini puanlayarak yüksek güvenilirlikli sinyaller üretir.
Borsa İstanbul hisselerinde sahte kırılımları (fake-out) filtrelemek için en dengeli yaklaşımdır.
"""
import pandas as pd
from strategies.base import BaseStrategy
from indicators import add_all_indicators

class EnsembleStrategy(BaseStrategy):
    def __init__(self, buy_threshold: int = 4, sell_threshold: int = 1):
        super().__init__(name="BIST Çoklu İndikatör Topluluk Stratejisi")
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = add_all_indicators(df)

        df["Score"] = 0
        
        # 1. Trend: SuperTrend Yeşil (+1)
        st_bull = (df["SuperTrend_Direction"] == 1).astype(int)
        
        # 2. Hareketli Ortalama: EMA 21 > EMA 50 (+1)
        ema_bull = (df["EMA_21"] > df["EMA_50"]).astype(int)
        
        # 3. Momentum: MACD > Sinyal (+1)
        macd_bull = (df["MACD"] > df["MACD_Signal"]).astype(int)
        
        # 4. Göreceli Güç: RSI 48 ile 68 arasında sağlıklı yükseliş trendi (+1)
        rsi_bull = ((df["RSI"] >= 48) & (df["RSI"] <= 68)).astype(int)
        
        # 5. Hacim: Hacim ortalamanın üzerinde (+1)
        vol_bull = (df["Volume"] > df["Vol_MA"]).astype(int)

        # Toplam Puan (0 - 5)
        df["Score"] = st_bull + ema_bull + macd_bull + rsi_bull + vol_bull

        df["Signal"] = 0
        df["Reason"] = ""

        # AL Sinyali: Puan eşiği aşıldığında ve bir önceki bar eşiğin altındaysa
        buy_cond = (df["Score"] >= self.buy_threshold) & (df["Score"].shift(1) < self.buy_threshold)
        
        # SAT Sinyali: Puan 1 veya altına düştüğünde
        sell_cond = (df["Score"] <= self.sell_threshold) & (df["Score"].shift(1) > self.sell_threshold)

        df.loc[buy_cond, "Signal"] = 1
        df.loc[buy_cond, "Reason"] = df["Score"].apply(lambda s: f"Güçlü Topluluk Skoru: {s}/5 Onayı")

        df.loc[sell_cond, "Signal"] = -1
        df.loc[sell_cond, "Reason"] = "Topluluk Skoru Zayıfladı (Trend Kaybı)"

        return df
