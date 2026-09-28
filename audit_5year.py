"""
BIST 5 Yıllık Kapsamlı Başarı Oranı ve Performans Denetimi (5-Year Audit)
Farklı sektörlerden 10 lokomotif BIST hissesi üzerinde son 5 yıllık (2021-2026)
işlem başarı oranı, kâr faktörü ve net getiri hesaplaması.
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

from backtester import Backtester
from data_loader import fetch_data
from strategies.bist_alpha_master import BISTAlphaMasterStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy

init(autoreset=True)

# 10 Farklı Sektörü Temsil Eden Hisse Sepeti
REPRESENTATIVE_BASKET = [
    ("THYAO.IS", "Havacılık / Ulaştırma"),
    ("ASELS.IS", "Savunma / Teknoloji"),
    ("GARAN.IS", "Bankacılık"),
    ("TUPRS.IS", "Rafineri / Enerji"),
    ("KCHOL.IS", "Holding / Sanayi"),
    ("BIMAS.IS", "Perakende / Defansif"),
    ("EREGL.IS", "Demir-Çelik / Emtia"),
    ("FROTO.IS", "Otomotiv / İhracat"),
    ("TCELL.IS", "İletişim / Telekom"),
    ("SISE.IS",  "Cam / Sanayi")
]

def run_5year_audit():
    print(f"\n{Fore.CYAN}==========================================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  BIST 5 YILLIK STRATEJİ DENETİMİ (2021 - 2026 / 10 FARKLI SEKTÖR TEMSİLCİSİ)")
    print(f"{Fore.CYAN}=========================================================================================={Style.RESET_ALL}\n")

    strat = BISTAlphaMasterStrategy(min_adx=18.0)

    rows = []
    total_trades_all = 0
    total_wins_all = 0
    total_losses_all = 0
    total_pnl_all = 0.0
    initial_per_stock = 100_000.0

    for ticker, sector in REPRESENTATIVE_BASKET:
        clean_t = ticker.replace(".IS", "")
        print(f"⏳ {clean_t} ({sector}) 5 yıllık verisi indiriliyor ve taranıyor...", end="\r")
        df = fetch_data(ticker, period="5y", interval="1d", use_cache=True)
        if df.empty or len(df) < 200:
            continue

        bt = Backtester(
            strategy=strat,
            initial_capital=initial_per_stock,
            commission_rate=0.001,
            slippage=0.0005,
            stop_loss_pct=0.035,
            take_profit_pct=9.99,   # Kâr tavanı serbest bırakıldı
            trailing_stop_pct=0.05, # %5 İz süren stop ile büyük dalgayı yakala
            use_trailing_stop=True
        )
        res = bt.run(df, ticker=ticker)

        net_pnl = res.final_equity - initial_per_stock
        total_pnl_all += net_pnl
        total_trades_all += res.total_trades
        total_wins_all += res.winning_trades
        total_losses_all += res.losing_trades

        rows.append({
            "Hisse": clean_t,
            "Sektör": sector,
            "Bitiş (TL)": f"{res.final_equity:,.0f} TL",
            "Net Kâr (TL)": f"{net_pnl:+,.0f} TL",
            "Getiri %": f"%{res.total_return_pct:+.1f}",
            "İşlem": res.total_trades,
            "Kazanma %": f"%{res.win_rate_pct:.1f}",
            "Kâr Faktörü": f"{res.profit_factor:.2f}",
            "Max DD": f"-%{res.max_drawdown_pct:.1f}"
        })

    print("\n" + "=" * 105)
    df_res = pd.DataFrame(rows)
    print(tabulate(df_res, headers="keys", tablefmt="grid", showindex=False))

    # Portföy Toplam İstatistikleri
    overall_win_rate = (total_wins_all / total_trades_all * 100.0) if total_trades_all > 0 else 0.0
    total_initial = initial_per_stock * len(rows)
    total_final = total_initial + total_pnl_all
    total_roi = (total_pnl_all / total_initial) * 100.0

    print(f"\n{Fore.YELLOW}{Style.BRIGHT}" + "=" * 65)
    print(f"  🏆 5 YILLIK GENEL PORTFÖY BAŞARI KARNESİ (ÖZET)")
    print("=" * 65 + Style.RESET_ALL)
    print(f"  • İncelenen Süre         : Son 5 Yıl (Günlük Barlar)")
    print(f"  • Toplam Başlangıç       : {total_initial:,.0f} TL (10 hisseye 100.000 TL)")
    print(f"  • Toplam Bitiş Sermayesi : {Fore.GREEN}{Style.BRIGHT}{total_final:,.0f} TL{Style.RESET_ALL}")
    print(f"  • Toplam Net Kâr         : {Fore.GREEN}{Style.BRIGHT}+{total_pnl_all:,.0f} TL (%{total_roi:+.1f}){Style.RESET_ALL}")
    print(f"  • Toplam Açılan İşlem    : {total_trades_all} Adet")
    print(f"  • Kazanan İşlemler       : {Fore.GREEN}{total_wins_all} Adet{Style.RESET_ALL}")
    print(f"  • Kaybeden İşlemler      : {Fore.RED}{total_losses_all} Adet{Style.RESET_ALL}")
    print(f"  • GENEL BAŞARI ORANI     : {Fore.CYAN}{Style.BRIGHT}%{overall_win_rate:.1f}{Style.RESET_ALL} (Win Rate)")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    run_5year_audit()
