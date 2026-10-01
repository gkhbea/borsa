"""
BIST 360 - 19:00 Günlük Kapanış Ekstresi ve Kâr/Zarar Raporu
Her iş günü saat 19:00'da seans kapandıktan sonra:
1. Portföyün son durumunu ve gün içi fiyat hareketlerini günceller.
2. "Bugün ne kadar kazandık veya kaybettik" net rakamını (TL ve %) hesaplar.
3. Açık ve kapatılan pozisyonların tam dökümünü çıkarır.
4. E-posta (HTML) ve Windows ekran bildirimi (Toast) ile kullanıcıya iletir.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any

from config import REPORTS_DIR, EMAIL_CONFIG
from paper_trader import (
    load_portfolio,
    update_paper_positions,
    get_portfolio_summary_report,
    record_daily_snapshot
)
from notifier import send_email_notification, send_desktop_notification

def build_closing_html(rep: Dict[str, Any], macro_summary: str = "") -> str:
    """19:00 kapanış raporu için modern ve şık HTML e-posta şablonu üretir."""
    daily_pnl = rep["daily_pnl_tl"]
    daily_pct = rep["daily_pnl_pct"]
    total_eq = rep["total_equity"]
    init_cap = rep["initial_capital"]
    cash = rep["cash"]
    cash_pct = (cash / total_eq) * 100 if total_eq > 0 else 0
    total_ret = rep["total_return_pct"]

    # Durum rengi ve başlığı
    if daily_pnl > 0:
        badge_color = "#10b981"
        badge_text = f"🟢 BUGÜN KAZANDIK: +{daily_pnl:,.2f} TL (%{daily_pct:+.2f})"
        status_bg = "#ecfdf5"
        status_border = "#10b981"
    elif daily_pnl < 0:
        badge_color = "#ef4444"
        badge_text = f"🔴 BUGÜN KAYBETTİK: {daily_pnl:,.2f} TL (%{daily_pct:+.2f})"
        status_bg = "#fef2f2"
        status_border = "#ef4444"
    else:
        badge_color = "#6b7280"
        badge_text = f"⚪ BUGÜN YATAY: 0.00 TL (%0.00)"
        status_bg = "#f9fafb"
        status_border = "#d1d5db"

    # Açık Pozisyonlar Tablosu HTML
    open_rows_html = ""
    if rep["open_positions"]:
        for p in rep["open_positions"]:
            pnl_str = p["Kâr/Zarar"]
            p_color = "#10b981" if "+" in pnl_str else ("#ef4444" if "-" in pnl_str else "#374151")
            open_rows_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px 12px; font-weight: 700; color: #1e3a8a;">{p['Hisse']}</td>
                <td style="padding: 10px 12px; text-align: center;">{p['Lot']}</td>
                <td style="padding: 10px 12px; text-align: right;">{p['Maliyet']}</td>
                <td style="padding: 10px 12px; text-align: right; font-weight: 600;">{p['Son Fiyat']}</td>
                <td style="padding: 10px 12px; text-align: right;">{p['Piyasa Değeri']}</td>
                <td style="padding: 10px 12px; text-align: right; font-weight: 700; color: {p_color};">{pnl_str}</td>
                <td style="padding: 10px 12px; text-align: right; color: #dc2626;">{p['Stop-Loss']}</td>
                <td style="padding: 10px 12px; text-align: right; color: #16a34a;">{p['Hedef']}</td>
            </tr>
            """
    else:
        open_rows_html = """
        <tr>
            <td colspan="8" style="padding: 16px; text-align: center; color: #6b7280; font-style: italic;">
                Şu anda açık hisse pozisyonu bulunmuyor (Portföy %100 Nakitte bekliyor).
            </td>
        </tr>
        """

    # Bugün Kapatılan İşlemler Tablosu HTML
    closed_rows_html = ""
    if rep.get("closed_trades_today"):
        for ct in rep["closed_trades_today"]:
            pnl_c = "#10b981" if ct["pnl_tl"] > 0 else "#ef4444"
            closed_rows_html += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 8px 12px; font-weight: bold;">{ct['ticker']}</td>
                <td style="padding: 8px 12px; text-align: right;">{ct['entry_price']:.2f} TL</td>
                <td style="padding: 8px 12px; text-align: right;">{ct['exit_price']:.2f} TL</td>
                <td style="padding: 8px 12px; text-align: right; font-weight: 700; color: {pnl_c};">{ct['pnl_tl']:+,.2f} TL (%{ct['pnl_pct']:+.1f})</td>
                <td style="padding: 8px 12px; color: #4b5563;">{ct['exit_reason']}</td>
            </tr>
            """
    else:
        closed_rows_html = """
        <tr>
            <td colspan="5" style="padding: 10px 12px; text-align: center; color: #6b7280; font-size: 13px;">
                Bugün kapatılan veya stoplanan bir işlem olmadı.
            </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 20px; color: #111827; }}
            .card {{ background: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); max-width: 780px; margin: 0 auto; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 24px; text-align: left; }}
            .title {{ margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
            .subtitle {{ margin-top: 6px; font-size: 13px; color: #94a3b8; }}
            .content {{ padding: 24px; }}
            .status-banner {{ background: {status_bg}; border-left: 6px solid {status_border}; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px; }}
            .kpi-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 24px; }}
            .kpi-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; text-align: center; }}
            .kpi-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px; }}
            .kpi-val {{ font-size: 20px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            th {{ background: #f1f5f9; padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #475569; font-weight: 700; }}
            .section-title {{ font-size: 15px; font-weight: 700; color: #1e293b; margin-top: 24px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
            .broker-note {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px 18px; font-size: 13px; color: #1e40af; line-height: 1.5; margin-top: 24px; }}
            .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px; text-align: center; font-size: 11px; color: #94a3b8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <div class="title">🔔 BIST 360 - GÜNLÜK PORTFÖY EKSTRESİ</div>
                <div class="subtitle">1 Haftalık Otonom Test | Saat 19:00 Kapanış Değerlemesi | {rep['today_date']}</div>
            </div>
            <div class="content">
                <!-- Günlük Durum Rozeti -->
                <div class="status-banner">
                    <div style="font-size: 18px; font-weight: 800; color: {badge_color};">{badge_text}</div>
                    <div style="font-size: 12px; color: #4b5563; margin-top: 4px;">
                        Gün Başlangıcı: <b>{rep['day_start_equity']:,.2f} TL</b> &nbsp;|&nbsp; Gün Kapanışı: <b>{total_eq:,.2f} TL</b>
                    </div>
                </div>

                <!-- 4 Temel Metrik Kartı -->
                <div style="display: table; width: 100%; margin-bottom: 20px;">
                    <div style="display: table-row;">
                        <div style="display: table-cell; width: 50%; padding: 6px;">
                            <div class="kpi-box">
                                <div class="kpi-label">Toplam Portföy Büyüklüğü</div>
                                <div class="kpi-val">{total_eq:,.2f} TL</div>
                                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Başlangıç: {init_cap:,.0f} TL</div>
                            </div>
                        </div>
                        <div style="display: table-cell; width: 50%; padding: 6px;">
                            <div class="kpi-box">
                                <div class="kpi-label">1 Haftalık Toplam Net Getiri</div>
                                <div class="kpi-val" style="color: {'#10b981' if total_ret >= 0 else '#ef4444'};">%{total_ret:+.2f}</div>
                                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Toplam K/Z: {rep['total_equity'] - init_cap:+,.2f} TL</div>
                            </div>
                        </div>
                    </div>
                    <div style="display: table-row;">
                        <div style="display: table-cell; width: 50%; padding: 6px;">
                            <div class="kpi-box">
                                <div class="kpi-label">Kasadaki Boş Nakit</div>
                                <div class="kpi-val" style="color: #0369a1;">{cash:,.2f} TL</div>
                                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Nakit Oranı: %{cash_pct:.1f} (Güvence)</div>
                            </div>
                        </div>
                        <div style="display: table-cell; width: 50%; padding: 6px;">
                            <div class="kpi-box">
                                <div class="kpi-label">Hisse Varlığı (Piyasa Değeri)</div>
                                <div class="kpi-val">{rep['stock_value']:,.2f} TL</div>
                                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">{len(rep['open_positions'])} Aktif Pozisyon</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Açık Pozisyonlar Tablosu -->
                <div class="section-title">📌 AKTİF TAŞINAN HİSSELER VE SEVİYELER</div>
                <table style="margin-bottom: 20px;">
                    <thead>
                        <tr>
                            <th>Hisse</th>
                            <th style="text-align: center;">Lot</th>
                            <th style="text-align: right;">Alış</th>
                            <th style="text-align: right;">Kapanış</th>
                            <th style="text-align: right;">Piyasa Değeri</th>
                            <th style="text-align: right;">Net Kâr/Zarar</th>
                            <th style="text-align: right;">Stop-Loss</th>
                            <th style="text-align: right;">Kâr Al</th>
                        </tr>
                    </thead>
                    <tbody>
                        {open_rows_html}
                    </tbody>
                </table>

                <!-- Bugün Kapatılan İşlemler -->
                <div class="section-title">📋 BUGÜN GERÇEKLEŞEN ÇIKIŞLAR / STOPLAR</div>
                <table style="margin-bottom: 20px;">
                    <thead>
                        <tr>
                            <th>Hisse</th>
                            <th style="text-align: right;">Alış Fiyatı</th>
                            <th style="text-align: right;">Çıkış Fiyatı</th>
                            <th style="text-align: right;">Realize Kâr</th>
                            <th>İşlem Nedeni</th>
                        </tr>
                    </thead>
                    <tbody>
                        {closed_rows_html}
                    </tbody>
                </table>

                <!-- Kıdemli Broker Değerlendirmesi -->
                <div class="broker-note">
                    <b>🎯 Kıdemli BIST Portföy Yöneticisi Değerlendirmesi:</b><br>
                    • <b>Sermaye Disiplini:</b> 5.000 TL test bütçesi maksimum 2 açık pozisyon kuralıyla yönetilmektedir. Asla tüm para tek hisseye bağlanmaz.<br>
                    • <b>Zarar Kes Güvencesi:</b> Taşınan hisselerde stop-loss emirleri sistem tarafından milisaniyelik takip altındadır. Zarara tahammül edilmez.<br>
                    • <b>Yarınki Plan:</b> 09:30 seans öncesi bülteninde sabah piyasa yönü ve radarımıza giren A+ fırsatlar taranıp iletilecektir.
                </div>
            </div>
            <div class="footer">
                BIST 360 Algoritmik Trading Sistemi &copy; 2026 | Otomatik 19:00 Kapanış Servisi
            </div>
        </div>
    </body>
    </html>
    """
    return html

def run_daily_closing_report(send_mail: bool = True) -> Dict[str, Any]:
    """19:00 günlük kapanış raporunu üretir, kaydeder ve mail/toast olarak gönderir."""
    print("\n" + "="*80)
    print("🔔 BIST 360 - 19:00 GÜNLÜK KAPANIŞ EKSTRESİ OLUŞTURULUYOR")
    print("="*80)

    # 1. Açık pozisyonları son fiyatlarla güncelle (stop veya kâr al var mı?)
    events = update_paper_positions()
    if events:
        print(f"[BİLGİ] Gün kapanışı sırasında {len(events)} pozisyon olayı gerçekleşti.")

    # 2. Portföy özetini ve snapshot'ını al
    rep = record_daily_snapshot()
    today_str = rep["today_date"]

    daily_pnl = rep["daily_pnl_tl"]
    daily_pct = rep["daily_pnl_pct"]
    total_eq = rep["total_equity"]
    cash = rep["cash"]

    # 3. Konsol Çıktısı
    print(f"Tarih           : {today_str} | Saat: 19:00")
    print(f"Gün Başlangıcı  : {rep['day_start_equity']:,.2f} TL")
    print(f"Gün Kapanışı    : {total_eq:,.2f} TL")
    pnl_sign = "+" if daily_pnl > 0 else ""
    print(f"BUGÜNKÜ NET K/Z : {pnl_sign}{daily_pnl:,.2f} TL (%{daily_pct:+.2f})")
    print(f"Kasadaki Nakit  : {cash:,.2f} TL | Hisse Varlığı: {rep['stock_value']:,.2f} TL")
    print(f"Toplam Getiri   : %{rep['total_return_pct']:+.2f} (Başlangıç: {rep['initial_capital']:,.0f} TL)\n")

    # 4. Raporu Markdown Olarak Kaydet
    md_content = f"""# BIST 360 - 19:00 Günlük Kapanış Ekstresi ({today_str})

## 📊 Günlük Net Sonuç
- **Bugün Net Kâr/Zarar**: `{pnl_sign}{daily_pnl:,.2f} TL (%{daily_pct:+.2f})`
- **Portföy Gün Kapanış Değeri**: `{total_eq:,.2f} TL`
- **Portföy Gün Başlangıç Değeri**: `{rep['day_start_equity']:,.2f} TL`
- **Kasadaki Nakit**: `{cash:,.2f} TL`
- **Hisse Değeri**: `{rep['stock_value']:,.2f} TL`
- **1 Haftalık Toplam Getiri**: `%{rep['total_return_pct']:+.2f}` (Başlangıç: {rep['initial_capital']:,.0f} TL)

## 📌 Açık Pozisyonlar
"""
    if rep["open_positions"]:
        md_content += "| Hisse | Lot | Maliyet | Son Fiyat | Piyasa Değeri | Kâr/Zarar | Stop-Loss | Hedef |\n|---|---|---|---|---|---|---|---|\n"
        for p in rep["open_positions"]:
            md_content += f"| {p['Hisse']} | {p['Lot']} | {p['Maliyet']} | {p['Son Fiyat']} | {p['Piyasa Değeri']} | {p['Kâr/Zarar']} | {p['Stop-Loss']} | {p['Hedef']} |\n"
    else:
        md_content += "*Şu anda açık hisse pozisyonu bulunmuyor.*\n"

    report_path = REPORTS_DIR / f"closing_report_{today_str}.md"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"📁 Rapor kaydedildi: {report_path.name}")
    except Exception as e:
        print(f"[UYARI] Rapor kaydedilemedi: {e}")

    # 5. Windows Toast Bildirimi
    toast_title = f"🔔 BIST 19:00 Günlük Ekstre ({today_str})"
    toast_msg = f"Bugün Net: {pnl_sign}{daily_pnl:,.0f} TL (%{daily_pct:+.1f}) | Toplam: {total_eq:,.0f} TL | Nakit: {cash:,.0f} TL"
    send_desktop_notification(toast_title, toast_msg)

    # 6. E-posta Gönderimi
    if send_mail and EMAIL_CONFIG.get("enabled", True):
        subject = f"🔔 BIST 360 - 19:00 Kapanış Ekstresi: Bugün {pnl_sign}{daily_pnl:,.0f} TL ({daily_pct:+.2f}%)"
        html_body = build_closing_html(rep)
        plain_body = f"BIST 360 19:00 Kapanış Raporu ({today_str})\nBugün Net: {pnl_sign}{daily_pnl:,.2f} TL (%{daily_pct:+.2f})\nToplam Portföy: {total_eq:,.2f} TL\nKasadaki Nakit: {cash:,.2f} TL"
        mail_sent = send_email_notification(subject, html_body, plain_body)
        if mail_sent:
            print(f"📧 19:00 Kapanış Ekstresi e-postası başarıyla gönderildi -> {EMAIL_CONFIG.get('recipient_email')}")
        else:
            print("⚠️ E-posta gönderilemedi (Ayarları kontrol edin).")

    return rep

if __name__ == "__main__":
    run_daily_closing_report(send_mail=True)
