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
from strategies import AVAILABLE_STRATEGIES
from visualizer import create_interactive_chart

init(autoreset=True)

def run_audit():
    basket = ["THYAO.IS", "ASELS.IS", "GARAN.IS", "TUPRS.IS", "KCHOL.IS"]
    strategies_to_test = ["momentum", "supertrend", "ensemble", "rsi_bb"]

    all_summary = []
    detailed_trades = {}

    print(f"\n{Fore.CYAN}==========================================================================")
    print(f"{Fore.WHITE}{Style.BRIGHT}  BIST LOKOMOTIFLERINDE 2 YILLIK GECMIS TESTLERI (BACKTEST AUDIT)")
    print(f"{Fore.CYAN}=========================================================================={Style.RESET_ALL}\n")

    for ticker in basket:
        clean_t = ticker.replace(".IS", "")
        print(f"⏳ {clean_t} verileri inceleniyor...")
        df = fetch_data(ticker, period="2y", interval="1d", use_cache=True)
        if df.empty:
            continue

        for strat_key in strategies_to_test:
            strat = AVAILABLE_STRATEGIES[strat_key]()
            bt = Backtester(
                strategy=strat,
                initial_capital=100_000.0,
                commission_rate=0.001,
                slippage=0.0005,
                stop_loss_pct=0.03,
                take_profit_pct=0.06,
                trailing_stop_pct=0.025,
                use_trailing_stop=True
            )
            res = bt.run(df, ticker=ticker)
            chart_path = create_interactive_chart(res)

            all_summary.append({
                "Hisse": clean_t,
                "Strateji": strat_key,
                "Bitis Sermayesi": f"{res.final_equity:,.0f} TL",
                "Net Getiri": f"%{res.total_return_pct:+.2f}",
                "Al-Tut %": f"%{res.buy_hold_return_pct:+.2f}",
                "Islem": res.total_trades,
                "Kazanma %": f"%{res.win_rate_pct:.1f}",
                "Kar Faktoru": f"{res.profit_factor:.2f}",
                "Max DD": f"-%{res.max_drawdown_pct:.1f}"
            })

            # En iyi stratejilerin son işlemlerini sakla
            if strat_key in ("momentum", "supertrend") and res.trades:
                detailed_trades[f"{clean_t}_{strat_key}"] = res.trades[-3:]

    print("\n" + "=" * 95)
    print(f"{Fore.YELLOW}{Style.BRIGHT}📊 2 YILLIK STRATEJI KARŞILAŞTIRMA MATRISI (100.000 TL BASLANGIC)")
    print("=" * 95)

    df_sum = pd.DataFrame(all_summary)
    print(tabulate(df_sum, headers="keys", tablefmt="grid", showindex=False))

    # Öne Çıkan Gerçekleşmiş İşlemler
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🎯 ZAMANINDA VERILEN SINYALLERIN AYRINTILI DÖKÜMÜ (SON GERÇEKLEŞMELER):")
    print("=" * 95)
    for key, trades in detailed_trades.items():
        hisse, st = key.split("_")
        print(f"\n📌 Hisse: {Fore.CYAN}{hisse}{Style.RESET_ALL} | Strateji: {Fore.YELLOW}{st}{Style.RESET_ALL}")
        for t in trades:
            c = Fore.GREEN if t.pnl > 0 else Fore.RED
            print(f"  • Giriş: {str(t.entry_date)[:10]} @ {t.entry_price:.2f} TL  ➔  "
                  f"Çıkış: {str(t.exit_date)[:10]} @ {t.exit_price:.2f} TL | "
                  f"Net Kâr: {c}{t.pnl:+,.0f} TL (%{t.pnl_pct:+.2f}){Style.RESET_ALL} | Neden: {t.exit_reason}")

if __name__ == "__main__":
    run_audit()
