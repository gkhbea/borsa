"""
BIST Strateji Parametre Optimizatörü (Grid Search)
Geçmiş veri üzerinde farklı indikatör parametre kombinasyonlarını test ederek
en yüksek kâr ve kazanma oranına sahip ayarları tespit eder.
"""
from typing import Dict, Any, List
import itertools
import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style

from config import DEFAULT_INITIAL_CAPITAL
from data_loader import fetch_data, normalize_ticker
from backtester import Backtester
from strategies.supertrend_ema import SuperTrendEMAStrategy
from strategies.rsi_bollinger import RSIBollingerStrategy

def optimize_supertrend(ticker: str, period: str = "2y") -> pd.DataFrame:
    """SuperTrend + EMA stratejisi için en optimal parametreleri bulur."""
    ticker = normalize_ticker(ticker)
    df = fetch_data(ticker, period=period, interval="1d", use_cache=True)
    if df.empty:
        print(f"[HATA] {ticker} için veri bulunamadı.")
        return pd.DataFrame()

    # Test edilecek parametre uzayı
    st_periods = [7, 10, 14]
    st_multipliers = [2.0, 2.5, 3.0, 3.5]
    fast_emas = [9, 14, 21]
    slow_emas = [34, 50]

    combinations = list(itertools.product(st_periods, st_multipliers, fast_emas, slow_emas))
    results = []

    print(f"\n🔍 {ticker} için {len(combinations)} farklı parametre kombinasyonu test ediliyor...")

    for st_p, st_m, f_ema, s_ema in combinations:
        if f_ema >= s_ema:
            continue
        strategy = SuperTrendEMAStrategy(
            st_period=st_p,
            st_multiplier=st_m,
            fast_ema=f_ema,
            slow_ema=s_ema
        )
        bt = Backtester(strategy=strategy, initial_capital=DEFAULT_INITIAL_CAPITAL)
        res = bt.run(df, ticker=ticker)

        results.append({
            "ST Periyot": st_p,
            "ST Çarpan": st_m,
            "Hızlı EMA": f_ema,
            "Yavaş EMA": s_ema,
            "İşlem Sayısı": res.total_trades,
            "Kazanma %": f"%{res.win_rate_pct:.1f}",
            "Kâr Faktörü": f"{res.profit_factor:.2f}",
            "Max DD %": f"%{res.max_drawdown_pct:.1f}",
            "Net Getiri %": res.total_return_pct,
            "Net Getiri (Ham)": res.total_return_pct
        })

    df_res = pd.DataFrame(results)
    if df_res.empty:
        return df_res

    # Net getiriye göre sırala
    df_res.sort_values(by="Net Getiri (Ham)", ascending=False, inplace=True)
    df_res.drop(columns=["Net Getiri (Ham)"], inplace=True)
    
    top_5 = df_res.head(5)
    print(f"\n🏆 EN İYİ 5 PARAMETRE KOMBİNASYONU ({ticker}):")
    print(tabulate(top_5, headers="keys", tablefmt="fancy_grid", showindex=False))
    return df_res
