"""
BIST Momentum ve Göreceli Güç (Relative Strength) Analiz Motoru
Borsa İstanbul'da ivmesi (hızı), işlem hacmi ve kırılım potansiyeli en yüksek hisseleri tespit eder.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import List, Optional, Dict, Any
import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init

from config import BIST_30_TICKERS
from data_loader import fetch_data, normalize_ticker
from indicators import add_all_indicators

init(autoreset=True)

class BISTMomentumRadar:
    def __init__(self, tickers: Optional[List[str]] = None):
        self.tickers = tickers or BIST_30_TICKERS

    def evaluate_momentum(self, ticker: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Tek bir hisse için 0 - 100 arası Momentum Skoru hesaplar."""
        ticker = normalize_ticker(ticker)
        if df is None or df.empty:
            df = fetch_data(ticker, period="1y", interval="1d", use_cache=True)

        if df.empty or len(df) < 30:
            return {"ticker": ticker, "momentum_score": 0.0, "verdict": "Yetersiz Veri"}

        df = add_all_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0.0
        details = {}

        # 1. 10 Günlük Hız (ROC 10) - Maks 30 Puan
        roc_10 = float(last.get("ROC_10", 0.0))
        if roc_10 >= 10.0:
            roc_score = 30.0
            roc_status = f"Çok Hızlı Fırlama (%{roc_10:+.1f})"
        elif roc_10 >= 5.0:
            roc_score = 25.0
            roc_status = f"Güçlü İvme (%{roc_10:+.1f})"
        elif roc_10 >= 2.0:
            roc_score = 18.0
            roc_status = f"Pozitif İvme (%{roc_10:+.1f})"
        elif roc_10 >= -2.0:
            roc_score = 10.0
            roc_status = f"Yatay İvme (%{roc_10:+.1f})"
        else:
            roc_score = 0.0
            roc_status = f"Negatif İvme (%{roc_10:+.1f})"
        score += roc_score
        details["ROC_10"] = roc_10

        # 2. Zirve Kırılımı ve 52H Zirveye Yakınlık - Maks 30 Puan
        dist_52w = float(last.get("Dist_To_52w_High_Pct", 99.0))
        is_breakout_20 = bool(last.get("Breakout_20d", False))

        breakout_score = 0.0
        if is_breakout_20:
            breakout_score += 15.0
        if dist_52w <= 3.0:
            breakout_score += 15.0
        elif dist_52w <= 8.0:
            breakout_score += 10.0
        elif dist_52w <= 15.0:
            breakout_score += 5.0
        score += breakout_score
        details["Zirve_Durumu"] = {
            "20G_Kirilim": is_breakout_20,
            "52H_Mesafe_Pct": round(dist_52w, 1)
        }

        # 3. Hacim İvmesi (Volume Surge) - Maks 20 Puan
        vol_ratio = float(last.get("Vol_Ratio", 1.0))
        if vol_ratio >= 2.0:
            vol_score = 20.0
        elif vol_ratio >= 1.4:
            vol_score = 15.0
        elif vol_ratio >= 1.0:
            vol_score = 10.0
        else:
            vol_score = 3.0
        score += vol_score
        details["Hacim_Kati"] = round(vol_ratio, 1)

        # 4. RSI & Trend Uyumu - Maks 20 Puan
        rsi = float(last.get("RSI", 50.0))
        ema_bull = bool(last.get("EMA_21", 0) > last.get("EMA_50", 0))
        rsi_score = 0.0
        if 55.0 <= rsi <= 72.0 and ema_bull:
            rsi_score = 20.0
        elif 50.0 <= rsi < 55.0 and ema_bull:
            rsi_score = 14.0
        elif rsi > 75.0:
            rsi_score = 8.0  # Aşırı alım
        else:
            rsi_score = 4.0
        score += rsi_score
        details["RSI"] = round(rsi, 1)

        final_score = round(min(score, 100.0), 1)

        if final_score >= 80.0:
            verdict = "LİDER MOMENTUM (Zirve Patlaması & Hacim)"
        elif final_score >= 65.0:
            verdict = "GÜÇLÜ İVME (Yükseliş Adayı)"
        elif final_score >= 45.0:
            verdict = "ORTA / DENGELİ"
        else:
            verdict = "ZAYIF / DÜŞÜK İVME"

        return {
            "ticker": ticker,
            "momentum_score": final_score,
            "verdict": verdict,
            "roc_10": roc_10,
            "vol_ratio": round(vol_ratio, 1),
            "dist_52w": round(dist_52w, 1),
            "breakout_20d": is_breakout_20,
            "rsi": round(rsi, 1),
            "close": round(last["Close"], 2)
        }

    def scan_momentum_leaders(self) -> pd.DataFrame:
        """Tüm BIST 30 hisselerini tarayarak en yüksek ivmeli liderleri sıralar."""
        results = []
        total = len(self.tickers)
        print(f"\n🚀 BIST 30 MOMENTUM RADARI BAŞLATILIYOR ({total} hisse taranıyor)...\n")

        for idx, ticker in enumerate(self.tickers, 1):
            print(f"[{idx}/{total}] {ticker} momentum inceleniyor...", end="\r")
            try:
                res = self.evaluate_momentum(ticker)
                results.append({
                    "Hisse": ticker.replace(".IS", ""),
                    "Son Fiyat": f"{res['close']:.2f}",
                    "Momentum Skor": res["momentum_score"],
                    "10G Hız (ROC)": f"%{res['roc_10']:+.1f}",
                    "Hacim Katı": f"{res['vol_ratio']}x",
                    "52H Zirve Mesafe": f"%{res['dist_52w']:.1f}",
                    "20G Kırılım": "EVET 🚀" if res["breakout_20d"] else "Hayır",
                    "RSI": res["rsi"],
                    "Durum": res["verdict"]
                })
            except Exception:
                pass

        print("\n" + "=" * 85)
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res.sort_values(by="Momentum Skor", ascending=False, inplace=True)
        return df_res

    def print_radar_table(self, df_res: pd.DataFrame):
        """Momentum liderlerini renkli tablo olarak ekrana basar."""
        if df_res.empty:
            print("Veri bulunamadı.")
            return

        colored = []
        for _, row in df_res.iterrows():
            sc = row["Momentum Skor"]
            if sc >= 75:
                c = Fore.GREEN + Style.BRIGHT
            elif sc >= 50:
                c = Fore.YELLOW
            else:
                c = Fore.WHITE

            colored.append([
                c + row["Hisse"],
                row["Son Fiyat"],
                c + f"{sc:.1f}" + Style.RESET_ALL,
                row["10G Hız (ROC)"],
                row["Hacim Katı"],
                row["52H Zirve Mesafe"],
                row["20G Kırılım"],
                row["RSI"],
                c + row["Durum"] + Style.RESET_ALL
            ])

        headers = ["Hisse", "Fiyat", "Momentum (100)", "10G Hız %", "Hacim", "52H Mesafe", "20G Kırılım", "RSI", "İvme Durumu"]
        print(tabulate(colored, headers=headers, tablefmt="fancy_grid", stralign="center"))
