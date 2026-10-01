"""
BIST Canlı Bot ve Webhook Arka Plan Servisi (Live Daemon)
1. TradingView Webhook dinleyicisini 8080 portunda canlı tutar.
2. BIST 30 hisselerini periyodik olarak tarayarak Sniper ve Momentum alım fırsatlarını izler.
3. Tespit edilen tüm sinyalleri anında günlüğe kaydeder ve alarmları tetikler.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import json
import threading
from pathlib import Path
from http.server import HTTPServer
from colorama import Fore, Style, init

from config import DATA_DIR, BIST_30_TICKERS
from data_loader import fetch_data
from strategies.bist_sniper import BISTSniperStrategy
from bist_360 import BIST360Analyzer
from notifier import notify_signal
from webhook_server import TradingViewWebhookHandler

init(autoreset=True)

# Öncelikli Takip Sepeti (En Yüksek BIST 360 Skorlu Hisseler)
PRIORITY_WATCHLIST = [
    "BIMAS.IS", "YKBNK.IS", "TOASO.IS", "AKBNK.IS", "GARAN.IS",
    "THYAO.IS", "ASELS.IS", "TUPRS.IS", "TCELL.IS", "KCHOL.IS"
]

LOG_FILE = DATA_DIR / "live_daemon.log"

def log_event(message: str):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {message}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def run_webhook_thread(port: int = 8080):
    """TradingView webhook sunucusunu arka planda çalıştırır."""
    server_address = ("", port)
    try:
        httpd = HTTPServer(server_address, TradingViewWebhookHandler)
        log_event(f"🌐 TradingView Webhook Sunucusu {port} portunda dinlemede...")
        httpd.serve_forever()
    except Exception as e:
        log_event(f"[HATA] Webhook sunucusu başlatılamadı: {e}")

def run_market_scanner_loop(interval_sec: int = 90):
    """Piyasa tarayıcısını periyodik olarak çalıştırır."""
    strat = BISTSniperStrategy()
    analyzer = BIST360Analyzer()
    seen_signals = set()

    log_event("🎯 BIST Piyasa Tarayıcısı devreye girdi. Öncelikli hisseler izleniyor...")

    while True:
        try:
            log_event("🔍 Piyasa kontrol ediliyor (Pusu listesi taranıyor)...")
            for ticker in PRIORITY_WATCHLIST:
                clean_t = ticker.replace(".IS", "")
                df = fetch_data(ticker, period="3mo", interval="1d", use_cache=False)
                if df.empty or len(df) < 30:
                    continue

                df = strat.generate_signals(df)
                last_row = df.iloc[-1]
                last_date = str(df.index[-1])[:10]
                sig = last_row.get("Signal", 0)

                if sig == 1:
                    sig_key = (clean_t, last_date, "AL")
                    if sig_key not in seen_signals:
                        seen_signals.add(sig_key)
                        close_p = last_row["Close"]
                        r360 = analyzer.analyze_single_stock(ticker)

                        # Alım Öncesi Haber & Tüyo Güvenlik Denetimi
                        try:
                            from sentiment_and_news_tracker import verify_stock_before_buy
                            v_check = verify_stock_before_buy(clean_t)
                            if not v_check["can_buy"]:
                                log_event(f"⛔ [FREN] {clean_t} teknik olarak AL verdi fakat haber radarı frenledi: {v_check['warning_note']}")
                                continue
                            
                            tip_note = ""
                            if v_check["hot_tips"]:
                                top_tip = v_check["hot_tips"][0]
                                tip_note = f" (🔥 Tüyo/Haber: {top_tip['keyword']})"
                        except Exception:
                            tip_note = ""

                        log_event(f"🔥 [AL SİNYALİ] {clean_t} @ {close_p:.2f} TL | BIST 360 Skor: {r360['total_score']:.1f}{tip_note}")
                        notify_signal(
                            ticker=clean_t,
                            signal_type="AL",
                            price=close_p,
                            reason=f"Sniper Dönüşü (BIST 360: {r360['total_score']:.0f}/100){tip_note}"
                        )

            time.sleep(interval_sec)
        except Exception as e:
            log_event(f"[UYARI] Tarama döngüsünde hata: {e}")
            time.sleep(10)

def main():
    log_event("=" * 60)
    log_event("🚀 BIST BROKER ARKA PLAN RADARI VE CANLI BOT BAŞLATILDI")
    log_event("=" * 60)

    # 1. Thread: TradingView Webhook Sunucusu (Port 8080)
    wh_thread = threading.Thread(target=run_webhook_thread, args=(8080,), daemon=True)
    wh_thread.start()

    # 2. Ana Döngü: Piyasa Tarayıcısı
    run_market_scanner_loop(interval_sec=90)

if __name__ == "__main__":
    main()
