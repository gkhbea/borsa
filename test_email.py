from notifier import send_email_notification, send_desktop_notification

print("1. Masaüstü bildirimi gönderiliyor...")
send_desktop_notification("BIST 360 AI Broker", "Gmail bağlantısı kuruldu! İlk test postası gönderiliyor.")

print("2. Test e-postası gönderiliyor...")
res = send_email_notification(
    subject="🚀 BIST 360 AI Broker - Canlı Bildirim Testi",
    html_body="""
    <div style="font-family: Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; border-radius: 12px;">
        <h2 style="color: #38bdf8;">✅ BIST 360 Bildirim Sistemi Başarıyla Bağlandı!</h2>
        <p>Merhaba Gökhan,</p>
        <p>Borsa İstanbul Algoritmik İşlem ve Analiz Botunun e-posta bildirim sistemi aktif edilmiştir.</p>
        <div style="background: #1e293b; padding: 16px; border-radius: 8px; border-left: 4px solid #4ade80;">
            <p style="margin: 0; font-weight: bold; color: #4ade80;">🎯 Aktif Özellikler:</p>
            <ul>
                <li>Her sabah saat <strong>09:30</strong> seans öncesi pusu ve lot dağılım bülteni</li>
                <li>Gün içi <strong>Sniper & Momentum</strong> AL sinyalleri</li>
                <li>Windows ekranına anlık sesli bildirim (Toast)</li>
            </ul>
        </div>
        <p style="color: #94a3b8; font-size: 12px; margin-top: 20px;">Antigravity AI BIST Engine • Disiplinli ve Kayıpsız İşlem Prensibi</p>
    </div>
    """,
    text_body="BIST 360 Bildirim Sistemi Aktif! Her sabah 09:30 bülteni ve sinyaller bu adrese iletilecek."
)
print("E-Posta Gönderim Sonucu:", res)
