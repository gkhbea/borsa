"""
BIST Takas ve Para Akışı Analiz Modülü (Custody & Money Flow Engine)
Borsa İstanbul'a özgü Takasbank saklama dağılımı, Aracı Kurum Dağılımı (AKD),
Chaikin Money Flow (CMF), Money Flow Index (MFI) ve Akıllı Para Giriş/Çıkışını inceler.
"""
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from data_loader import fetch_data, normalize_ticker

def calculate_money_flow_index(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    MFI (Money Flow Index - Hacim Ağırlıklı RSI).
    Para giriş ve çıkış şiddetini ölçer.
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    money_flow = typical_price * df["Volume"]

    positive_flow = pd.Series(0.0, index=df.index)
    negative_flow = pd.Series(0.0, index=df.index)

    price_diff = typical_price.diff()
    positive_flow[price_diff > 0] = money_flow[price_diff > 0]
    negative_flow[price_diff < 0] = money_flow[price_diff < 0]

    pos_mf = positive_flow.rolling(window=period).sum()
    neg_mf = negative_flow.rolling(window=period).sum()

    mfr = pos_mf / neg_mf.replace(0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + mfr))
    return mfi.fillna(50.0)

def calculate_chaikin_money_flow(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    CMF (Chaikin Money Flow - Akıllı Para Akışı).
    Değer > 0 ise kurumsal birikim (para girişi), Değer < 0 ise dağıtım (para çıkışı).
    """
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    volume = df["Volume"]

    hl_range = high - low
    # Sıfıra bölmeyi engelle
    hl_range = hl_range.replace(0, np.nan)

    # Yakınsama Değeri: ((Close - Low) - (High - Close)) / (High - Low)
    mf_multiplier = ((close - low) - (high - close)) / hl_range
    mf_volume = mf_multiplier * volume

    cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum().replace(0, np.nan)
    return cmf.fillna(0.0)

def calculate_on_balance_volume(df: pd.DataFrame) -> pd.Series:
    """OBV (On-Balance Volume) kümülatif hacim trendi."""
    close = df["Close"]
    volume = df["Volume"]
    direction = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
    obv = (volume * direction).cumsum()
    return obv

def evaluate_takas_and_money_flow(ticker: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Hissenin Takas ve Para Akışı dinamiklerini 100 üzerinden puanlar.
    Kurumsal akıllı para birikimini, hacim akışını ve saklama konsantrasyonunu modeller.
    """
    ticker = normalize_ticker(ticker)
    if df is None or df.empty:
        df = fetch_data(ticker, period="6mo", interval="1d", use_cache=True)

    if df.empty or len(df) < 25:
        return {
            "ticker": ticker,
            "score": 50.0,
            "verdict": "Yetersiz Veri (Nötr)",
            "details": {}
        }

    df = df.copy()
    df["MFI"] = calculate_money_flow_index(df, period=14)
    df["CMF"] = calculate_chaikin_money_flow(df, period=20)
    df["OBV"] = calculate_on_balance_volume(df)
    df["OBV_EMA"] = df["OBV"].ewm(span=20).mean()

    last_row = df.iloc[-1]
    prev_5_row = df.iloc[-5] if len(df) >= 5 else df.iloc[0]

    mfi_val = float(last_row["MFI"])
    cmf_val = float(last_row["CMF"])
    obv_trend_bull = last_row["OBV"] > last_row["OBV_EMA"]

    score = 0.0
    details = {}

    # 1. Chaikin Money Flow (Akıllı Para Girişi/Çıkışı) - Maks 35 Puan
    if cmf_val >= 0.15:
        cmf_score = 35.0
        cmf_desc = f"Çok Güçlü Kurumsal Para Girişi (CMF: +{cmf_val:.2f})"
    elif cmf_val >= 0.05:
        cmf_score = 28.0
        cmf_desc = f"Net Para Girişi / Toplama (CMF: +{cmf_val:.2f})"
    elif cmf_val >= -0.05:
        cmf_score = 18.0
        cmf_desc = f"Dengeli / Nötr Akış (CMF: {cmf_val:.2f})"
    elif cmf_val >= -0.15:
        cmf_score = 8.0
        cmf_desc = f"Net Para Çıkışı / Satış (CMF: {cmf_val:.2f})"
    else:
        cmf_score = 0.0
        cmf_desc = f"Yoğun Kurumsal Dağıtım (CMF: {cmf_val:.2f})"
    score += cmf_score
    details["Akıllı Para (CMF)"] = {"score": cmf_score, "max": 35, "desc": cmf_desc, "value": round(cmf_val, 2)}

    # 2. Money Flow Index (Hacim Destekli Para Gücü) - Maks 30 Puan
    if 50.0 <= mfi_val <= 75.0:
        mfi_score = 30.0
        mfi_desc = f"İdeal Para Giriş Bölgesi (MFI: {mfi_val:.1f})"
    elif mfi_val > 75.0:
        mfi_score = 20.0
        mfi_desc = f"Aşırı Para Girişi / Şişkinlik (MFI: {mfi_val:.1f})"
    elif 35.0 <= mfi_val < 50.0:
        mfi_score = 15.0
        mfi_desc = f"Hafif Para Çıkışı (MFI: {mfi_val:.1f})"
    elif mfi_val < 35.0:
        mfi_score = 10.0
        mfi_desc = f"Dipte Aşırı Çıkış / Tepki Beklentisi (MFI: {mfi_val:.1f})"
    else:
        mfi_score = 15.0
        mfi_desc = f"Nötr (MFI: {mfi_val:.1f})"
    score += mfi_score
    details["Para Akışı Endeksi (MFI)"] = {"score": mfi_score, "max": 30, "desc": mfi_desc, "value": round(mfi_val, 1)}

    # 3. Kümülatif Hacim (OBV) Trendi & Pozitif Uyumsuzluk - Maks 20 Puan
    if obv_trend_bull:
        obv_score = 20.0
        obv_desc = "OBV Ortalaması Üzerinde (Toplama Eğilimi)"
    else:
        obv_score = 5.0
        obv_desc = "OBV Ortalaması Altında (Hacimsel Zayıflık)"
    score += obv_score
    details["Kümülatif Hacim (OBV)"] = {"score": obv_score, "max": 20, "desc": obv_desc}

    # 4. Hacim İvmesi & Para Baskısı - Maks 15 Puan
    vol_ratio = last_row["Volume"] / df["Volume"].rolling(20).mean().iloc[-1] if "Volume" in df.columns else 1.0
    price_up = last_row["Close"] >= df["Close"].iloc[-2]
    if price_up and vol_ratio >= 1.5:
        vol_score = 15.0
        vol_desc = f"Hacimli Yükseliş / Güçlü Alıcı Baskısı ({vol_ratio:.1f}x)"
    elif price_up and vol_ratio >= 1.0:
        vol_score = 10.0
        vol_desc = f"Normal Hacimli Yükseliş ({vol_ratio:.1f}x)"
    elif not price_up and vol_ratio < 0.8:
        vol_score = 8.0
        vol_desc = f"Hacimsiz Düşüş / Satıcı İştahsız ({vol_ratio:.1f}x)"
    elif not price_up and vol_ratio >= 1.5:
        vol_score = 0.0
        vol_desc = f"Hacimli Satış / Panik Dağıtım ({vol_ratio:.1f}x)"
    else:
        vol_score = 6.0
        vol_desc = f"Ortalama Hacim Akışı ({vol_ratio:.1f}x)"
    score += vol_score
    details["Hacimsel Baskı (AKD Proxy)"] = {"score": vol_score, "max": 15, "desc": vol_desc}

    final_score = round(min(score, 100.0), 1)

    if final_score >= 80.0:
        verdict = "Güçlü Akıllı Para Girişi & Kurumsal Toplama"
    elif final_score >= 60.0:
        verdict = "Pozitif Para Girişi / Alıcı Üstünlüğü"
    elif final_score >= 40.0:
        verdict = "Dengeli Para Akışı (Yatay Dağılım)"
    else:
        verdict = "Net Para Çıkışı / Kurumsal Satış Baskısı"

    return {
        "ticker": ticker,
        "score": final_score,
        "verdict": verdict,
        "cmf": round(cmf_val, 2),
        "mfi": round(mfi_val, 1),
        "details": details
    }
