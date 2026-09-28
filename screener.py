import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import Optional, List
import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init

from config import BIST_30_TICKERS
from data_loader import fetch_data
from indicators import add_all_indicators
from strategies.base import BaseStrategy
from strategies.ensemble import EnsembleStrategy

init(autoreset=True)

class BISTScreener:
    def __init__(self, tickers: Optional[List[str]] = None, strategy: Optional[BaseStrategy] = None):
        self.tickers = tickers or BIST_30_TICKERS
        self.strategy = strategy or EnsembleStrategy()

    def run_screen(self, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        """Tüm hedef BIST hisselerini tarar ve özet tablo oluşturur."""
        results = []
        total = len(self.tickers)

        print(f"\n🚀 BIST 30 Tarama Başlatılıyor ({len(self.tickers)} hisse, Strateji: {self.strategy.name})...\n")

        for idx, ticker in enumerate(self.tickers, 1):
            print(f"[{idx}/{total}] {ticker} taranıyor...", end="\r")
            df = fetch_data(ticker, period=period, interval=interval, use_cache=True)
            if df.empty or len(df) < 30:
                continue

            df = add_all_indicators(df)
            df = self.strategy.generate_signals(df)

            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]

            close_price = last_row["Close"]
            daily_change_pct = ((close_price - prev_row["Close"]) / prev_row["Close"]) * 100.0
            rsi = last_row["RSI"]
            st_trend = "BOĞA 🟢" if last_row["SuperTrend_Direction"] == 1 else "AYI 🔴"
            ema_trend = "POZİTİF" if last_row["EMA_21"] > last_row["EMA_50"] else "NEGATİF"
            vol_ratio = last_row.get("Vol_Ratio", 1.0)
            signal = last_row.get("Signal", 0)
            reason = last_row.get("Reason", "")

            # Sinyal durumu
            if signal == 1:
                sig_str = "AL 🚀"
            elif signal == -1:
                sig_str = "SAT ⚠️"
            else:
                sig_str = "TUT / İZLE"

            results.append({
                "Hisse": ticker.replace(".IS", ""),
                "Son Fiyat (TL)": f"{close_price:.2f}",
                "Günlük %": f"{daily_change_pct:+.2f}%",
                "RSI (14)": f"{rsi:.1f}",
                "SuperTrend": st_trend,
                "EMA 21/50": ema_trend,
                "Hacim Katı": f"{vol_ratio:.1f}x",
                "Sinyal": sig_str,
                "Açıklama": reason[:32] if reason else "-"
            })

        print("\n" + "=" * 80)
        df_res = pd.DataFrame(results)
        return df_res

    def print_pretty_table(self, df_res: pd.DataFrame):
        """Sonuçları renkli ve okunabilir bir tablo olarak ekrana basar."""
        if df_res.empty:
            print("Taranacak veri bulunamadı.")
            return

        colored_rows = []
        for _, row in df_res.iterrows():
            sig = row["Sinyal"]
            if "AL" in sig:
                color = Fore.GREEN + Style.BRIGHT
            elif "SAT" in sig:
                color = Fore.RED + Style.BRIGHT
            else:
                color = Fore.WHITE

            chg_val = float(row["Günlük %"].replace("%", ""))
            chg_color = Fore.GREEN if chg_val > 0 else (Fore.RED if chg_val < 0 else Fore.WHITE)

            colored_rows.append([
                color + row["Hisse"],
                row["Son Fiyat (TL)"],
                chg_color + row["Günlük %"] + Style.RESET_ALL,
                row["RSI (14)"],
                row["SuperTrend"],
                row["EMA 21/50"],
                row["Hacim Katı"],
                color + row["Sinyal"] + Style.RESET_ALL,
                row["Açıklama"]
            ])

        headers = [
            "Hisse", "Son Fiyat", "Değişim %", "RSI(14)", "SuperTrend", "EMA 21/50", "Hacim Katı", "Sinyal", "Gerekçe"
        ]
        table_output = tabulate(colored_rows, headers=headers, tablefmt="fancy_grid", stralign="center")
        print(table_output)
        
        # Özet İstatistikler
        buy_count = sum(1 for _, r in df_res.iterrows() if "AL" in r["Sinyal"])
        sell_count = sum(1 for _, r in df_res.iterrows() if "SAT" in r["Sinyal"])
        print(f"\n📊 [TARAMA ÖZETİ] İncelenen: {len(df_res)} | AL Sinyali: {buy_count} | SAT Sinyali: {sell_count}")
