# 📈 BIST 360 - Kurumsal Algoritmik Ticaret & Otonom Portföy Sistemi

Borsa İstanbul (BIST) hisseleri için özel olarak geliştirilmiş; temel bilanço analizi, haber/KAP/tüyo dedektörü, asimetrik alfa algoritmaları, 437 hisselik canlı pazar tarayıcısı ve otonom portföy yönetim motorunu bir araya getiren profesyonel algoritmik ticaret platformu.

---

## 🌟 Öne Çıkan Kurumsal Yetenekler

### 1. 🛡️ 1 Haftalık Otonom Test & Kağıt İşlem Motoru (`paper_trader.py`)
* **5.000 TL Mikro-Portföy Kalibrasyonu**: Küçük sermayeleri korumak için tasarlanmış konsantre model.
* **Maksimum 2 Açık Pozisyon**: Pozisyon başına ~2.000 TL tahsis, 1.000 TL acil durum nakit tamponu.
* **Milisaniyelik Zarar Kes**: %3 Stop-Loss, %6 Hedef 1 (%50 Kâr Al & Stopu Başa Çek), Hedef 2 (Trend Sürüşü).
* **Şeffaf Günlük**: Her işlem, kâr/zarar ve nakit hareketi `data/paper_portfolio.json` üzerinde kayıtlıdır.

### 2. ⏰ Otomatik Raporlama Servisi (`live_bot_daemon.py`)
* **09:30 Sabah Seans Öncesi Bülteni**: Dolar, Altın, Brent petrol, makro piyasa yönü, KAP tüyoları ve günün A+ pusu listesi (E-posta + Windows Bildirimi).
* **10:00 - 18:00 Canlı Seans Radarı**: 90 saniyede bir tarama, TradingView 8080 Webhook dinleyicisi ve anlık alarm.
* **19:00 Günlük Kapanış Ekstresi**: *"Bugün ne kazandık / ne kaybettik"* net TL ve % dökümü, aktif pozisyon karnesi ve broker seans değerlendirmesi (E-posta + Windows Bildirimi).

### 3. 🔍 437 Hisselik Yüksek Hızlı Pazar Tarayıcısı (`bist_market_scanner.py`)
* TradingView kurumsal scanner motoru üzerinden tüm Borsa İstanbul'u **1.5 saniyede** tarar.
* Minimum 15 Milyon TL günlük hacim filtresi ile sığ hisseleri eler.
* Sonuçları iki kategoriye ayırır:
  1. **BIST 30 Lokomotifler** (Tek tuşla anında çıkılabilen A+ likit hisseler).
  2. **BIST Tüm Gizli Büyüme Hisseleri** (RSI dipte, EMA üzerinde hacim patlaması yapan yan tahtalar).

### 4. 📰 KAP, Haber & Tüyo Radarı (`sentiment_and_news_tracker.py`)
* Google News TR ve KAP bültenlerini anlık tarar.
* **Katalizörler**: İhale, Yeni İş İlişkisi, Pay Geri Alımı, Bedelsiz, Temettü.
* **Fren / Tehlike Filtresi**: Devre Kesici, VBTS Tedbiri, Ceza veya Soruşturma alan hisselerde teknik AL sinyali gelse dahi alımı durdurur (`verify_stock_before_buy`).

### 5. 🧠 Asimetrik Alpha Algoritmaları (`asymmetric_alpha_engine.py`)
* **🩸 Stop Hunt / Likidite Avı Tespiti**: Büyük fonların küçük yatırımcıyı stop ettirip hisseyi yukarı sürdüğü anı yakalar.
* **⏱️ Seans Zamanlama Muhafızı**: 10:00-10:25 açılış tuzaklarını engeller, 16:00-17:45 kurumsal kapanış dalgasını hedefler.
* **🎯 Sektörel Arbitraj (Lead-Lag)**: Sektör lideri hisseler (AKBNK, GARAN) fırladığında geride kalanları (YKBNK, ISCTR) tespit eder.
* **🪞 Sosyal Medya Ters İndikatörü (Anti-Hype)**: Herkesin konuştuğu tepe noktalarda alım yapmaz, sessizlikte pusuya yatar.

---

## 🚀 Hızlı Başlangıç

### 1. Kurulum
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy local_settings.py.example local_settings.py
```
*(local_settings.py içerisine Gmail Uygulama Şifrenizi tanımlayın)*

### 2. Canlı Otonom Botu Başlatma (7/24 Nöbet)
```powershell
.\.venv\Scripts\python.exe live_bot_daemon.py
```

### 3. Modülleri Manuel Çalıştırma
```powershell
# 19:00 Günlük Kapanış Raporunu Çalıştır:
.\.venv\Scripts\python.exe daily_closing_report.py

# 09:30 Sabah Seans Bültenini Çalıştır:
.\.venv\Scripts\python.exe pre_market_bulletin.py

# 437 Hisselik Tüm BIST Pazarını Tara:
.\.venv\Scripts\python.exe bist_market_scanner.py

# Portföy Durumunu Ekranda Gör:
.\.venv\Scripts\python.exe paper_trader.py
```

---

## 💻 İş Bilgisayarı Kurulumu
Detaylı iş bilgisayarı kurulum adımları için [WORK_PC_SETUP.md](file:///C:/Users/g%C3%B6khan/.gemini/antigravity-ide/scratch/bist_algo_bot/WORK_PC_SETUP.md) dosyasına bakabilirsiniz.

---

## 📁 Proje Dosya Mimarisi

```
bist_algo_bot/
│
├── config.py                     # Sermaye (5k TL), risk, bildirim ve e-posta ayarları
├── local_settings.py.example     # E-posta şifre şablonu (Gitignored)
├── live_bot_daemon.py            # 7/24 Arka plan canlı daemon & zamanlayıcı (09:30 & 19:00)
├── daily_closing_report.py       # 19:00 Günlük Kapanış Ekstresi & K/Z Raporlayıcı
├── pre_market_bulletin.py        # 09:30 Seans Öncesi Bülten & Pusu Listesi
├── paper_trader.py               # 1 Haftalık test sanal portföy ve ledger motoru
├── bist_market_scanner.py        # 437 Hisselik TradingView yüksek hızlı pazar tarayıcısı
├── sentiment_and_news_tracker.py # KAP, haber ve tüyo güvenlik radarı
├── asymmetric_alpha_engine.py    # Stop Hunt, Sektör Arbitrajı ve Zamanlama motoru
├── bist_360.py                   # 360 Derece Temel + Teknik analiz motoru
├── macro_and_earnings_tracker.py # Dolar, Altın, Brent petrol ve bilanço takibi
├── notifier.py                   # E-posta (HTML) ve Windows Toast bildirim servisi
├── data_loader.py                # Yahoo Finance veri çekici ve önbellek
├── requirements.txt              # Bağımlılıklar
├── WORK_PC_SETUP.md              # İş bilgisayarı hızlı başlangıç kılavuzu
│
├── data/                         # Portföy durumu (paper_portfolio.json) ve önbellek
└── reports/                      # Üretilen günlük bülten ve kapanış raporları
```
