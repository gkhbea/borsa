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

# Varsayılan Test ve İşlem Sembolü
DEFAULT_TICKER = "THYAO.IS"

# Backtest ve Simülasyon Ayarları
DEFAULT_INITIAL_CAPITAL = 100_000.0  # 100.000 TL başlangıç sermayesi
DEFAULT_COMMISSION_RATE = 0.001      # Binde 1 komisyon (0.1%)
DEFAULT_SLIPPAGE = 0.0005            # Kayma payı (0.05%)

# Risk Yönetimi Parametreleri
MAX_POSITION_SIZE_PCT = 0.10        # Her hisseye maksimum %10 sermaye tahsisi (100k'da 10.000 TL)
DEFAULT_STOP_LOSS_PCT = 0.03        # %3 Stop-Loss
DEFAULT_TAKE_PROFIT_PCT = 0.06      # %6 Kâr Al (Risk-Ödül: 1:2)
DEFAULT_TRAILING_STOP_PCT = 0.025   # %2.5 İz süren stop

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
