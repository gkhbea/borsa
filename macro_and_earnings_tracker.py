"""
BIST 360 - Makroekonomi, Gündem ve Bilanço Takip Motoru
1. XU100 Endeks Trendi, Dolar/TL Kuru, Brent Petrol ve Altın makro göstergelerini izler.
2. BIST Elit hisselerinin bilançolarını (Kârlılık, Borçluluk, Nakit Durumu, ROE) analiz eder.
3. Kıdemli bir BIST Brokerı gibi sentezleyerek günlük piyasa iklimini ve işlem stratejisini belirler.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import yfinance as yf
import pandas as pd
from config import ELITE_LIQUID_TICKERS
from fundamental_analyzer import evaluate_fundamentals

def get_macro_snapshot():
    """Makroekonomik verileri çeker ve piyasa iklimini belirler."""
    symbols = {
        "XU100": "XU100.IS",
        "USDTRY": "USDTRY=X",
        "BRENT": "BZ=F",
        "ALTIN": "GC=F"
    }
    
    data = {}
    for name, sym in symbols.items():
        try:
            h = yf.Ticker(sym).history(period="1mo")
            if not h.empty and len(h) >= 2:
                last_p = h["Close"].iloc[-1]
                prev_p = h["Close"].iloc[-2]
                pct_chg = ((last_p / prev_p) - 1) * 100
                
                # Hareketli ortalama trendi
                ema20 = h["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
                trend = "YÜKSELİŞ 🟢" if last_p >= ema20 else "DÜZELTME / TEMKİN 🟡"
                
                data[name] = {
                    "last": round(last_p, 2),
                    "change_pct": round(pct_chg, 2),
                    "trend": trend,
                    "ema20": round(ema20, 2)
                }
            else:
                data[name] = {"last": 0.0, "change_pct": 0.0, "trend": "VERİ YOK", "ema20": 0.0}
        except Exception:
            data[name] = {"last": 0.0, "change_pct": 0.0, "trend": "HATA", "ema20": 0.0}

    # Broker Piyasa İklimi Değerlendirmesi
    xu = data.get("XU100", {})
    brent = data.get("BRENT", {})
    usd = data.get("USDTRY", {})
    
    regime = "NÖTR"
    verdict = ""
    
    if xu.get("trend") == "YÜKSELİŞ 🟢":
        regime = "BOĞA / RİSK İŞTAHI POZİTİF"
        verdict = "Endeks 20 günlük ortalamasının üzerinde. Lokomotif hisselerde seçici alım iştahı korunuyor."
    else:
        regime = "TEMKİNLİ / DÜZELTME REGİMİ"
        verdict = "Endeks dinlenme/düzeltme aşamasında. Körü körüne alım yapılmamalı, sadece güçlü pusu destekleri beklenmeli."

    sector_note = []
    if brent.get("change_pct", 0) < -1.0:
        sector_note.append("Brent petroldeki gerileme havacılık (THYAO) ve sanayi marjları için maliyet avantajı yaratıyor.")
    elif brent.get("change_pct", 0) > 1.5:
        sector_note.append("Brent petroldeki yükseliş rafineri marjlarını desteklerken (TUPRS), havacılıkta yakıt maliyetini artırabilir.")

    if usd.get("change_pct", 0) > 0.3:
        sector_note.append("Dolar/TL hareketliliği döviz fazlası ve güçlü ihracatçı hisseleri (THYAO, ASELS, SISE) ön plana çıkarır.")

    return {
        "metrics": data,
        "regime": regime,
        "broker_verdict": verdict,
        "sector_note": " ".join(sector_note) if sector_note else "Döviz ve emtia dengeli seyrediyor; tahta bazlı hikayeler takip edilecek."
    }

def get_elite_balance_sheets():
    """Elit 10 lokomotifin güncel bilanço kârlılık ve borçluluk röntgenini çıkarır."""
    results = []

    for ticker in ELITE_LIQUID_TICKERS:
        clean_t = ticker.replace(".IS", "")
        f_data = evaluate_fundamentals(ticker)
        raw = f_data.get("raw", {})
        score = f_data.get("score", 0.0)

        roe = raw.get("roe", 0.0)
        debt_to_eq = raw.get("debt_to_equity", 0.0)
        margin = raw.get("profit_margin", 0.0)
        pe = raw.get("forward_pe") or raw.get("trailing_pe") or 0.0
        pb = raw.get("price_to_book", 0.0)

        # Bilanço Güvenlik Notu
        bilanco_durumu = "ORTA"
        if score >= 75.0:
            bilanco_durumu = "💎 KAYA GİBİ SAĞLAM (Kârlı & Güçlü Nakit)"
        elif score >= 60.0:
            bilanco_durumu = "🟢 SAĞLIKLI FİNANSALLAR"
        elif score >= 45.0:
            bilanco_durumu = "🟡 DENGELİ / NÖTR"
        else:
            bilanco_durumu = "⚠️ BORÇ / MARJ BASKISI"

        results.append({
            "Hisse": clean_t,
            "Bilanço Gücü": bilanco_durumu,
            "Temel Puan": round(score, 1),
            "ROE (Özsermaye Kârı)": f"%{roe*100:.1f}" if roe else "-",
            "Net Kâr Marjı": f"%{margin*100:.1f}" if margin else "-",
            "Borç/Özkaynak": f"{debt_to_eq:.1f}" if debt_to_eq else "Nakit Artıda",
            "F/K": f"{pe:.1f}" if pe else "-",
            "PD/DD": f"{pb:.2f}" if pb else "-"
        })

    results.sort(key=lambda x: x["Temel Puan"], reverse=True)
    return results

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🌍 GÜNLÜK MAKROEKONOMİK VE PİYASA İKLİMİ RAPORU")
    print("="*80)
    macro = get_macro_snapshot()
    print(f"BIST 100 Regimi: {macro['regime']}")
    print(f"Broker Yorumu  : {macro['broker_verdict']}")
    print(f"Sektörel Etki  : {macro['sector_note']}\n")
    for k, v in macro["metrics"].items():
        print(f"  • {k:8}: {v['last']:10.2f} (Günlük: {v['change_pct']:+5.2f}%) | Trend: {v['trend']}")

    print("\n" + "="*80)
    print("📊 ELİT LOKOMOTİFLERİN BİLANÇO VE FİNANSAL SAĞLIK LİSTESİ")
    print("="*80)
    sheets = get_elite_balance_sheets()
    df = pd.DataFrame(sheets)
    print(df.to_string(index=False))
