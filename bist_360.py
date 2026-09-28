import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from typing import Dict, Any, List, Optional
import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init

from config import BIST_30_TICKERS, DEFAULT_TICKER
from data_loader import fetch_data, normalize_ticker
from indicators import add_all_indicators
from fundamental_analyzer import evaluate_fundamentals
from takas_analyzer import evaluate_takas_and_money_flow

init(autoreset=True)

class BIST360Analyzer:
    def __init__(self):
        pass

    def evaluate_technical(self, ticker: str, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Teknik Analiz Puanı hesaplar (0 - 100)."""
        ticker = normalize_ticker(ticker)
        if df is None or df.empty:
            df = fetch_data(ticker, period="6mo", interval="1d", use_cache=True)

        if df.empty or len(df) < 30:
            return {"score": 50.0, "verdict": "Yetersiz Veri", "details": {}}

        df = add_all_indicators(df)
        last = df.iloc[-1]

        score = 0.0
        details = {}

        # 1. SuperTrend (30 Puan)
        st_bull = last["SuperTrend_Direction"] == 1
        st_score = 30.0 if st_bull else 0.0
        score += st_score
        details["SuperTrend"] = {"score": st_score, "max": 30, "status": "Boğa 🟢" if st_bull else "Ayı 🔴"}

        # 2. Hareketli Ortalamalar EMA 21 / EMA 50 (25 Puan)
        ema_bull = last["EMA_21"] > last["EMA_50"]
        ema_score = 25.0 if ema_bull else 5.0
        score += ema_score
        details["EMA Trend"] = {"score": ema_score, "max": 25, "status": "Yükseliş" if ema_bull else "Düşüş"}

        # 3. RSI Momentum (25 Puan)
        rsi = float(last["RSI"])
        if 48.0 <= rsi <= 65.0:
            rsi_score = 25.0
            rsi_desc = f"Kusursuz Yükseliş Momenti ({rsi:.1f})"
        elif 40.0 <= rsi < 48.0:
            rsi_score = 18.0
            rsi_desc = f"Toparlanma Bölgesi ({rsi:.1f})"
        elif rsi > 70.0:
            rsi_score = 12.0
            rsi_desc = f"Aşırı Alım / Düzeltme Riski ({rsi:.1f})"
        elif rsi < 35.0:
            rsi_score = 10.0
            rsi_desc = f"Aşırı Satım / Tepki Yakın ({rsi:.1f})"
        else:
            rsi_score = 15.0
            rsi_desc = f"Nötr ({rsi:.1f})"
        score += rsi_score
        details["RSI (14)"] = {"score": rsi_score, "max": 25, "status": rsi_desc}

        # 4. MACD & Hacim (20 Puan)
        macd_bull = last["MACD"] > last["MACD_Signal"]
        macd_score = 12.0 if macd_bull else 2.0
        vol_surge = last.get("Vol_Surge", False)
        vol_score = 8.0 if vol_surge else 4.0
        score += (macd_score + vol_score)
        details["MACD & Hacim"] = {
            "score": macd_score + vol_score,
            "max": 20,
            "status": f"MACD: {'Pozitif' if macd_bull else 'Negatif'}, Hacim Patlaması: {'Evet' if vol_surge else 'Hayır'}"
        }

        final_score = round(min(score, 100.0), 1)
        if final_score >= 80.0:
            verdict = "Güçlü Boğa Trendi (Alım Uygun)"
        elif final_score >= 60.0:
            verdict = "Pozitif / Yükseliş Eğilimi"
        elif final_score >= 40.0:
            verdict = "Yatay / Kararsız Bölge"
        else:
            verdict = "Belirgin Ayı Trendi (Düşüş Baskısı)"

        return {
            "score": final_score,
            "verdict": verdict,
            "details": details,
            "last_close": round(last["Close"], 2)
        }

    def analyze_single_stock(self, ticker: str) -> Dict[str, Any]:
        """Bir hisseyi Teknik, Temel ve Takas olmak üzere 360 derece analiz eder."""
        ticker = normalize_ticker(ticker)
        df = fetch_data(ticker, period="6mo", interval="1d", use_cache=True)

        tech_res = self.evaluate_technical(ticker, df=df)
        fund_res = evaluate_fundamentals(ticker)
        takas_res = evaluate_takas_and_money_flow(ticker, df=df)

        tech_score = tech_res["score"]
        fund_score = fund_res["score"]
        takas_score = takas_res["score"]

        # Hibrit Ağırlıklandırma:
        # Teknik: %35 | Temel: %35 | Takas: %30
        total_score = round((tech_score * 0.35) + (fund_score * 0.35) + (takas_score * 0.30), 1)

        # Karar ve Uyarılar
        alerts = []
        if tech_score >= 75 and takas_score <= 40:
            alerts.append("⚠️ BOĞA TUZAĞI RİSKİ: Teknik yükseliyor ancak Takas/Para Akışından para çıkıyor!")
        if fund_score >= 75 and tech_score <= 40:
            alerts.append("🚨 DEĞER TUZAĞI DİKKATİ: Şirket temel olarak ucuz ancak teknik düşüş trendinde!")
        if takas_score >= 75 and tech_score <= 50 and fund_score >= 65:
            alerts.append("💎 SESSİZ TOPLAMA FIRSATI: Fiyat yatay/dipte iken kurumsal akıllı para hisseyi topluyor!")
        if total_score >= 80:
            alerts.append("🚀 SÜPER UYUM (TRIPLE BULL): Teknik, Temel ve Takas üçü birden alım teyidi veriyor!")

        # Genel Görünüm
        if total_score >= 80.0:
            final_verdict = "GÜÇLÜ AL (Kurumsal Destekli + Cazip Değerleme + Trend)"
        elif total_score >= 65.0:
            final_verdict = "KADEMELİ AL / OLUMLU (Yüksek Potansiyel)"
        elif total_score >= 45.0:
            final_verdict = "NÖTR / İZLE (Net Trend Beklenmeli)"
        elif total_score >= 30.0:
            final_verdict = "ZAYIF / RİSKLİ (Baskı Devam Ediyor)"
        else:
            final_verdict = "GÜÇLÜ SAT / KAÇIN (Pahalı, Trend Bozuk, Para Çıkışı)"

        return {
            "ticker": ticker,
            "total_score": total_score,
            "final_verdict": final_verdict,
            "tech": tech_res,
            "fund": fund_res,
            "takas": takas_res,
            "alerts": alerts
        }

    def print_report(self, res: Dict[str, Any]):
        """Tek bir hisse için ayrıntılı 360 derece kart raporu basar."""
        t = res["ticker"].replace(".IS", "")
        tot = res["total_score"]

        color = Fore.GREEN if tot >= 65 else (Fore.YELLOW if tot >= 45 else Fore.RED)

        print("\n" + f"{Fore.CYAN}{'=' * 70}")
        print(f"{Fore.WHITE}{Style.BRIGHT}  BIST 360 HIBRIT ANALIZ RAPORU: {t}")
        print(f"{Fore.CYAN}{'=' * 70}")
        print(f"  BIST 360 GENEL SKORU: {color}{Style.BRIGHT}{tot}/100{Style.RESET_ALL} -> {color}{res['final_verdict']}{Style.RESET_ALL}\n")

        # 3 Sütun Puan Dağılımı
        print(f"  * TEKNIK SKOR   (%35): {Fore.CYAN}{res['tech']['score']}/100{Style.RESET_ALL} | {res['tech']['verdict']}")
        print(f"  * TEMEL SKOR    (%35): {Fore.CYAN}{res['fund']['score']}/100{Style.RESET_ALL} | {res['fund']['verdict']}")
        print(f"  * TAKAS & AKIS  (%30): {Fore.CYAN}{res['takas']['score']}/100{Style.RESET_ALL} | {res['takas']['verdict']}")
        print(f"{Fore.CYAN}{'-' * 70}")

        # Temel Çarpan Özeti
        raw_fund = res["fund"].get("raw", {})
        f_pe = raw_fund.get("forward_pe") or raw_fund.get("trailing_pe")
        pb = raw_fund.get("price_to_book")
        roe = raw_fund.get("roe")
        roe_str = f"%{roe * 100:.1f}" if roe else "-"

        print(f"  Carpanlar : F/K: {f'{f_pe:.1f}' if f_pe else '-'} | PD/DD: {f'{pb:.2f}' if pb else '-'} | ROE: {roe_str}")
        print(f"  Para Akisi: CMF: {res['takas']['cmf']:+.2f} | MFI: {res['takas']['mfi']:.1f}")

        # Özel Uyarılar
        if res["alerts"]:
            print(f"\n  [!] OZEL TESPITLER & UYARILAR:")
            for a in res["alerts"]:
                print(f"   * {a}")
        print(f"{Fore.CYAN}{'=' * 70}\n")

    def screen_bist_360(self, tickers: Optional[List[str]] = None) -> pd.DataFrame:
        """Tüm BIST hisselerini 3 sütunlu puanlamaya göre tarar ve sıralar."""
        tickers = tickers or BIST_30_TICKERS
        total = len(tickers)
        rows = []

        print(f"\n🚀 BIST 360° Tarama Başlatılıyor ({total} Hisse: Teknik + Temel + Takas)...\n")

        for idx, ticker in enumerate(tickers, 1):
            print(f"[{idx}/{total}] {ticker} 360° taranıyor...", end="\r")
            try:
                res = self.analyze_single_stock(ticker)
                rows.append({
                    "Hisse": ticker.replace(".IS", ""),
                    "Toplam Skor": res["total_score"],
                    "Teknik (35)": f"{res['tech']['score']:.0f}",
                    "Temel (35)": f"{res['fund']['score']:.0f}",
                    "Takas (30)": f"{res['takas']['score']:.0f}",
                    "CMF Akış": f"{res['takas']['cmf']:+.2f}",
                    "MFI": f"{res['takas']['mfi']:.0f}",
                    "Genel Görünüm": res["final_verdict"].split("(")[0].strip()
                })
            except Exception as e:
                pass

        print("\n" + "=" * 85)
        df_res = pd.DataFrame(rows)
        if not df_res.empty:
            df_res.sort_values(by="Toplam Skor", ascending=False, inplace=True)
        return df_res

    def print_screener_table(self, df_res: pd.DataFrame):
        """Sonuçları renkli sıralı tablo olarak ekrana basar."""
        if df_res.empty:
            print("Sonuç bulunamadı.")
            return

        colored = []
        for _, row in df_res.iterrows():
            score = row["Toplam Skor"]
            if score >= 70:
                c = Fore.GREEN + Style.BRIGHT
            elif score >= 50:
                c = Fore.YELLOW
            else:
                c = Fore.RED

            colored.append([
                c + row["Hisse"],
                c + f"{score:.1f}" + Style.RESET_ALL,
                row["Teknik (35)"],
                row["Temel (35)"],
                row["Takas (30)"],
                row["CMF Akış"],
                row["MFI"],
                c + row["Genel Görünüm"] + Style.RESET_ALL
            ])

        headers = ["Hisse", "BIST 360 Skor", "Teknik (35)", "Temel (35)", "Takas (30)", "CMF Akış", "MFI", "Görünüm"]
        print(tabulate(colored, headers=headers, tablefmt="fancy_grid", stralign="center"))
