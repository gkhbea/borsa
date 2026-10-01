"""
BIST Algoritmik Bot - Yapılandırma ve Parametreler
"""
from pathlib import Path

# Temel Dizinler
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# BIST 30 Sembol Listesi (Yahoo Finance formatı: SEMBOL.IS)
BIST_30_TICKERS = [
    "AKBNK.IS", "ARCLK.IS", "ASELS.IS", "BIMAS.IS", "EKGYO.IS",
    "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS",
    "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KOZAL.IS", "KRDMD.IS",
    "MGROS.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS",
    "SASA.IS",  "SISE.IS",  "TCELL.IS", "THYAO.IS", "TOASO.IS",
    "TUPRS.IS", "VAKBN.IS", "VESTL.IS", "YKBNK.IS", "KONTR.IS"
]

# 🏆 ELİT A+ LİKİDİTE SEPETİ (Tek Tuşla Anında Çıkılabilen, En Güvenli Lokomotifler)
# Bu hisselerde günlük hacim milyarlarca TL'dir; 1 saniyede kademe kaybetmeden nakde dönülebilir.
ELITE_LIQUID_TICKERS = [
    "THYAO.IS", "TUPRS.IS", "BIMAS.IS", "AKBNK.IS",
    "GARAN.IS", "KCHOL.IS", "ISCTR.IS", "YKBNK.IS",
    "ASELS.IS", "SAHOL.IS"
]

# Seçici İşlem Modu: Sadece A+ kurulum varsa işlem öner, yoksa nakitte bekle
STRICT_A_PLUS_FILTER = True

# Varsayılan Test ve İşlem Sembolü
DEFAULT_TICKER = "THYAO.IS"

# 1 Haftalık Canlı Test ve Portföy Ayarları (5.000 TL Mikro-Portföy)
DEFAULT_INITIAL_CAPITAL = 5_000.0    # 5.000 TL başlangıç sermayesi (Kullanıcı Talebi)
POSITION_ALLOCATION_TL = 2_000.0     # Pozisyon başına maksimum tahsis (~2.000 TL)
MAX_OPEN_POSITIONS = 2               # Maksimum 2 açık hisse (Konsantre & Hızlı Çıkış)
MIN_CASH_RESERVE_TL = 1_000.0        # 1.000 TL nakit tamponu (Dipten maliyet/fırsat payı)
DEFAULT_COMMISSION_RATE = 0.001      # Binde 1 komisyon (0.1%)
DEFAULT_SLIPPAGE = 0.0005            # Kayma payı (0.05%)

# Risk Yönetimi Parametreleri
MAX_POSITION_SIZE_PCT = 0.40        # 5.000 TL'de %40 = 2.000 TL
DEFAULT_STOP_LOSS_PCT = 0.03        # %3 Stop-Loss
DEFAULT_TAKE_PROFIT_PCT = 0.06      # %6 Kâr Al (Risk-Ödül: 1:2)
DEFAULT_TRAILING_STOP_PCT = 0.025   # %2.5 İz süren stop

# Otomatik Raporlama Saatleri
DAILY_REPORT_TIME = "19:00"          # Günlük kapanış ve kâr/zarar ekstresi (Mail + Ekran)
MORNING_BULLETIN_TIME = "09:30"      # Seans öncesi bülten ve pusu listesi (Mail + Ekran)

# Veri Periyotları
# Desteklenen aralıklar (yfinance): '1d', '1h', '30m', '15m', '5m'
DEFAULT_INTERVAL = "1d"
DEFAULT_PERIOD = "2y"  # 2 yıllık geçmiş veri

# Canlı Alarm ve Bildirim Ayarları
DESKTOP_NOTIFY_CONFIG = {
    "enabled": True,             # Windows ekran bildirimi (Toast)
    "sound": True
}

try:
    from local_settings import EMAIL_PASSWORD
except ImportError:
    EMAIL_PASSWORD = ""

EMAIL_CONFIG = {
    "enabled": True,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "gokhanelalyz@gmail.com",
    "sender_password": EMAIL_PASSWORD,       # Gmail 16 haneli 'Uygulama Şifresi' (App Password)
    "recipient_email": "gokhanelalyz@gmail.com"
}

# İsteğe bağlı: Telegram Botu
TELEGRAM_CONFIG = {
    "enabled": False,
    "bot_token": "",      # @BotFather ile alınan Token
    "chat_id": ""         # Telegram Kullanıcı veya Kanal ID'si
}
