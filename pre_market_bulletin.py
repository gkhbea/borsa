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

from config import BIST_30_TICKERS, DEFAULT_INITIAL_CAPITAL
from data_loader import fetch_data
from strategies.bist_sniper import BISTSniperStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy
from bist_360 import BIST360Analyzer

init(autoreset=True)

def generate_morning_bulletin():
    sniper = BISTSniperStrategy()
    momentum = MomentumBreakoutStrategy()
    analyzer = BIST360Analyzer()

    # Portföy Dağılımı: 100.000 TL sermaye, 3 ana yuva = Yuva başına ~33.000 TL
    slot_capital = DEFAULT_INITIAL_CAPITAL / 3

    candidates = []

    print(f"\n{Fore.YELLOW}==========================================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  ☀️  BIST 360 SEANS ÖNCESİ ALGORİTMİK HİSSE LİSTESİ (SAAT 09:30 RAPORU)")
    print(f"{Fore.YELLOW}=========================================================================================={Style.RESET_ALL}")
    print(f"Toplam Sermaye: {DEFAULT_INITIAL_CAPITAL:,.0f} TL | Pozisyon Başına Ayrılan: {slot_capital:,.0f} TL | Disiplin: Maks 3 Hisse\n")

    for ticker in BIST_30_TICKERS:
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

        stop_loss = round(close_p - (atr * 1.5), 2)
        target_1 = round(close_p + (atr * 2.5), 2)
        target_2 = round(close_p + (atr * 4.5), 2)

        # Kaç lot alınabilir?
        lot_count = int(slot_capital // close_p)
        total_cost = lot_count * close_p

        # Karar Mekanizması
        priority = 0
        tag = ""
        action_note = ""

        if sig_s == 1:
            priority = 100
            tag = "🔥 1. ÖNCELİK (SNIPER)"
            action_note = "Destekten Dönüş Başladı - Açılışta Pusu"
        elif sig_m == 1:
            priority = 95
            tag = "🚀 1. ÖNCELİK (MOMENTUM)"
            action_note = "Zirve Kırılımı + Güçlü Para Girişi"
        elif score_360 >= 70.0 and cmf > 0.05:
            priority = 85
            tag = "💎 2. ÖNCELİK (KURUMSAL ALIM)"
            action_note = "Tahta Toplanıyor, Çarpanlar Çok Cazip"
        elif score_360 >= 65.0 and cmf > 0.0:
            priority = 75
            tag = "⚡ 2. ÖNCELİK (GÜÇLÜ 360)"
            action_note = "Teknik/Temel/Takas Uyumu Pozitif"
        elif rec_s or rec_m:
            priority = 70
            tag = "👀 3. ÖNCELİK (PUSU LİSTESİ)"
            action_note = "Sinyal Çok Taze, Onay Bekleniyor"
        elif score_360 >= 60.0 and cmf > 0.0:
            priority = 60
            tag = "📊 3. ÖNCELİK (DİP DESTEK)"
            action_note = "Trend Pozitif, Stop Yakın Takip"

        if priority >= 60:
            candidates.append({
                "Hisse": clean_t,
                "Durum": tag,
                "Son Fiyat": f"{close_p:.2f} TL",
                "Önerilen Lot": f"{lot_count} Adet",
                "Toplam Tutar": f"{total_cost:,.0f} TL",
                "Stop-Loss (Zarar Kes)": f"{stop_loss:.2f} TL",
                "Hedef 1 (Kısa)": f"{target_1:.2f} TL",
                "Hedef 2 (Ana Trend)": f"{target_2:.2f} TL",
                "BIST 360": f"{score_360:.1f}",
                "Para Girişi": f"{cmf:+.2f}",
                "priority": priority,
                "score": score_360,
                "Strateji Notu": action_note
            })

    if not candidates:
        print("Bugün için yüksek güvenlikli işlem kriterlerini karşılayan hisse bulunamadı.")
        return

    # Sıralama: Önce Öncelik Derecesi, sonra 360 Skoru
    candidates.sort(key=lambda x: (x["priority"], float(x["score"])), reverse=True)

    # Tablo görünümü
    display_rows = []
    for c in candidates:
        display_rows.append({
            "Hisse": c["Hisse"],
            "Öncelik": c["Durum"],
            "Fiyat": c["Son Fiyat"],
            "Lot Sayısı": c["Önerilen Lot"],
            "Maliyet": c["Toplam Tutar"],
            "Zarar Kes (Stop)": c["Stop-Loss (Zarar Kes)"],
            "Hedef 1": c["Hedef 1 (Kısa)"],
            "Hedef 2": c["Hedef 2 (Ana Trend)"],
            "Skor": c["BIST 360"],
            "CMF": c["Para Girişi"]
        })

    df_report = pd.DataFrame(display_rows)
    print(tabulate(df_report, headers="keys", tablefmt="fancy_grid", showindex=False))

    print(f"\n{Fore.GREEN}{Style.BRIGHT}💡 BROKER YÖNETİCİ NOTU (PORTFÖY DİSİPLİNİ):")
    print(f"1. Yukarıdaki listeden en yüksek öncelikli **en fazla 3 hisse** seçilmelidir (Risk bölüştürme).")
    print(f"2. Stop-Loss seviyelerinin altına seans içi sarkmalarda kesinlikle inatlaşılmamalıdır.")
    print(f"3. Hedef 1'e ulaşıldığında pozisyonun %50'si realize edilip, stop seviyesi giriş fiyatına (başa baş) çekilmelidir.")
    print(f"==========================================================================================\n")

if __name__ == "__main__":
    generate_morning_bulletin()
