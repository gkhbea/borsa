# 📈 BIST Algoritmik Al-Sat ve Ticaret Botu (Borsa İstanbul)

Borsa İstanbul (BIST 30 / BIST 100) hisseleri için özel olarak geliştirilmiş, teknik analiz indikatörleri, otomatik sinyal üretimi, risk yönetimi ve interaktif görselleştirme sunan profesyonel algoritmik ticaret ve backtest platformu.

---

## 🌟 Temel Özellikler

1. **Borsa İstanbul Entegrasyonu**:
   - `THYAO`, `GARAN`, `ASELS`, `TUPRS`, `EREGL`, `BIMAS` gibi tüm BIST hisselerini otomatik olarak `.IS` formatında çeker.
   - Hızlı testler için akıllı yerel önbellekleme (Caching).

2. **Dahili Stratejiler**:
   - **`supertrend`**: SuperTrend & EMA Ribbon Trend Takip Stratejisi (Trend piyasalarında en yüksek kârlılık).
   - **`rsi_bb`**: RSI + Bollinger Bantları ile Ortalama Dönüş / Dip Yakalama (Dalgalı piyasalar için).
   - **`macd_vol`**: MACD Kesişimi + Hacim Patlaması Onayı (Kurumsal giriş tespiti).
   - **`ensemble`**: Trend, Momentum, Hacim ve Volatiliteyi harmanlayan 5 puanlık Çoklu İndikatör Topluluk Stratejisi.

3. **Gelişmiş Risk Yönetimi & Backtest Motoru**:
   - Dinamik Stop-Loss (%3) ve Kâr Al (%6) emirleri.
   - **İz Süren Stop (Trailing Stop)**: Kârı korumak için fiyat yükseldikçe stop seviyesini otomatik yukarı çeker.
   - Gerçekçi komisyon hesaplaması (Binde 1 komisyon oranı) ve kayma payı (slippage).
   - Performans metrikleri: Toplam Getiri, Al & Tut (Benchmark) Getirisi, Kazanma Oranı (Win Rate %), Kâr Faktörü (Profit Factor), Maksimum Çekilme (Max Drawdown %), Sharpe Oranı.

4. **İnteraktif HTML Raporlama (Plotly)**:
   - Şamdan (Candlestick) grafikleri, hareketli ortalamalar, SuperTrend çizgisi.
   - Alım ve Satım noktalarının grafik üzerinde net oklarla gösterilmesi.
   - Portföy Değeri (TL) ile BIST hissesinin Al-Tut getirisinin zaman içindeki birebir kıyaslama eğrisi.

5. **BIST 30 Canlı Piyasa Tarayıcı (Screener)**:
   - Tek komutla tüm BIST 30 hisselerini tarar.
   - Anlık fiyat, günlük değişim %, RSI değeri, SuperTrend yönü, hacim artışı ve güncel AL/SAT durumunu renkli terminal tablosunda sunar.

6. **Telegram Alarm Entegrasyonu**:
   - Üretilen AL ve SAT sinyallerini anında Telegram kanalınıza veya telefonunuza bildirim olarak atabilir.

---

## 🌐 TradingView Canlı Entegrasyonu (Pine Script v5 & Webhook)

Sistem artık TradingView ile iki yönlü tam entegre çalışır:

1. **Hazır Pine Script v5 Kodu:** [`tradingview_strategy_v5.pine`](file:///C:/Users/g%C3%B6khan/.gemini/antigravity-ide/scratch/bist_algo_bot/tradingview_strategy_v5.pine)
   - 15m ve 1h grafiklerde yüksek serilik ve kâr potansiyeli için tasarlanmış, ADX rejim filtreli ve ATR Chandelier stoplu kurumsal strateji.
   - Grafik üzerinde şık bilgi tablosu ve al-sat okları üretir.

2. **Canlı Webhook Dinleyicisi (`webhook_server.py`):**
   - TradingView'de kurduğunuz alarmları mikro-saniyede yakalar.
   - Gelen her sinyal anında BIST 360 motorumuzdan (Temel + Takas) onay süzgecinden geçer ve Telegram'a net emir olarak düşer.

### TradingView Nasıl Kurulur? (3 Adım)
1. TradingView'de herhangi bir BIST hissesi (Örn: `THYAO`) açın. Alt paneldeki **Pine Editor** sekmesine tıklayın.
2. Projedeki [`tradingview_strategy_v5.pine`](file:///C:/Users/g%C3%B6khan/.gemini/antigravity-ide/scratch/bist_algo_bot/tradingview_strategy_v5.pine) kodunun tamamını yapıştırıp **"Grafiğe Ekle"** butonuna basın.
3. Grafikte stratejiye sağ tıklayıp **"Alarm Ekle"** deyin:
   - **Webhook URL:** `http://IP_ADRESINIZ:8080/webhook` (veya ngrok url)
   - Mesaj kısmına dokunmayın (kod otomatik olarak JSON formatında hazırlar).
4. Terminalde dinleyiciyi başlatın:
   ```powershell
   python main.py webhook --port 8080
   ```

### 2. Kullanım Seçenekleri

#### A. İnteraktif Menü (Tavsiye Edilen)
Hiçbir parametre girmeden sadece şu komutu çalıştırarak menü üzerinden seçim yapabilirsiniz:
```powershell
.\.venv\Scripts\python.exe main.py
```

#### B. Tek Bir Hisse İçin Backtest Çalıştırma
Örnek: Türk Hava Yolları (`THYAO`) üzerinde SuperTrend stratejisini 2 yıllık geçmiş veriyle test etmek için:
```powershell
.\.venv\Scripts\python.exe main.py backtest --ticker THYAO --strategy supertrend --period 2y
```
Test tamamlandığında hem terminalde detaylı özet rapor basılır hem de `reports/` klasöründe interaktif bir HTML grafik dosyası oluşturulur.

#### C. BIST 30 Canlı Piyasa Taraması (Screener)
Günün potansiyel al-sat fırsatlarını tüm BIST 30 hisselerinde taramak için:
```powershell
.\.venv\Scripts\python.exe main.py screen --strategy ensemble
```

#### D. Canlı Alarm Modunu Başlatma
```powershell
.\.venv\Scripts\python.exe main.py live --interval 60
```

---

## 📁 Proje Dosya Yapısı

```
bist_algo_bot/
│
├── config.py             # Hisse listeleri, komisyon, stop-loss ve genel ayarlar
├── data_loader.py        # Veri çekme ve yerel önbellek yönetimi
├── indicators.py         # RSI, MACD, SuperTrend, EMA, Bollinger, ATR hesaplamaları
├── backtester.py         # Gelişmiş backtest simülasyonu ve performans metrikleri
├── visualizer.py         # Plotly interaktif HTML raporlayıcı
├── screener.py           # BIST 30 hisse tarayıcısı
├── notifier.py           # Telegram ve konsol alarm servisi
├── main.py               # Ana komut satırı ve interaktif menü
├── requirements.txt      # Gerekli Python kütüphaneleri
│
├── strategies/           # Modüler Stratejiler Klasörü
│   ├── base.py           # Temel Strateji Arayüzü
│   ├── supertrend_ema.py # SuperTrend & EMA Trend Stratejisi
│   ├── rsi_bollinger.py  # RSI & Bollinger Bantları Ortalama Dönüş
│   ├── macd_volume.py    # MACD + Hacim Patlaması Stratejisi
│   └── ensemble.py       # Çoklu İndikatör Topluluk Stratejisi
│
├── data/                 # İndirilen verilerin önbellek alanı
└── reports/              # Üretilen HTML grafik raporları
```

---

## ⚙️ Özelleştirme ve Strateji Ekleme

Yeni bir al-sat stratejisi geliştirmek çok kolaydır:
1. `strategies/` klasörü altına `my_strategy.py` oluşturun.
2. `BaseStrategy` sınıfından türeterek `generate_signals(df)` metodunu yazın (`Signal=1` AL, `Signal=-1` SAT).
3. `strategies/__init__.py` içerisindeki sözlüğe kaydedin.
4. Hemen `python main.py backtest --strategy my_strategy` ile test edin!
