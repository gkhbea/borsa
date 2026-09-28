import sys
import io

# Windows konsolunda UTF-8 karakter (Türkçe, emoji, kutu çizgileri) desteği
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import time
from pathlib import Path
from colorama import Fore, Style, init

from config import DEFAULT_TICKER, DEFAULT_INITIAL_CAPITAL, BIST_30_TICKERS, REPORTS_DIR
from data_loader import fetch_data, normalize_ticker
from backtester import Backtester
from visualizer import create_interactive_chart
from screener import BISTScreener
from strategies import AVAILABLE_STRATEGIES
from notifier import notify_signal

init(autoreset=True)

def print_banner():
    banner = f"""{Fore.CYAN}{Style.BRIGHT}
 ==========================================================================
          BIST ALGORITMIK AL-SAT & TICARET BOTU (Borsa Istanbul)          
               Teknik Analiz - Otomatik Sinyal - Backtest Motoru          
 =========================================================================={Style.RESET_ALL}
"""
    print(banner)

def run_backtest_flow(ticker: str, strategy_name: str, period: str, interval: str, capital: float, open_browser: bool = False):
    ticker = normalize_ticker(ticker)
    if strategy_name not in AVAILABLE_STRATEGIES:
        print(f"{Fore.RED}[HATA] Geçersiz strateji! Mevcut stratejiler: {list(AVAILABLE_STRATEGIES.keys())}")
        return

    strategy_cls = AVAILABLE_STRATEGIES[strategy_name]
    strategy = strategy_cls()

    print(f"\n{Fore.YELLOW}⏳ {ticker} için {period} verisi çekiliyor...")
    df = fetch_data(ticker, period=period, interval=interval, use_cache=True)
    if df.empty:
        print(f"{Fore.RED}[HATA] {ticker} için veri bulunamadı.")
        return

    print(f"{Fore.CYAN}⚙️  Backtest çalıştırılıyor: {strategy.name} (Sermaye: {capital:,.0f} TL)...")
    bt = Backtester(strategy=strategy, initial_capital=capital)
    result = bt.run(df, ticker=ticker)

    # Özet Kartı
    ret_color = Fore.GREEN if result.total_return_pct >= 0 else Fore.RED
    bh_color = Fore.GREEN if result.buy_hold_return_pct >= 0 else Fore.RED

    print("\n" + f"{Fore.CYAN}{'═' * 60}")
    print(f"{Fore.WHITE}{Style.BRIGHT}  📊 BACKTEST SONUÇLARI: {result.ticker} ({result.strategy_name})")
    print(f"{Fore.CYAN}{'═' * 60}")
    print(f"  • Başlangıç Sermayesi : {result.initial_capital:,.2f} TL")
    print(f"  • Bitiş Sermayesi     : {result.final_equity:,.2f} TL")
    print(f"  • Bot Toplam Getiri   : {ret_color}{Style.BRIGHT}%{result.total_return_pct:+,.2f}{Style.RESET_ALL}")
    print(f"  • Al ve Tut Getirisi  : {bh_color}%{result.buy_hold_return_pct:+,.2f}{Style.RESET_ALL} (BIST Benchmark)")
    print(f"  • Toplam İşlem Sayısı : {result.total_trades} (Kazanılan: {result.winning_trades} | Kaybedilen: {result.losing_trades})")
    print(f"  • Kazanma Oranı (Win%): {Fore.YELLOW}%{result.win_rate_pct:.1f}{Style.RESET_ALL}")
    print(f"  • Kâr Faktörü (P.F.)  : {Fore.YELLOW}{result.profit_factor:.2f}{Style.RESET_ALL}")
    print(f"  • Maksimum Çekilme    : {Fore.RED}-%{result.max_drawdown_pct:.2f}{Style.RESET_ALL} (Max Drawdown)")
    print(f"  • Sharpe Oranı        : {result.sharpe_ratio:.2f}")
    print(f"{Fore.CYAN}{'═' * 60}\n")

    # Son 5 İşlem Listesi
    if result.trades:
        print(f"{Fore.WHITE}{Style.BRIGHT}🔍 Son Gerçekleşen İşlemler:")
        for t in result.trades[-5:]:
            t_color = Fore.GREEN if t.pnl > 0 else Fore.RED
            print(f"  [{str(t.entry_date)[:10]}] Giriş: {t.entry_price:6.2f} TL ➔ [{str(t.exit_date)[:10]}] Çıkış: {t.exit_price:6.2f} TL | "
                  f"Getiri: {t_color}%{t.pnl_pct:+6.2f} ({t.pnl:+,.0f} TL){Style.RESET_ALL} | Sebep: {t.exit_reason}")
        print()

    # İnteraktif HTML Rapor Oluştur
    chart_path = create_interactive_chart(result)
    print(f"{Fore.GREEN}✅ İnteraktif Grafik Raporu Kaydedildi:")
    print(f"   📂 {chart_path.resolve()}\n")

def run_screener_flow(strategy_name: str = "ensemble"):
    strat_cls = AVAILABLE_STRATEGIES.get(strategy_name, AVAILABLE_STRATEGIES["ensemble"])
    screener = BISTScreener(tickers=BIST_30_TICKERS, strategy=strat_cls())
    df_res = screener.run_screen()
    screener.print_pretty_table(df_res)

def run_monitor_loop(strategy_name: str = "ensemble", check_interval_sec: int = 60):
    """Belirli aralıklarla piyasayı tarar ve yeni sinyal gelirse alarm gönderir."""
    print(f"{Fore.GREEN}📡 Canlı Sinyal Takip Modu Başlatıldı. ({check_interval_sec} sn aralıkla taranacak)...")
    strat_cls = AVAILABLE_STRATEGIES.get(strategy_name, AVAILABLE_STRATEGIES["ensemble"])
    strategy = strat_cls()

    seen_signals = {}  # {ticker: last_signal_date}

    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] Canlı veri kontrol ediliyor...")
            for ticker in BIST_30_TICKERS:
                try:
                    df = fetch_data(ticker, period="1mo", interval="1d", use_cache=False)
                    if df.empty or len(df) < 20:
                        continue
                    df = strategy.generate_signals(df)
                    last_row = df.iloc[-1]
                    last_date = str(df.index[-1])[:10]
                    signal = last_row.get("Signal", 0)

                    if signal in (1, -1):
                        key = (ticker, last_date, signal)
                        if key not in seen_signals:
                            seen_signals[key] = True
                            sig_type = "AL" if signal == 1 else "SAT"
                            notify_signal(
                                ticker=ticker,
                                signal_type=sig_type,
                                price=last_row["Close"],
                                reason=last_row.get("Reason", "Strateji Sinyali")
                            )
                except Exception as e:
                    pass
            time.sleep(check_interval_sec)
    except KeyboardInterrupt:
        print("\nCanlı takip durduruldu.")

from optimizer import optimize_supertrend
from bist_360 import BIST360Analyzer
from momentum_analyzer import BISTMomentumRadar
from webhook_server import start_webhook_server

def interactive_menu():
    print_banner()
    analyzer360 = BIST360Analyzer()
    radar = BISTMomentumRadar()
    while True:
        print(f"{Fore.WHITE}{Style.BRIGHT}Lutfen Yapmak Istediginiz Islemi Secin:")
        print(f"  [1] 📊 Tek Hisse Icin Backtest Calistir (Alpha, Momentum, SuperTrend, RSI)")
        print(f"  [2] 🚀 BIST 30 Hizli Teknik Tarayici (Screener)")
        print(f"  [3] ⚡ BIST Momentum Radari (En Hizli Yukselenler & Zirve Kirilimlari)")
        print(f"  [4] 🌟 BIST 360° TEKNIK + TEMEL + TAKAS Analizi (Tek Hisse)")
        print(f"  [5] 🏆 BIST 360° Tum BIST 30 Siralamasi (Teknik, Temel, Takas Tarayici)")
        print(f"  [6] 📈 Farkli Stratejileri Karsilastir (Alpha vs Momentum vs SuperTrend)")
        print(f"  [7] 🎯 Strateji Parametre Optimizasyonu (Grid Search / En Iyi Ayarlar)")
        print(f"  [8] 📡 Canli Alarm ve Takip Modunu Baslat")
        print(f"  [9] 🌐 TRADINGVIEW WEBHOOK KOPRUSUNU BASLAT (Canli TV Dinleyici)")
        print(f"  [10] 📜 TRADINGVIEW PINE SCRIPT v5 KODUNU GORUNTULE / KOPYALA")
        print(f"  [0] Cikis")
        
        choice = input(f"\n{Fore.YELLOW}Seciminiz [0-10]: {Style.RESET_ALL}").strip()
        
        if choice == "1":
            ticker = input(f"Hisse Kodu (Varsayilan {DEFAULT_TICKER}): ").strip() or DEFAULT_TICKER
            print("\nMevcut Stratejiler:")
            for k in AVAILABLE_STRATEGIES:
                print(f"  - {k}")
            strat = input("Strateji Secimi (Varsayilan alpha): ").strip() or "alpha"
            period = input("Zaman Araligi (1y, 2y, 5y) [Varsayilan 2y]: ").strip() or "2y"
            run_backtest_flow(ticker=ticker, strategy_name=strat, period=period, interval="1d", capital=DEFAULT_INITIAL_CAPITAL)
        elif choice == "2":
            strat = input("Kullanilacak Strateji (alpha / momentum / supertrend / ensemble) [Varsayilan: alpha]: ").strip() or "alpha"
            run_screener_flow(strategy_name=strat)
        elif choice == "3":
            df_mom = radar.scan_momentum_leaders()
            radar.print_radar_table(df_mom)
        elif choice == "4":
            ticker = input(f"Analiz Edilecek Hisse (Varsayilan {DEFAULT_TICKER}): ").strip() or DEFAULT_TICKER
            res = analyzer360.analyze_single_stock(ticker)
            analyzer360.print_report(res)
        elif choice == "5":
            df_360 = analyzer360.screen_bist_360()
            analyzer360.print_screener_table(df_360)
        elif choice == "6":
            ticker = input(f"Karsilastirilacak Hisse (Varsayilan {DEFAULT_TICKER}): ").strip() or DEFAULT_TICKER
            print(f"\n{Fore.CYAN}=== {ticker} ICIN TUM STRATEJILER KARSILASTIRILIYOR ===")
            for st_name in AVAILABLE_STRATEGIES:
                run_backtest_flow(ticker=ticker, strategy_name=st_name, period="2y", interval="1d", capital=DEFAULT_INITIAL_CAPITAL)
        elif choice == "7":
            ticker = input(f"Optimize Edilecek Hisse (Varsayilan {DEFAULT_TICKER}): ").strip() or DEFAULT_TICKER
            optimize_supertrend(ticker=ticker)
        elif choice == "8":
            interval_sec = input("Tarama Araligi (Saniye) [Varsayilan: 60]: ").strip() or "60"
            run_monitor_loop(strategy_name="ensemble", check_interval_sec=int(interval_sec))
        elif choice == "9":
            port = input("Calisacak Port [Varsayilan 8080]: ").strip() or "8080"
            start_webhook_server(int(port))
        elif choice == "10":
            pine_file = Path(__file__).resolve().parent / "tradingview_strategy_v5.pine"
            print(f"\n{Fore.GREEN}==========================================================================")
            print(f"  TRADINGVIEW PINE SCRIPT v5 KODU (tradingview_strategy_v5.pine)")
            print(f"=========================================================================={Style.RESET_ALL}")
            print(f"Dosya Yolu: {pine_file}\n")
            print("Bu kodu TradingView'de alt paneldeki 'Pine Editor' kismina yapistirip 'Grafiğe Ekle' butonuna basiniz.")
            print("Alarm kurarken Webhook URL'si olarak 'http://IP_ADRESINIZ:8080/webhook' belirtiniz.\n")
        elif choice == "0":
            print("Iyi gunler!")
            break
        else:
            print(f"{Fore.RED}Gecersiz secim, lutfen tekrar deneyin.")

def main():
    parser = argparse.ArgumentParser(description="BIST Algoritmik Al-Sat ve Bot Sistemi")
    subparsers = parser.add_subparsers(dest="command")

    # Backtest komutu
    bt_parser = subparsers.add_parser("backtest", help="Gecmis veri uzerinde strateji testi yapar.")
    bt_parser.add_argument("--ticker", "-t", default=DEFAULT_TICKER, help="BIST hisse kodu (orn: THYAO)")
    bt_parser.add_argument("--strategy", "-s", default="alpha", choices=list(AVAILABLE_STRATEGIES.keys()), help="Kullanilacak strateji")
    bt_parser.add_argument("--period", "-p", default="2y", help="Gecmis veri suresi (orn: 1y, 2y, 5y)")
    bt_parser.add_argument("--interval", "-i", default="1d", help="Bar araligi (orn: 1d, 1h)")
    bt_parser.add_argument("--capital", "-c", type=float, default=DEFAULT_INITIAL_CAPITAL, help="Baslangic sermayesi (TL)")

    # Screener komutu
    screen_parser = subparsers.add_parser("screen", help="BIST 30 hisselerini anlik olarak tarar.")
    screen_parser.add_argument("--strategy", "-s", default="alpha", choices=list(AVAILABLE_STRATEGIES.keys()), help="Kullanilacak strateji")

    # BIST 360 Tekil Analiz komutu
    a360_parser = subparsers.add_parser("analyze360", help="Teknik + Temel + Takas hibrit 360 derece hisse analizi yapar.")
    a360_parser.add_argument("--ticker", "-t", default=DEFAULT_TICKER, help="BIST hisse kodu (orn: GARAN)")

    # BIST 360 Tarama komutu
    s360_parser = subparsers.add_parser("screen360", help="BIST 30 hisselerini Teknik, Temel ve Takas puanlarina gore tarar.")

    # Momentum Radar komutu
    mom_parser = subparsers.add_parser("momentum", help="BIST 30 hisselerini Momentum ve Zirve Kirilimlarina gore tarar.")

    # Webhook Sunucusu komutu
    webhook_parser = subparsers.add_parser("webhook", help="TradingView Webhook dinleyici sunucusunu baslatir.")
    webhook_parser.add_argument("--port", type=int, default=8080, help="Sunucu portu (varsayilan: 8080)")

    # Optimize komutu
    opt_parser = subparsers.add_parser("optimize", help="Strateji parametre optimizasyonu yapar.")
    opt_parser.add_argument("--ticker", "-t", default=DEFAULT_TICKER, help="BIST hisse kodu (orn: THYAO)")
    opt_parser.add_argument("--period", "-p", default="2y", help="Gecmis veri suresi")

    # Canli takip komutu
    live_parser = subparsers.add_parser("live", help="Canli al/sat sinyal takipcisi")
    live_parser.add_argument("--strategy", "-s", default="alpha", choices=list(AVAILABLE_STRATEGIES.keys()))
    live_parser.add_argument("--interval", type=int, default=60, help="Kontrol sikligi (saniye)")

    args = parser.parse_args()

    if args.command == "backtest":
        print_banner()
        run_backtest_flow(
            ticker=args.ticker,
            strategy_name=args.strategy,
            period=args.period,
            interval=args.interval,
            capital=args.capital
        )
    elif args.command == "screen":
        print_banner()
        run_screener_flow(strategy_name=args.strategy)
    elif args.command == "momentum":
        print_banner()
        r = BISTMomentumRadar()
        df_mom = r.scan_momentum_leaders()
        r.print_radar_table(df_mom)
    elif args.command == "analyze360":
        print_banner()
        a = BIST360Analyzer()
        res = a.analyze_single_stock(args.ticker)
        a.print_report(res)
    elif args.command == "screen360":
        print_banner()
        a = BIST360Analyzer()
        df_360 = a.screen_bist_360()
        a.print_screener_table(df_360)
    elif args.command == "webhook":
        print_banner()
        start_webhook_server(args.port)
    elif args.command == "optimize":
        print_banner()
        optimize_supertrend(ticker=args.ticker, period=args.period)
    elif args.command == "live":
        print_banner()
        run_monitor_loop(strategy_name=args.strategy, check_interval_sec=args.interval)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
