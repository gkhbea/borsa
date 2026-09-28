"""
BIST Veri Yükleyici ve Önbellek Yönetimi
Yahoo Finance API üzerinden Borsa İstanbul verilerini çeker ve önbelleğe alır.
"""
import os
import time
from pathlib import Path
from typing import Optional, List
import pandas as pd
import yfinance as yf

from config import DATA_DIR, BIST_30_TICKERS, DEFAULT_INTERVAL, DEFAULT_PERIOD

def normalize_ticker(symbol: str) -> str:
    """
    Hisse sembolünü BIST formatına (SEMBOL.IS) dönüştürür.
    Örn: 'THYAO' -> 'THYAO.IS', 'GARAN.IS' -> 'GARAN.IS'
    """
    clean_sym = symbol.strip().upper()
    if not clean_sym.endswith(".IS"):
        return f"{clean_sym}.IS"
    return clean_sym

def get_cache_path(ticker: str, period: str, interval: str) -> Path:
    """Önbellek dosya yolunu döner (CSV formatında)."""
    safe_name = ticker.replace(".", "_")
    return DATA_DIR / f"{safe_name}_{period}_{interval}.csv"

def fetch_data(
    ticker: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
    use_cache: bool = True,
    max_cache_age_hours: float = 4.0
) -> pd.DataFrame:
    """
    Belirtilen BIST hissesi için OHLCV verilerini indirir veya önbellekten okur.
    
    Dönen Sütunlar: Open, High, Low, Close, Volume
    """
    ticker = normalize_ticker(ticker)
    cache_file = get_cache_path(ticker, period, interval)

    # Önbellek kontrolü
    if use_cache and cache_file.exists():
        file_age_hours = (time.time() - os.path.getmtime(cache_file)) / 3600.0
        if file_age_hours < max_cache_age_hours:
            try:
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                if not df.empty:
                    return df
            except Exception:
                pass  # Bozuk dosya varsa yeniden indir

    # Yahoo Finance üzerinden veri çek
    try:
        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(period=period, interval=interval, auto_adjust=True)
    except Exception as e:
        print(f"[HATA] {ticker} verisi çekilirken sorun oluştu: {e}")
        return pd.DataFrame()

    if df.empty:
        print(f"[UYARI] {ticker} için veri bulunamadı.")
        return pd.DataFrame()

    # İndeks ve sütun temizliği
    # Çoklu indeks varsa düzelt
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Gerekli sütunları standartlaştır
    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    available_cols = [c for c in required_cols if c in df.columns]
    df = df[available_cols].copy()

    # Eksik değerleri temizle
    df.dropna(inplace=True)

    # Tarih saat bölgesini temizle (UTC timezone kaldır)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # Önbelleğe kaydet (CSV)
    if use_cache and not df.empty:
        try:
            df.to_csv(cache_file)
        except Exception:
            pass

    return df

def fetch_batch_data(
    tickers: Optional[List[str]] = None,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL
) -> dict[str, pd.DataFrame]:
    """Birden fazla hisse senedinin verilerini toplu olarak çeker."""
    if tickers is None:
        tickers = BIST_30_TICKERS

    data_map = {}
    total = len(tickers)
    for i, t in enumerate(tickers, 1):
        print(f"[{i}/{total}] {t} verisi alınıyor...", end="\r")
        df = fetch_data(t, period=period, interval=interval)
        if not df.empty:
            data_map[t] = df
    print(f"\nToplam {len(data_map)} hisse verisi hazırlandı.")
    return data_map
