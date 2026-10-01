# 💻 İş Bilgisayarı Hızlı Kurulum ve Devam Rehberi (BIST 360)

Bu rehber, ev bilgisayarında geliştirdiğimiz ve GitHub'a yüklediğimiz BIST 360 otonom sistemini iş bilgisayarında **2 dakikada sıfır sorunla çalıştırmanızı** sağlar.

---

### 1. Repoyu İş Bilgisayarına Çekin

Terminali (PowerShell) açın ve projeyi kurmak istediğiniz dizinde çalıştırın:

```powershell
git clone https://github.com/gkhbea/borsa.git
cd borsa
```

*(Eğer repo zaten klonlanmışsa sadece son güncellemeleri çekin):*
```powershell
git pull origin main
```

---

### 2. Sanal Ortamı (Virtual Environment) Kurun

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

---

### 3. E-Posta Şifresini Tanımlayın (`local_settings.py`)

Şifreniz GitHub'a yüklenmez (`.gitignore` ile korunur). Hazır şablonu kopyalayıp dosyanızı oluşturun:

```powershell
copy local_settings.py.example local_settings.py
```

*(Dosya içeriğinde Google Uygulama Şifreniz zaten tanımlıdır):*
```python
EMAIL_PASSWORD = "jlaycnzuosloprtp"
```

---

### 4. Canlı Botu ve Otomatik Raporlayıcıyı Başlatın

Bot arka planda 7/24 çalışacak, sabah 09:30 bültenini ve akşam 19:00 kâr/zarar ekstresini mailinize otomatik atacaktır:

```powershell
.\.venv\Scripts\python.exe live_bot_daemon.py
```

---

### 5. Hızlı Manuel Test Komutları

Dilediğiniz an tek komutla çalıştırabileceğiniz modüller:

* **19:00 Günlük Kapanış Ekstresini Şimdi Gönder**:
  ```powershell
  .\.venv\Scripts\python.exe daily_closing_report.py
  ```
* **09:30 Sabah Seans Öncesi Bültenini Şimdi Gönder**:
  ```powershell
  .\.venv\Scripts\python.exe pre_market_bulletin.py
  ```
* **437 Hisselik Tüm BIST Pazarını 2 Saniyede Tara**:
  ```powershell
  .\.venv\Scripts\python.exe bist_market_scanner.py
  ```
* **Anlık Portföy Durumunu Ekranda Gör**:
  ```powershell
  .\.venv\Scripts\python.exe paper_trader.py
  ```
* **KAP Haber ve Tüyo Radarını Çalıştır**:
  ```powershell
  .\.venv\Scripts\python.exe sentiment_and_news_tracker.py
  ```

---

### 6. Sistem Mimarisi & Ayarlar Özeti

* **Test Bütçesi**: 5.000 TL
* **Pozisyon Tahsisi**: Maksimum 2 açık hisse (~2.000 TL x 2), 1.000 TL boş nakit tamponu
* **Stop-Loss**: %3 (Milisaniyelik zarar kes güvencesi)
* **Hedef 1**: %6 (%50 Kâr Al ve Stopu Başa Başa Çek)
* **Hedef 2**: Ana Trend Çıkışı (%100 Kapat)
* **Kayıt Dosyası**: `data/paper_portfolio.json`
