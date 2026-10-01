import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

from config import DESKTOP_NOTIFY_CONFIG, EMAIL_CONFIG

logger = logging.getLogger("Notifier")

def send_desktop_notification(title: str, message: str) -> bool:
    """Windows ekranına sesli Toast bildirimi fırlatır."""
    if not DESKTOP_NOTIFY_CONFIG.get("enabled", True):
        return False

    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="BIST 360 AI Broker",
            title=title,
            msg=message,
            duration="short"
        )
        if DESKTOP_NOTIFY_CONFIG.get("sound", True):
            toast.set_audio(audio.Default, loop=False)
        toast.show()
        return True
    except Exception as e:
        logger.warning(f"Masaüstü bildirimi gönderilemedi: {e}")
        return False

def send_email_notification(subject: str, html_body: str, text_body: str = None) -> bool:
    """Belirtilen e-posta adresine zengin HTML bülten gönderir."""
    cfg = EMAIL_CONFIG
    if not cfg.get("enabled", False):
        return False

    recipient = cfg.get("recipient_email", "gokhanelalyz@gmail.com")
    sender = cfg.get("sender_email", recipient)
    password = cfg.get("sender_password", "").strip()

    if not password:
        # Şifre henüz tanımlanmamışsa terminale açık bilgilendirme ver
        print("\n" + "="*70)
        print("⚠️  [GMAIL BİLDİRİMİ BİLGİSİ]")
        print(f"Alıcı: {recipient}")
        print("E-posta gönderimi için config.py içinde 'sender_password' tanımlanmalıdır.")
        print("Google 2 Adımlı Doğrulama açıkken 'Uygulama Şifresi' (16 haneli) kullanılır:")
        print("👉 myaccount.google.com/apppasswords adresinden 'Borsa Botu' için şifre alıp")
        print("   config.py -> EMAIL_CONFIG['sender_password'] alanına yapıştırabilirsiniz.")
        print("="*70 + "\n")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"BIST 360 AI Broker <{sender}>"
        msg["To"] = recipient

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server = smtplib.SMTP(cfg.get("smtp_server", "smtp.gmail.com"), cfg.get("smtp_port", 587), timeout=15)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        print(f"✅ E-posta başarıyla iletildi: {recipient} ({subject})")
        return True
    except Exception as e:
        print(f"❌ E-posta gönderim hatası: {e}")
        return False

def broadcast_signal_alert(ticker: str, signal_type: str, price: float, reason: str, score: float = 0.0):
    """Hem ekrana bildirim basar hem de e-posta kuyruğuna iletir."""
    title = f"🚨 BIST ALARM: {ticker} {signal_type}!"
    short_msg = f"{ticker} @ {price:.2f} TL | {reason} (Skor: {score:.1f})"
    
    # 1. Ekrana Windows Toast Bildirimi
    send_desktop_notification(title, short_msg)

    # 2. HTML E-Posta Şablonu
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
            <h2 style="color: #38bdf8; margin-top: 0;">🎯 BIST 360 Algoritmik Sinyal Uyarısı</h2>
            <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                <p style="font-size: 20px; font-weight: bold; margin: 0; color: #4ade80;">
                    {ticker} - {signal_type}
                </p>
                <p style="font-size: 16px; margin: 8px 0; color: #cbd5e1;">
                    <strong>Fiyat:</strong> {price:.2f} TL
                </p>
                <p style="font-size: 14px; margin: 4px 0; color: #94a3b8;">
                    <strong>Strateji / Gerekçe:</strong> {reason}
                </p>
                <p style="font-size: 14px; margin: 4px 0; color: #38bdf8;">
                    <strong>BIST 360 Skoru:</strong> {score:.1f} / 100
                </p>
            </div>
            <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">
                Bu bildirim BIST 360 AI Algoritmik İşlem ve Tarama Motoru tarafından otomatik üretilmiştir.
            </p>
        </div>
    </body>
    </html>
    """
    send_email_notification(f"[{signal_type}] {ticker} - BIST 360 Sinyal Uyarısı", html_content, short_msg)

def broadcast_pre_market_bulletin(report_df_rows, macro=None, balance_sheets=None):
    """Saat 09:30 bültenini hem ekrana hem de e-postaya iletir (Makro & Bilanço Destekli)."""
    title = "☀️ 09:30 BIST Seans Bülteni & Broker Raporu"
    top_tickers = [r.get("Hisse", "") for r in report_df_rows[:3]]
    msg = f"Gündem: {macro.get('regime', 'Piyasa')} | Pusu: {', '.join(top_tickers)} (%10 Kuralı)" if macro else f"Bugünün Pusu Hisseleri: {', '.join(top_tickers)}"

    # 1. Ekrana Sesli Bildirim
    send_desktop_notification(title, msg)

    # 2. Makro Bölümü HTML
    macro_html = ""
    if macro:
        m = macro.get("metrics", {})
        xu = m.get("XU100", {})
        usd = m.get("USDTRY", {})
        brent = m.get("BRENT", {})
        gold = m.get("ALTIN", {})

        macro_html = f"""
        <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 20px; border-left: 4px solid #38bdf8;">
            <h3 style="margin-top: 0; color: #38bdf8; font-size: 16px;">🌍 Broker Makro & Piyasa İklimi</h3>
            <p style="margin: 4px 0; font-size: 14px; color: #f8fafc;">
                <strong>Endeks Regimi:</strong> <span style="color: #4ade80;">{macro.get('regime')}</span>
            </p>
            <p style="margin: 6px 0; font-size: 13px; color: #cbd5e1;">
                <strong>Broker Görüşü:</strong> {macro.get('broker_verdict')}
            </p>
            <p style="margin: 6px 0; font-size: 13px; color: #94a3b8;">
                <strong>Sektörel Dinamik:</strong> {macro.get('sector_note')}
            </p>
            <div style="display: flex; gap: 10px; margin-top: 10px; font-size: 12px; color: #cbd5e1;">
                <span><strong>BIST 100:</strong> {xu.get('last', 0):,.0f} ({xu.get('change_pct', 0):+0.2f}%)</span> |
                <span><strong>Dolar/TL:</strong> {usd.get('last', 0):.2f} ({usd.get('change_pct', 0):+0.2f}%)</span> |
                <span><strong>Brent:</strong> ${brent.get('last', 0):.2f} ({brent.get('change_pct', 0):+0.2f}%)</span> |
                <span><strong>Ons Altın:</strong> ${gold.get('last', 0):,.0f}</span>
            </div>
        </div>
        """

    # 3. HTML Tablo Oluşturma
    table_rows_html = ""
    for r in report_df_rows:
        table_rows_html += f"""
        <tr style="border-bottom: 1px solid #334155; text-align: center;">
            <td style="padding: 10px; font-weight: bold; color: #38bdf8;">{r.get('Hisse', '')}</td>
            <td style="padding: 10px; color: #cbd5e1;">{r.get('Öncelik', '')}</td>
            <td style="padding: 10px; font-weight: bold; color: #f8fafc;">{r.get('Pusu Fiyatı', '')}</td>
            <td style="padding: 10px; color: #a7f3d0;">{r.get('Lot', '')}</td>
            <td style="padding: 10px; color: #fcd34d;">{r.get('Tutar (%10)', r.get('Tutar', ''))}</td>
            <td style="padding: 10px; color: #f87171; font-weight: bold;">{r.get('Zarar Kes (Stop)', '')}</td>
            <td style="padding: 10px; color: #4ade80; font-weight: bold;">{r.get('Hedef 1 (+%6-8)', '')}</td>
            <td style="padding: 10px; color: #34d399; font-weight: bold;">{r.get('Hedef 2 (+%15)', '')}</td>
            <td style="padding: 10px; color: #f59e0b; font-weight: bold;">{r.get('Çıkış', '⚡ Anında')}</td>
            <td style="padding: 10px; color: #93c5fd;">{r.get('360 Skor', '')}</td>
        </tr>
        """

    html_email = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
        <div style="max-width: 900px; margin: auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
            <h2 style="color: #38bdf8; margin-top: 0;">☀️ BIST 360 - Kıdemli Broker Seans Raporu</h2>
            <p style="color: #94a3b8; font-size: 14px;">
                Portföy: 100.000 TL | Maksimum %10 Kuralı (10.000 TL / Hisse) | Elit Likidite & Anında Çıkış
            </p>
            {macro_html}
            <h3 style="color: #f8fafc; font-size: 15px; margin-top: 20px;">🎯 Seçici A+ Pusu Seviyeleri (Zorlama Yok, En Fazla 1-2 Hisse):</h3>
            <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px;">
                <thead>
                    <tr style="background: #0f172a; color: #94a3b8; text-transform: uppercase;">
                        <th style="padding: 10px;">Hisse</th>
                        <th style="padding: 10px;">Öncelik</th>
                        <th style="padding: 10px;">Pusu Fiyatı</th>
                        <th style="padding: 10px;">Lot</th>
                        <th style="padding: 10px;">Tutar</th>
                        <th style="padding: 10px;">Stop-Loss</th>
                        <th style="padding: 10px;">Hedef 1</th>
                        <th style="padding: 10px;">Hedef 2</th>
                        <th style="padding: 10px;">Çıkış</th>
                        <th style="padding: 10px;">360 Skor</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
            <div style="margin-top: 20px; padding: 14px; background: #0f172a; border-radius: 8px; border-left: 4px solid #4ade80;">
                <p style="margin: 0; font-size: 13px; color: #cbd5e1;">
                    <strong>💡 Broker Prensibi:</strong> Sadece BIST'in en likit tahtalarında pusuya yatılır. Sat tuşuna basıldığında kademe kaybetmeden 1 saniyede nakde geçilir. Hedef 1'de %50 realize edilip stop başa başa çekilir.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    send_email_notification("☀️ BIST 360 - Günlük Broker & Makro Seans Raporu", html_email, msg)

def broadcast_news_tip(ticker: str, tip_type: str, keyword: str, headline: str, source: str):
    """Sıcak bir tüyo veya kritik KAP haberi yakalandığında anında ekrana ve e-postaya fırlatır."""
    title = f"📢 BIST TÜYO ALARMI: {ticker} ({keyword})"
    msg = f"{headline[:75]}... [{source}]"
    
    # 1. Ekrana Windows Toast Bildirimi
    send_desktop_notification(title, msg)
    
    # 2. HTML E-Posta Şablonu
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #1e293b; border-radius: 12px; padding: 24px; border: 1px solid #334155;">
            <h2 style="color: #38bdf8; margin-top: 0;">📢 BIST Sıcak Haber & Tüyo Bildirimi</h2>
            <div style="background: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 20px; border-left: 4px solid #f59e0b;">
                <p style="font-size: 18px; font-weight: bold; margin: 0; color: #f59e0b;">
                    {ticker} - {tip_type} ({keyword})
                </p>
                <p style="font-size: 15px; margin: 10px 0; color: #cbd5e1;">
                    {headline}
                </p>
                <p style="font-size: 12px; margin: 4px 0; color: #94a3b8;">
                    <strong>Kaynak:</strong> {source}
                </p>
            </div>
            <p style="font-size: 12px; color: #64748b; margin-bottom: 0;">
                Bu bildirim BIST 360 Haber ve Tüyo Radarı tarafından canlı taranarak iletilmiştir.
            </p>
        </div>
    </body>
    </html>
    """
    send_email_notification(f"📢 [{keyword}] {ticker} - BIST Sıcak Haber & Tüyo", html_email, msg)

def send_telegram_alert(message: str) -> bool:
    """Telegram yapılandırılmışsa mesaj iletir."""
    from config import TELEGRAM_CONFIG
    cfg = TELEGRAM_CONFIG
    if not cfg.get("enabled", False) or not cfg.get("bot_token") or not cfg.get("chat_id"):
        return False
    try:
        import requests
        url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        payload = {"chat_id": cfg["chat_id"], "text": message, "parse_mode": "Markdown"}
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def notify_signal(ticker: str, signal_type: str, price: float, reason: str, score: float = 0.0):
    """live_bot_daemon ve webhook_server ile uyumluluk fonksiyonu."""
    broadcast_signal_alert(ticker, signal_type, price, reason, score)

if __name__ == "__main__":
    print("Masaüstü bildirim testi yapılıyor...")
    send_desktop_notification("BIST 360 AI Broker", "Masaüstü bildirim testi başarılı! Ses ve görsel aktif.")
    print("Test tamamlandı.")
