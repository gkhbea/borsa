"""
TradingView Webhook Dinleyici ve Canlı Köprü Sunucusu
TradingView alarmlarını POST /webhook üzerinden canlı olarak yakalar,
doğrular, Telegram'a iletir ve terminalde canlı kaydeder.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from colorama import Fore, Style, init

from config import DATA_DIR
from notifier import notify_signal, send_telegram_alert
from bist_360 import BIST360Analyzer

init(autoreset=True)

ALERTS_LOG_FILE = DATA_DIR / "tradingview_alerts.json"
WEBHOOK_PASSPHRASE = "BIST_SECRET_KEY_123"

def save_alert_to_history(alert_data: dict):
    """Gelen alarmı yerel geçmişe kaydeder."""
    history = []
    if ALERTS_LOG_FILE.exists():
        try:
            with open(ALERTS_LOG_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    
    alert_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    history.append(alert_data)
    
    # Son 500 alarmı sakla
    if len(history) > 500:
        history = history[-500:]

    try:
        with open(ALERTS_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[UYARI] Alarm dosyaya yazılamadı: {e}")

class TradingViewWebhookHandler(BaseHTTPRequestHandler):
    analyzer = BIST360Analyzer()

    def do_GET(self):
        """Sağlık kontrolü ve canlı mini dashboard."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "TradingView Webhook Bridge"}')
            return

        # Basit canlı kontrol sayfası
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BIST TradingView Webhook Canli Paneli</title>
            <style>
                body {{ background: #12151a; color: #fff; font-family: -apple-system, sans-serif; padding: 30px; }}
                .card {{ background: #1a1f29; padding: 20px; border-radius: 8px; border: 1px solid #2d3545; max-width: 600px; }}
                h2 {{ color: #00c076; margin-top: 0; }}
                .badge {{ background: #007aff; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>BIST TradingView Webhook Köprüsü Aktif</h2>
                <p>Sunucu TradingView alarmlarını dinliyor.</p>
                <p><b>Webhook Uç Noktası:</b> <code>POST /webhook</code></p>
                <p><b>Durum:</b> <span class="badge">DINLEMEDE (ONLINE)</span></p>
                <p><b>Sunucu Saati:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        """TradingView'den gelen alert webhook'unu yakalar."""
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(post_data)
        except Exception:
            # Düz metin geldiyse
            payload = {"raw_text": post_data}

        # Şifre kontrolü (güvenlik)
        received_pass = payload.get("passphrase")
        if received_pass and received_pass != WEBHOOK_PASSPHRASE:
            print(f"{Fore.RED}[GÜVENLİK UYARISI] Geçersiz Webhook Şifresi!")
            self.send_response(403)
            self.end_headers()
            return

        ticker = payload.get("ticker", "BIST_HISSE").upper()
        action = payload.get("action", "AL").upper()
        price = float(payload.get("price", 0.0))
        sl = payload.get("stop_loss", "-")
        tp = payload.get("take_profit", "-")

        # Terminale renkli bildirim bas
        action_color = Fore.GREEN if "AL" in action or "BUY" in action else Fore.RED
        print("\n" + "=" * 65)
        print(f"{Fore.YELLOW}{Style.BRIGHT}🔔 TRADINGVIEW CANLI ALARMI YAKALANDI!")
        print("=" * 65)
        print(f"  • Hisse Kodu    : {Fore.CYAN}{ticker}{Style.RESET_ALL}")
        print(f"  • Sinyal Yönü   : {action_color}{Style.BRIGHT}{action}{Style.RESET_ALL}")
        print(f"  • Tetik Fiyatı  : {price:.2f} TL")
        print(f"  • Stop-Loss     : {sl} TL")
        print(f"  • Take-Profit   : {tp} TL")
        print(f"  • Zaman         : {time.strftime('%H:%M:%S')}")
        print("=" * 65)

        # 360 Derece Hızlı Uyumluluk Kontrolü (Hisse Temel & Takas Uygun mu?)
        try:
            r360 = self.analyzer.analyze_single_stock(ticker)
            print(f"  📊 BIST 360 Skoru: {r360['total_score']}/100 ➔ {r360['final_verdict']}")
        except Exception:
            pass

        # Geçmişe kaydet
        save_alert_to_history(payload)

        # Telegram'a ilet
        telegram_msg = (
            f"🚨 *TRADINGVIEW ALARMI GELDİ!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *Hisse:* `{ticker}`\n"
            f"⚡ *İşlem:* *{action}*\n"
            f"💰 *Fiyat:* `{price:.2f} TL`\n"
            f"🛑 *Stop-Loss:* `{sl}`\n"
            f"🎯 *Hedef Kâr:* `{tp}`\n"
            f"⏰ *Zaman:* `{time.strftime('%H:%M:%S')}`\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        send_telegram_alert(telegram_msg)

        # TradingView'e başarılı yanıtı dön
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "success", "message": "Signal received and processed"}')

    def log_message(self, format, *args):
        # Varsayılan HTTP access loglarını gizle, sadece sinyalleri göster
        return

def start_webhook_server(port: int = 8080):
    """TradingView webhook dinleyicisini başlatır."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, TradingViewWebhookHandler)
    print(f"\n{Fore.GREEN}{Style.BRIGHT}==========================================================================")
    print(f"  🚀 TRADINGVIEW WEBHOOK KÖPRÜSÜ ÇALIŞIYOR (Port: {port})")
    print(f"==========================================================================")
    print(f"  • Webhook URL'niz : http://localhost:{port}/webhook")
    print(f"  • Şifreniz        : {WEBHOOK_PASSPHRASE}")
    print(f"  • Tarayıcı Paneli : http://localhost:{port}")
    print(f"  • Sinyaller       : Otomatik yakalanıp Telegram'a ve terminale iletilecek.")
    print(f"=========================================================================={Style.RESET_ALL}\n")
    print("Durdurmak için Ctrl+C tuşlarına basabilirsiniz...\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nWebhook sunucusu durduruldu.")
        httpd.server_close()

if __name__ == "__main__":
    start_webhook_server(8080)
