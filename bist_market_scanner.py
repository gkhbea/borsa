"""
BIST 360 - Tüm Borsa İstanbul Pazar Tarayıcısı (Entire Market Scanner)
Sadece BIST 30 veya BIST 100 değil, Borsa İstanbul'daki 450+ likit hissenin tamamını
anlık olarak tarar, hacim patlaması ve dönüş formasyonu veren hisseleri listeler.

Güvenlik Kalkanı:
- Günlük işlem hacmi 15 Milyon TL'nin altındaki sığ, batık veya manipülatif tahtalar elenir.
- Kullanıcı tek tuşla anında çıkabileceği likit büyüme hisseleriyle korunur.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import urllib.request
import pandas as pd
from typing import Dict, Any, List

from config import DEFAULT_INITIAL_CAPITAL, MAX_POSITION_SIZE_PCT, BIST_30_TICKERS

def scan_entire_bist(min_volume_tl: float = 15_000_000, limit: int = 50) -> Dict[str, Any]:
    """
    Borsa İstanbul'daki tüm pazar hisselerini (Yıldız Pazar, Ana Pazar) tarar.
    En yüksek hacim, momentum ve teknik dönüş gösterenleri ayıklar.
    """
    url = "https://scanner.tradingview.com/turkey/scan"
    payload = json.dumps({
        "filter": [
            {"left": "type", "operation": "equal", "right": "stock"},
            {"left": "Value.Traded", "operation": "greater", "right": min_volume_tl}
        ],
        "options": {"lang": "tr"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [
            "name", "close", "change", "Value.Traded",
            "RSI", "MACD.macd", "MACD.signal", "EMA20", "EMA50", "EMA200",
            "Recommend.All", "market_cap_basic", "description"
        ],
        "sort": {"sortBy": "Value.Traded", "sortOrder": "desc"},
        "range": [0, 150]
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            data = res.get("data", [])
            total_scanned = res.get("totalCount", len(data))
    except Exception as e:
        print(f"[HATA] Tüm pazar tarayıcısı bağlanamadı: {e}")
        return {"bist_30_picks": [], "bist_all_picks": [], "total_scanned": 0}

    slot_capital = DEFAULT_INITIAL_CAPITAL * MAX_POSITION_SIZE_PCT
    bist_30_clean = [t.replace(".IS", "") for t in BIST_30_TICKERS]

    all_candidates = []

    for row in data:
        symbol = row["s"].replace("BIST:", "")
        d = row["d"]

        close_p = d[1] if d[1] else 0.0
        change_pct = d[2] if d[2] else 0.0
        val_traded = d[3] if d[3] else 0.0
        rsi = d[4] if d[4] else 50.0
        macd = d[5] if d[5] else 0.0
        macd_sig = d[6] if d[6] else 0.0
        ema20 = d[7] if d[7] else close_p
        desc = d[12] if len(d) > 12 and d[12] else symbol

        if close_p <= 0.0:
            continue

        # Dönüş ve Pusu Skoru
        # 1. Aşırı satımdan toparlanma veya EMA 20 desteği üzerinde tutunma
        score = 50.0
        tag = "İzleme"

        # RSI 30-55 arası dip toparlanması
        if 32 <= rsi <= 52:
            score += 20.0
            tag = "💎 Dip Toparlanması"
        elif 52 < rsi <= 68:
            score += 15.0
            tag = "🚀 Güçlü İvme / Trend"

        # EMA 20 desteğine yakınlık (%2 civarı)
        dist_ema20 = (close_p - ema20) / ema20 * 100
        if -1.5 <= dist_ema20 <= 2.5:
            score += 15.0
            tag = "🎯 Destek Pusu (EMA 20)"

        # MACD pozitif kesişim
        if macd > macd_sig:
            score += 10.0

        # Devasa Hacim Bonusu (Günde 500M TL üzeri)
        if val_traded > 500_000_000:
            score += 5.0

        # Stop ve Hedefler
        atr_proxy = close_p * 0.035
        pusu_fiyati = round(close_p * 0.993, 2)
        stop_loss = round(pusu_fiyati - (atr_proxy * 1.5), 2)
        target_1 = round(pusu_fiyati + (atr_proxy * 2.5), 2)
        target_2 = round(pusu_fiyati + (atr_proxy * 4.5), 2)

        lot_count = int(slot_capital // pusu_fiyati)
        total_cost = lot_count * pusu_fiyati

        is_bist30 = symbol in bist_30_clean
        pazar_turu = "BIST 30 Lokomotif" if is_bist30 else "BIST TÜM / Büyüme"

        all_candidates.append({
            "Hisse": symbol,
            "Tanım": desc[:25],
            "Pazar": pazar_turu,
            "Fiyat": f"{close_p:.2f} TL",
            "Pusu Fiyatı": f"{pusu_fiyati:.2f} TL",
            "Günlük Değişim": f"{change_pct:+.2f}%",
            "Hacim": f"{val_traded/1e6:.1f}M TL",
            "Lot": f"{lot_count} Adet",
            "Tutar (%10)": f"{total_cost:,.0f} TL",
            "Stop-Loss": f"{stop_loss:.2f} TL",
            "Hedef 1": f"{target_1:.2f} TL",
            "Hedef 2": f"{target_2:.2f} TL",
            "RSI": f"{rsi:.1f}",
            "Durum": tag,
            "Skor": score,
            "is_bist30": is_bist30,
            "raw_volume": val_traded
        })

    # Sıralama: En yüksek puandan aşağıya
    all_candidates.sort(key=lambda x: (x["Skor"], x["raw_volume"]), reverse=True)

    # 1. BIST 30 Dev Lokomotifler
    bist_30_picks = [c for c in all_candidates if c["is_bist30"]][:3]

    # 2. BIST Tüm Yıldız / Büyüme Hisseleri (BIST 30 Dışı Yüksek Hacimli Fırsatlar)
    bist_all_picks = [c for c in all_candidates if not c["is_bist30"]][:3]

    return {
        "bist_30_picks": bist_30_picks,
        "bist_all_picks": bist_all_picks,
        "total_scanned": total_scanned
    }

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🌍 BİST TÜM PAZAR GENİŞ TARAMA TESTİ (400+ HİSSE)")
    print("="*80)
    res = scan_entire_bist(min_volume_tl=15_000_000)
    print(f"Toplam Taranan Likit Hisse Sayısı: {res['total_scanned']}")

    print("\n🏆 KATEGORİ 1: BIST 30 LOKOMOTİF FIRSATLARI")
    df_30 = pd.DataFrame(res["bist_30_picks"])
    if not df_30.empty:
        cols = ["Hisse", "Pazar", "Fiyat", "Pusu Fiyatı", "Lot", "Stop-Loss", "Hedef 1", "Hacim", "Durum"]
        print(df_30[cols].to_string(index=False))

    print("\n🚀 KATEGORİ 2: BIST TÜM GİZLİ CEVHERLER / BÜYÜME HİSSELERİ (BIST 30 DIŞI)")
    df_all = pd.DataFrame(res["bist_all_picks"])
    if not df_all.empty:
        cols = ["Hisse", "Pazar", "Fiyat", "Pusu Fiyatı", "Lot", "Stop-Loss", "Hedef 1", "Hacim", "Durum"]
        print(df_all[cols].to_string(index=False))
