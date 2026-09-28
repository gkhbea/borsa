"""
BIST Temel Analiz Modülü (Fundamental Valuation & Health)
Borsa İstanbul şirketlerinin F/K, PD/DD, FD/FAVÖK, ROE, Borçluluk ve Kârlılık
oranlarını inceler, 100 üzerinden Temel Sağlık Skoru üretir.
"""
from typing import Dict, Any, Optional
import time
import os
import json
from pathlib import Path
import yfinance as yf

from config import DATA_DIR
from data_loader import normalize_ticker

def get_fundamental_cache_path(ticker: str) -> Path:
    safe = ticker.replace(".", "_")
    return DATA_DIR / f"{safe}_fundamental.json"

def fetch_fundamental_data(ticker: str, max_cache_hours: float = 12.0) -> Dict[str, Any]:
    """Hisse için bilanço ve değerleme verilerini çeker (önbellek destekli)."""
    ticker = normalize_ticker(ticker)
    cache_path = get_fundamental_cache_path(ticker)

    # Önbellek kontrolü
    if cache_path.exists():
        age = (time.time() - os.path.getmtime(cache_path)) / 3600.0
        if age < max_cache_hours:
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
    except Exception as e:
        print(f"[UYARI] {ticker} temel veri çekilemedi: {e}")
        return {}

    # Temel oranları ayıkla
    data = {
        "ticker": ticker,
        "sector": info.get("sector", "Bilinmiyor"),
        "industry": info.get("industry", "Bilinmiyor"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "forward_pe": info.get("forwardPE"),
        "trailing_pe": info.get("trailingPE"),
        "price_to_book": info.get("priceToBook"),
        "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
        "roe": info.get("returnOnEquity"),
        "profit_margin": info.get("profitMargins"),
        "gross_margin": info.get("grossMargins"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "dividend_yield": info.get("dividendYield"),
        "analyst_target_price": info.get("targetMeanPrice"),
        "updated_at": time.time()
    }

    # Önbelleğe kaydet
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return data

def evaluate_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Hissenin temel verilerini puanlar (0 - 100 puan).
    BIST dinamiklerine (yüksek enflasyon, çarpan standartları) göre kalibre edilmiştir.
    """
    raw = fetch_fundamental_data(ticker)
    if not raw or not raw.get("current_price"):
        return {
            "ticker": ticker,
            "score": 50.0,
            "verdict": "Yetersiz Temel Veri (Nötr)",
            "details": {}
        }

    score = 0.0
    max_possible = 100.0
    details = {}

    # 1. F/K Değerlemesi (Forward veya Trailing PE) - Maksimum 25 Puan
    pe = raw.get("forward_pe") or raw.get("trailing_pe")
    if pe is not None and pe > 0:
        if pe <= 6.0:
            pe_score = 25.0
            pe_desc = f"Çok Ucuz (F/K: {pe:.1f})"
        elif pe <= 10.0:
            pe_score = 20.0
            pe_desc = f"Makul / Cazip (F/K: {pe:.1f})"
        elif pe <= 15.0:
            pe_score = 12.0
            pe_desc = f"Ortalama (F/K: {pe:.1f})"
        elif pe <= 25.0:
            pe_score = 5.0
            pe_desc = f"Pahalı (F/K: {pe:.1f})"
        else:
            pe_score = 0.0
            pe_desc = f"Aşırı Primli (F/K: {pe:.1f})"
    else:
        pe_score = 10.0
        pe_desc = "F/K Hesaplanamadı / Zararda"
    score += pe_score
    details["F/K"] = {"score": pe_score, "max": 25, "desc": pe_desc, "value": pe}

    # 2. PD/DD (Fiyat / Defter Değeri) - Maksimum 20 Puan
    pb = raw.get("price_to_book")
    if pb is not None and pb > 0:
        if pb <= 1.5:
            pb_score = 20.0
            pb_desc = f"Defter Değerine Yakın (PD/DD: {pb:.2f})"
        elif pb <= 3.5:
            pb_score = 15.0
            pb_desc = f"Makul Defter Değeri (PD/DD: {pb:.2f})"
        elif pb <= 7.0:
            pb_score = 8.0
            pb_desc = f"Sektörel Primli (PD/DD: {pb:.2f})"
        else:
            pb_score = 2.0
            pb_desc = f"Yüksek Defter Değeri Primi (PD/DD: {pb:.2f})"
    else:
        pb_score = 10.0
        pb_desc = "PD/DD Verisi Yok"
    score += pb_score
    details["PD/DD"] = {"score": pb_score, "max": 20, "desc": pb_desc, "value": pb}

    # 3. Kârlılık ve Özsermaye Kârlılığı (ROE) - Maksimum 25 Puan
    roe = raw.get("roe")
    if roe is not None:
        roe_pct = roe * 100.0 if roe < 5 else roe
        if roe_pct >= 40.0:
            roe_score = 25.0
            roe_desc = f"Çok Yüksek Kârlılık (%{roe_pct:.1f})"
        elif roe_pct >= 25.0:
            roe_score = 20.0
            roe_desc = f"Güçlü Kârlılık (%{roe_pct:.1f})"
        elif roe_pct >= 15.0:
            roe_score = 12.0
            roe_desc = f"Orta Kârlılık (%{roe_pct:.1f})"
        elif roe_pct > 0:
            roe_score = 5.0
            roe_desc = f"Düşük Kârlılık (%{roe_pct:.1f})"
        else:
            roe_score = 0.0
            roe_desc = f"Negatif Özsermaye Kârlılığı (%{roe_pct:.1f})"
    else:
        roe_score = 12.0
        roe_desc = "ROE Verisi Yok"
    score += roe_score
    details["ROE"] = {"score": roe_score, "max": 25, "desc": roe_desc, "value": roe}

    # 4. Borçluluk ve Likidite (Debt/Equity & Cari Oran) - Maksimum 15 Puan
    de = raw.get("debt_to_equity")
    cr = raw.get("current_ratio")
    debt_score = 0.0
    if de is not None:
        if de <= 60.0:
            debt_score += 10.0
        elif de <= 150.0:
            debt_score += 6.0
        else:
            debt_score += 2.0
    else:
        debt_score += 5.0

    if cr is not None and cr >= 1.2:
        debt_score += 5.0
    elif cr is not None and cr >= 0.9:
        debt_score += 3.0
    else:
        debt_score += 1.0

    score += debt_score
    details["Borçluluk"] = {
        "score": debt_score,
        "max": 15,
        "desc": f"Borç/Özkaynak: {de if de else '-'}, Cari Oran: {cr if cr else '-'}"
    }

    # 5. Temettü Verimi & Analist Hedefi - Maksimum 15 Puan
    extra_score = 0.0
    div = raw.get("dividend_yield")
    if div is not None and div > 0:
        div_pct = div if div > 1 else div * 100.0
        if div_pct >= 4.0:
            extra_score += 8.0
        else:
            extra_score += 4.0
    
    target_price = raw.get("analyst_target_price")
    curr_price = raw.get("current_price")
    if target_price and curr_price and target_price > curr_price:
        upside = ((target_price - curr_price) / curr_price) * 100.0
        if upside >= 25.0:
            extra_score += 7.0
        elif upside >= 10.0:
            extra_score += 4.0
    
    score += extra_score
    details["Temettü & Hedef Potansiyel"] = {
        "score": extra_score,
        "max": 15,
        "desc": f"Temettü: %{div if div else 0:.1f}"
    }

    final_score = round(min(score, max_possible), 1)

    # Değerlendirme Yorumu
    if final_score >= 80.0:
        verdict = "Mükemmel Temel Değer & Kârlılık (Ucuz & Güçlü)"
    elif final_score >= 65.0:
        verdict = "Sağlıklı Finansal Yapı (Cazip)"
    elif final_score >= 45.0:
        verdict = "Dengeli / Sektör Ortalamasında"
    elif final_score >= 30.0:
        verdict = "Zayıf Kârlılık / Primli Çarpanlar"
    else:
        verdict = "Yüksek Risk / Aşırı Pahalı veya Borçlu"

    return {
        "ticker": ticker,
        "score": final_score,
        "verdict": verdict,
        "details": details,
        "raw": raw
    }
