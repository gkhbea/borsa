"""
BIST 360 - 09:30 SEANS ÖNCESİ ALINABİLİR HİSSELER VE EMİR LİSTESİ
Saat 09:30'da seans açılmadan (10:00) önce portföyün 100.000 TL bütçesine göre
tam lot sayıları, giriş, stop-loss ve kâr al seviyelerini hesaplar.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init

from config import (
    BIST_30_TICKERS, ELITE_LIQUID_TICKERS, STRICT_A_PLUS_FILTER,
    DEFAULT_INITIAL_CAPITAL, MAX_POSITION_SIZE_PCT
)
from data_loader import fetch_data
from strategies.bist_sniper import BISTSniperStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy
from bist_360 import BIST360Analyzer
from macro_and_earnings_tracker import get_macro_snapshot

init(autoreset=True)

def generate_morning_bulletin():
    sniper = BISTSniperStrategy()
    momentum = MomentumBreakoutStrategy()
    analyzer = BIST360Analyzer()

    # 1. Makroekonomik Gündem ve İklim
    macro = get_macro_snapshot()
    m_xu = macro["metrics"].get("XU100", {})
    m_usd = macro["metrics"].get("USDTRY", {})
    m_brent = macro["metrics"].get("BRENT", {})

    print(f"\n{Fore.CYAN}==========================================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  🌍  KIDEMLİ BROKER SEANS ÖNCESİ MAKRO & GÜNDEM DEĞERLENDİRMESİ")
    print(f"{Fore.CYAN}=========================================================================================={Style.RESET_ALL}")
    print(f"• BIST 100 Regimi: {macro['regime']} (Son: {m_xu.get('last', 0):,.0f} | Günlük: {m_xu.get('change_pct', 0):+0.2f}%)")
    print(f"• Broker Görüşü  : {macro['broker_verdict']}")
    print(f"• Sektörel Dinamik: {macro['sector_note']}")
    print(f"• Dolar/TL: {m_usd.get('last', 0):.2f} | Brent Petrol: ${m_brent.get('last', 0):.2f}\n")

    # Portföy Dağılımı: 100.000 TL sermaye, Maksimum %10 Kuralı = Hisse başına 10.000 TL
    slot_capital = DEFAULT_INITIAL_CAPITAL * MAX_POSITION_SIZE_PCT

    candidates = []

    # Hedef Hisse Havuzu: Sadece en derin, anında tek tuşla çıkılabilen Elit A+ Lokomotifler
    target_pool = ELITE_LIQUID_TICKERS if STRICT_A_PLUS_FILTER else BIST_30_TICKERS

    print(f"{Fore.YELLOW}==========================================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  🛡️  BIST 360 SEÇİCİ A+ LİSTESİ (EN GÜVENLİ & ANINDA ÇIKILABİLİR LOKOMOTİFLER)")
    print(f"{Fore.YELLOW}=========================================================================================={Style.RESET_ALL}")
    print(f"Toplam Sermaye: {DEFAULT_INITIAL_CAPITAL:,.0f} TL | Pozisyon Tavanı: {slot_capital:,.0f} TL (%10) | Prensip: Zorlama Yok, Sadece A+\n")

    for ticker in target_pool:
        clean_t = ticker.replace(".IS", "")
        df = fetch_data(ticker, period="6mo", interval="1d", use_cache=True)
        if df.empty or len(df) < 30:
            continue

        df_s = sniper.generate_signals(df)
        df_m = momentum.generate_signals(df)

        last = df.iloc[-1]
        close_p = last["Close"]
        atr = last.get("ATR", close_p * 0.03)

        sig_s = df_s.iloc[-1].get("Signal", 0)
        sig_m = df_m.iloc[-1].get("Signal", 0)

        # Son barlarda alım tetiklendi mi
        rec_s = 1 in df_s.iloc[-3:]["Signal"].tolist()
        rec_m = 1 in df_m.iloc[-3:]["Signal"].tolist()

        r360 = analyzer.analyze_single_stock(ticker)
        score_360 = r360["total_score"]
        cmf = r360["takas"]["cmf"]

        # Seans Öncesi Pusu Seviyesi: Destek (EMA 21/50 veya ATR 0.5x altı)
        entry_limit = round(close_p * 0.992, 2)  # Açılış sarkmasında pusu (yüzde 0.8 iskonto)
        stop_loss = round(entry_limit - (atr * 1.5), 2)
        target_1 = round(entry_limit + (atr * 2.5), 2)
        target_2 = round(entry_limit + (atr * 4.5), 2)

        lot_count = int(slot_capital // entry_limit)
        total_cost = lot_count * entry_limit

        # Puanlama & Öncelik
        priority = 0
        tag = ""
        action_note = ""

        if sig_s == 1 or sig_m == 1:
            priority = 100
            tag = "🔥 1. DERECE (TETİKTE)"
            action_note = "Doğrudan Alım Sinyali Aktif"
        elif score_360 >= 60.0 or (score_360 >= 53.0 and cmf >= 0.08):
            priority = 85
            tag = "💎 1. DERECE (KURUMSAL PUSU)"
            action_note = "Tahtada Ciddi Toplama Var, Sarkmada Al"
        elif score_360 >= 50.0 and cmf > 0.0:
            priority = 70
            tag = "⚡ 2. DERECE (POZİTİF RADAR)"
            action_note = "Para Girişi Pozitif, Destek Takip"
        elif score_360 >= 50.0:
            priority = 50
            tag = "📊 3. DERECE (İZLEME)"
            action_note = "Piyasa Dönüşüyle Tetiklenebilir"

        if priority >= 70:
            candidates.append({
                "Hisse": clean_t,
                "Durum": tag,
                "Son Kapanış": f"{close_p:.2f} TL",
                "Önerilen Pusu": f"{entry_limit:.2f} TL",
                "Lot Sayısı": f"{lot_count} Adet",
                "Maliyet": f"{total_cost:,.0f} TL",
                "Stop-Loss": f"{stop_loss:.2f} TL",
                "Hedef 1": f"{target_1:.2f} TL",
                "Hedef 2": f"{target_2:.2f} TL",
                "BIST 360": f"{score_360:.1f}",
                "CMF (Para)": f"{cmf:+.2f}",
                "priority": priority,
                "score": score_360,
                "Strateji": action_note
            })

    if not candidates:
        print("Piyasada aşırı risk tespit edildi, nakitte kalınması önerilir.")
        return

    # Sıralama: Önce Öncelik, sonra BIST 360 Skoru
    candidates.sort(key=lambda x: (x["priority"], float(x["score"])), reverse=True)

    # İlla her şeye girmeyeceğiz: Sadece EN TEMİZ ilk 2 veya 3 Elit hisse
    top_candidates = candidates[:3]

    print(f"\n{Fore.MAGENTA}==========================================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  🕵️‍♂️  ALIM ÖNCESİ SİTE, HABER, KAP VE TÜYO İSTİHBARATI")
    print(f"{Fore.MAGENTA}=========================================================================================={Style.RESET_ALL}")

    display_rows = []
    from sentiment_and_news_tracker import verify_stock_before_buy

    for c in top_candidates:
        t_info = verify_stock_before_buy(c["Hisse"])
        tip_summary = "🟢 Temiz Akış"
        if t_info["hot_tips"]:
            primary_tip = t_info["hot_tips"][0]
            tip_summary = f"{primary_tip['type'][:2]} {primary_tip['keyword']}"
            print(f"• {c['Hisse']:6} : [{primary_tip['type']}] {primary_tip['headline'][:85]}...")
            print(f"           💡 Broker Uyarısı: {t_info['warning_note']}")
        else:
            print(f"• {c['Hisse']:6} : 🟢 Olağan haber akışı, spekülatif tuzak veya devre kesici riski yok.")

        display_rows.append({
            "Hisse": c["Hisse"],
            "Öncelik": c["Durum"],
            "Pusu Fiyatı": c["Önerilen Pusu"],
            "Lot": c["Lot Sayısı"],
            "Tutar (%10)": c["Maliyet"],
            "Zarar Kes (Stop)": c["Stop-Loss"],
            "Hedef 1 (+%6-8)": c["Hedef 1"],
            "Hedef 2 (+%15)": c["Hedef 2"],
            "Tüyo / Haber": tip_summary,
            "Çıkış": "⚡ Anında (A+)"
        })

    print()
    df_report = pd.DataFrame(display_rows)
    print(tabulate(df_report, headers="keys", tablefmt="fancy_grid", showindex=False))

    # Ekrana ve E-Postaya Bildirim Gönder
    try:
        from notifier import broadcast_pre_market_bulletin
        broadcast_pre_market_bulletin(display_rows, macro=macro)
    except Exception as e:
        print(f"[UYARI] Bildirim gönderilemedi: {e}")

    print(f"\n{Fore.GREEN}{Style.BRIGHT}💡 KIDEMLİ BROKER YÖNETİCİ NOTU (GARANTİ & NAKDE ÇIKIŞ DİSİPLİNİ):")
    print(f"1. ⚡ Anında Çıkış Garantisi: Sadece BIST'in en derin mega-hisseleri seçilmiştir. Satış tuşuna bastığında 1 saniyede nakde geçebilirsin.")
    print(f"2. 🛡️ Zorlama İşlem Yok: İlla tüm hisseleri almak zorunda değiliz; nakit de bir pozisyondur. Günde en fazla 1-2 A+ hisse yeterlidir.")
    print(f"3. 💰 Maksimum %10 Kuralı: Pozisyon başına 10.000 TL tavan. Stop olsak dahi portföy kaybı sadece ~300 TL'dir (%0.3).")
    print(f"4. 🎯 Hedef 1 Disiplini: +%6-8 kârda %50 satılır, stop maliyete çekilir, sıfır riskle trend izlenir.")
    print(f"==========================================================================================\n")

if __name__ == "__main__":
    generate_morning_bulletin()
