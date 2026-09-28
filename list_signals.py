"""
BIST Güncel Sinyal ve Fırsat Listesi
Tüm aktif al-sat sinyallerini, pusu seviyelerini, stop-loss ve hedef fiyatları listeler.
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

from config import BIST_30_TICKERS
from data_loader import fetch_data
from strategies.bist_sniper import BISTSniperStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy
from bist_360 import BIST360Analyzer

init(autoreset=True)

def get_all_signals():
    sniper = BISTSniperStrategy()
    momentum = MomentumBreakoutStrategy()
    analyzer = BIST360Analyzer()

    rows = []
    print(f"\n{Fore.CYAN}==========================================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  BIST GÜNCEL SİNYAL VE İŞLEM LİSTESİ (CANLI BROKER RADARI)")
    print(f"{Fore.CYAN}=========================================================================================={Style.RESET_ALL}\n")

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

        # Son 3 bar içinde alım sinyali geldi mi?
        rec_s = 1 in df_s.iloc[-3:]["Signal"].tolist()
        rec_m = 1 in df_m.iloc[-3:]["Signal"].tolist()

        r360 = analyzer.analyze_single_stock(ticker)
        score_360 = r360["total_score"]
        cmf_flow = r360["takas"]["cmf"]

        stop_loss = round(close_p - (atr * 1.5), 2)
        take_profit = round(close_p + (atr * 3.2), 2)

        durum = "BEKLEMEDE"
        sebep = "-"

        if sig_s == 1:
            durum = "🔥 AKTİF AL (SNIPER)"
            sebep = "EMA 21 Desteğe Oturma ve Dönüş"
        elif sig_m == 1:
            durum = "🚀 AKTİF AL (MOMENTUM)"
            sebep = "20G Zirve Kırılımı + Hacim"
        elif rec_s or rec_m:
            durum = "👀 YAKIN PUSU (DÖNÜŞ AŞAMASI)"
            sebep = "Tetik Çok Yakın / Güçlü İvme"
        elif score_360 >= 65.0:
            durum = "💎 DİP TOPLAMA (360 ONAYLI)"
            sebep = "Temel Çarpanlar & Takas Çok Cazip"

        if durum != "BEKLEMEDE":
            rows.append({
                "Hisse": clean_t,
                "Son Fiyat": f"{close_p:.2f} TL",
                "Sinyal Durumu": durum,
                "Gerekçe": sebep,
                "Zarar Kes (Stop)": f"{stop_loss:.2f} TL",
                "İlk Hedef (Kâr)": f"{take_profit:.2f} TL",
                "BIST 360 Skor": f"{score_360:.1f}",
                "Para Akışı (CMF)": f"{cmf_flow:+.2f}"
            })

    df_res = pd.DataFrame(rows)
    if not df_res.empty:
        # Önce Aktif Al sinyallerini, sonra yüksek 360 skorluları getir
        df_res.sort_values(by="BIST 360 Skor", ascending=False, inplace=True)
        print(tabulate(df_res, headers="keys", tablefmt="grid", showindex=False))
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✅ Toplam {len(df_res)} hissede işlem ve pusu fırsatı tespit edildi.")
    else:
        print("Şu anda şartları sağlayan açık sinyal bulunamadı.")

if __name__ == "__main__":
    get_all_signals()
