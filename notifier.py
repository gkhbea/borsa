"""
Bildirim ve Alarm Servisi
Telegram Bot veya Konsol üzerinden alım-satım ve risk alarmlarını iletir.
"""
import requests
from config import TELEGRAM_CONFIG

def send_telegram_alert(message: str) -> bool:
    """Telegram üzerinden formatlanmış mesaj gönderir."""
    if not TELEGRAM_CONFIG.get("enabled"):
        return False

    token = TELEGRAM_CONFIG.get("bot_token")
    chat_id = TELEGRAM_CONFIG.get("chat_id")

    if not token or not chat_id:
        print("[UYARI] Telegram yapılandırması eksik (token veya chat_id boş).")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[HATA] Telegram mesajı iletilemedi: {e}")
        return False

def notify_signal(ticker: str, signal_type: str, price: float, reason: str):
    """Sinyal tespit edildiğinde terminale ve Telegram'a alarm gönderir."""
    icon = "🟢 AL (BUY)" if signal_type.upper() == "AL" else "🔴 SAT (SELL)"
    text = (
        f"🚨 *BIST ALGORİTMİK SİNYAL ALARMI*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Hisse:* `{ticker}`\n"
        f"⚡ *Sinyal:* *{icon}*\n"
        f"💰 *Son Fiyat:* `{price:.2f} TL`\n"
        f"📝 *Gerekçe:* {reason}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    print("\n" + text + "\n")
    send_telegram_alert(text)
