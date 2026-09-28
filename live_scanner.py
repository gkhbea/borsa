"""
Canlı BIST 30 Fırsat ve Pusu Radarı
Şu anki güncel BIST verileriyle alım fırsatlarını ve pusuya yatan hisseleri listeler.
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
from bist_360 import BIST360Analyzer

init(autoreset=True)

def scan_live_opportunities():
    strat = BISTSniperStrategy()
    analyzer = BIST360Analyzer()

    print(f"\n{Fore.GREEN}{Style.BRIGHT}==========================================================================")
    print("  CANLI BIST 30 FIRSAT VE PUSU RADARI (ŞU AN MASADA NE VAR?)")
    print("==========================================================================" + Style.RESET_ALL)

    signals = []
    total = len(BIST_30_TICKERS)

    for idx, ticker in enumerate(BIST_30_TICKERS, 1):
        clean_t = ticker.replace(".IS", "")
        print(f"[{idx}/{total}] {clean_t} canlı verisi taranıyor...", end="\r")
        df = fetch_data(ticker, period="6mo", interval="1d", use_cache=False)
        if df.empty or len(df) < 50:
            continue

        df = strat.generate_signals(df)
        last_row = df.iloc[-1]
        
        # Son 3 bar içinde al sinyali var mı?
        recent_buys = df.iloc[-3:]["Signal"].tolist()
        is_fresh = last_row.get("Signal", 0) == 1
        is_hot = (1 in recent_buys) and not is_fresh

        try:
            r360 = analyzer.analyze_single_stock(ticker)
            score_360 = r360["total_score"]
            verdict = r360["final_verdict"].split("(")[0].strip()
        except Exception:
            score_360 = 50.0
            verdict = "Nötr"

        if is_fresh:
            status = "ALIS FIRSATI 🚀"
        elif is_hot:
            status = "YAKIN PUSUDA 👀"
        else:
            status = "BEKLEMEDE ⚪"

        signals.append({
            "Hisse": clean_t,
            "Son Fiyat": f"{last_row['Close']:.2f} TL",
            "Sniper Sinyal": status,
            "SuperTrend": "BOGA 🟢" if last_row["SuperTrend_Direction"] == 1 else "AYI 🔴",
            "BIST 360 Skor": score_360,
            "Görünüm": verdict
        })

    print("\n" + "=" * 90)
    df_res = pd.DataFrame(signals)
    if not df_res.empty:
        # Öncelik: Yüksek BIST 360 skoru
        df_res.sort_values(by="BIST 360 Skor", ascending=False, inplace=True)
        print(tabulate(df_res.head(15), headers="keys", tablefmt="grid", showindex=False))

if __name__ == "__main__":
    scan_live_opportunities()
