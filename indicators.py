"""
Teknik Analiz İndikatörleri Modülü
Harici karmaşık C kütüphanelerine bağımlı olmadan saf Pandas/NumPy ile optimize edilmiş formüller.
TradingView ile %100 uyumlu standart hesaplamalar.
"""
import numpy as np
import pandas as pd

def add_moving_averages(df: pd.DataFrame, windows=(9, 21, 50, 200)) -> pd.DataFrame:
    """Üssel (EMA) ve Basit (SMA) Hareketli Ortalamaları ekler."""
    df = df.copy()
    for w in windows:
        df[f"EMA_{w}"] = df["Close"].ewm(span=w, adjust=False).mean()
        df[f"SMA_{w}"] = df["Close"].rolling(window=w).mean()
    return df

def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Wilder's RSI (Göreceli Güç Endeksi) hesaplar.
    Aşırı Alım: >= 70, Aşırı Satım: <= 30
    """
    df = df.copy()
    delta = df["Close"].diff()
    
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's Exponential Smoothing (TradingView standardı)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100.0 - (100.0 / (1.0 + rs))
    df["RSI"] = df["RSI"].fillna(50.0)
    return df

def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> pd.DataFrame:
    """
    MACD (Moving Average Convergence Divergence) hesaplar.
    MACD = EMA(12) - EMA(26)
    Signal = EMA(MACD, 9)
    Hist = MACD - Signal
    """
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()

    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df

def add_bollinger_bands(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2.0
) -> pd.DataFrame:
    """
    Bollinger Bantları hesaplar.
    Orta Bant = SMA(20)
    Üst/Alt Bant = Orta +/- (2 * Standart Sapma)
    """
    df = df.copy()
    mid = df["Close"].rolling(window=window).mean()
    std = df["Close"].rolling(window=window).std()

    df["BB_Middle"] = mid
    df["BB_Upper"] = mid + (num_std * std)
    df["BB_Lower"] = mid - (num_std * std)
    # Band genişliği ve %B göstergesi
    bandwidth = (df["BB_Upper"] - df["BB_Lower"]) / mid.replace(0, np.nan)
    df["BB_Bandwidth"] = bandwidth
    df["BB_Pct"] = (df["Close"] - df["BB_Lower"]) / (df["BB_Upper"] - df["BB_Lower"]).replace(0, np.nan)
    return df

def add_atr(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    ATR (Ortalama Gerçek Aralık - Volatilite İndikatörü).
    Stop-loss belirleme ve SuperTrend için temel teşkil eder.
    """
    df = df.copy()
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["TR"] = tr
    # Wilder's Smoothing
    df["ATR"] = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    return df

def add_supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0
) -> pd.DataFrame:
    """
    SuperTrend İndikatörü (Borsa İstanbul'da trend takibinde en yaygın ve başarılı araç).
    Direction: 1 (Yükseliş / Yeşil), -1 (Düşüş / Kırmızı)
    """
    df = add_atr(df, window=period)
    df = df.copy()

    hl2 = (df["High"] + df["Low"]) / 2.0
    basic_upper = hl2 + (multiplier * df["ATR"])
    basic_lower = hl2 - (multiplier * df["ATR"])

    final_upper = np.zeros(len(df))
    final_lower = np.zeros(len(df))
    supertrend = np.zeros(len(df))
    direction = np.ones(len(df))  # 1: Long, -1: Short

    close = df["Close"].values
    basic_upper_vals = basic_upper.values
    basic_lower_vals = basic_lower.values

    for i in range(1, len(df)):
        # Üst bant hesaplama
        if basic_upper_vals[i] < final_upper[i - 1] or close[i - 1] > final_upper[i - 1]:
            final_upper[i] = basic_upper_vals[i]
        else:
            final_upper[i] = final_upper[i - 1]

        # Alt bant hesaplama
        if basic_lower_vals[i] > final_lower[i - 1] or close[i - 1] < final_lower[i - 1]:
            final_lower[i] = basic_lower_vals[i]
        else:
            final_lower[i] = final_lower[i - 1]

        # Trend Yönü belirleme
        prev_dir = direction[i - 1]
        if prev_dir == 1:
            if close[i] < final_lower[i]:
                direction[i] = -1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lower[i]
        else:
            if close[i] > final_upper[i]:
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]

    df["SuperTrend"] = supertrend
    df["SuperTrend_Direction"] = direction
    return df

def add_volume_features(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Hacim ortalaması ve Hacim Patlaması (Volume Surge) tespiti."""
    df = df.copy()
    df["Vol_MA"] = df["Volume"].rolling(window=window).mean()
    df["Vol_Ratio"] = df["Volume"] / df["Vol_MA"].replace(0, np.nan)
    # Hacim 20 günlük ortalamanın %50 üzerindeyse hacim patlaması sayılır
    df["Vol_Surge"] = df["Vol_Ratio"] >= 1.5
    return df

def add_momentum_indicators(df: pd.DataFrame, roc_windows=(10, 21)) -> pd.DataFrame:
    """
    Momentum ve Fiyat Değişim Hızı (ROC - Rate of Change) hesaplar.
    Hisse ivmesini ve fırlama potansiyelini ölçer.
    """
    df = df.copy()
    for w in roc_windows:
        # Yüzdesel getiri hızı
        df[f"ROC_{w}"] = df["Close"].pct_change(periods=w) * 100.0
    
    # Fiyat ivmesi (10 günlük mutlak momentum)
    df["MOM_10"] = df["Close"] - df["Close"].shift(10)
    return df

def add_donchian_breakout(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Donchian Kanalı ve Zirve Kırılımı (Mark Minervini / Stan Weinstein Momentum Stili).
    Fiyat son N günün zirvesini kırdığında güçlü momentum başlangıcı sayılır.
    """
    df = df.copy()
    df[f"High_{window}d"] = df["High"].shift(1).rolling(window=window).max()
    df[f"Low_{window}d"] = df["Low"].shift(1).rolling(window=window).min()
    
    # 20 günlük zirve kırılımı
    df["Breakout_20d"] = df["Close"] > df[f"High_{window}d"]
    # 52 haftalık (252 işlem günü) zirveye yakınlık oranı
    high_52w = df["High"].rolling(window=min(252, len(df))).max()
    df["Dist_To_52w_High_Pct"] = ((high_52w - df["Close"]) / high_52w) * 100.0
    df["Is_52w_High"] = df["Dist_To_52w_High_Pct"] <= 2.0  # Zirvenin %2 içinde
    return df

def add_bollinger_squeeze(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bollinger Sıkışması (Volatilite Daralması & Patlama Öncesi).
    Bantlar son 60 günün en dar halindeyse (squeeze) patlama yakındır.
    """
    df = add_bollinger_bands(df, window=20, num_std=2.0)
    df = df.copy()
    min_bandwidth_60 = df["BB_Bandwidth"].rolling(window=min(60, len(df))).min()
    df["BB_Squeeze"] = df["BB_Bandwidth"] <= (min_bandwidth_60 * 1.15)
    return df

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tüm teknik ve momentum indikatörlerini tek seferde DataFrame'e ekler."""
    df = add_moving_averages(df, windows=(9, 21, 50, 200))
    df = add_rsi(df, window=14)
    df = add_macd(df, fast=12, slow=26, signal=9)
    df = add_bollinger_bands(df, window=20, num_std=2.0)
    df = add_supertrend(df, period=10, multiplier=3.0)
    df = add_volume_features(df, window=20)
    df = add_momentum_indicators(df, roc_windows=(10, 21))
    df = add_donchian_breakout(df, window=20)
    df = add_bollinger_squeeze(df)
    return df
