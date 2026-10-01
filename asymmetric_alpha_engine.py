"""
BIST 360 - Asimetrik Üstünlük ve Akıllı Para Motoru (Asymmetric Alpha Engine)
Piyasadaki %95'lik perakende yatırımcının ve sıradan botların göremediği 4 kurumsal sırrı yönetir:

1. 🩸 Stop Avı Dedektörü (Liquidity Sweep / False Breakdown):
   - Fiyat desteği kırıp amatörleri stop ettikten hemen sonra Akıllı Para (CMF) ile içeri dönüşü yakalar.
2. ⏱️ Seans Mikro-Yapı & Saat Kalkanı (Session Timing Guard):
   - 10:00-10:25 açılış tuzaklarını engeller, 16:00-17:40 kurumsal para giriş saatlerini değerlendirir.
3. 🎯 Sektörel Lider-Takipçi (Lead-Lag) Radarı:
   - Sektör lideri (örn. GARAN/AKBNK) koştuğunda arkadan gelecek artçı hisseyi (YKBNK/ISCTR) henüz kalkmadan yakalar.
4. 🪞 Anti-Hype & Sosyal Medya Ters İndikatörü:
   - Aşırı konuşulan, Twitter'da pompalanan hisseleri mal boşaltma riskiyle engeller; sessizce toplananlara oturur.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import datetime
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from data_loader import fetch_data
from takas_analyzer import calculate_chaikin_money_flow
from indicators import add_rsi

# Sektörel Lider - Takipçi Eşleşmeleri
SECTOR_PAIRS = {
    "BANKACILIK": {
        "leaders": ["AKBNK.IS", "GARAN.IS"],
        "followers": ["YKBNK.IS", "ISCTR.IS", "VAKBN.IS"]
    },
    "HOLDING": {
        "leaders": ["KCHOL.IS"],
        "followers": ["SAHOL.IS"]
    },
    "HAVACILIK_SANAYI": {
        "leaders": ["THYAO.IS"],
        "followers": ["PGSUS.IS", "TUPRS.IS"]
    }
}

def detect_liquidity_sweep(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Stop Avı (Liquidity Sweep) Tespiti:
    Son 20 günün en düşüğü kırılmış gibi yapılıp panikle satanların malı toplanmış mı?
    Eğer kırılım barında veya hemen ertesi gün fiyat tekrar desteğin üzerine çıkıyor
    ve CMF pozitif kalıyorsa bu kusursuz bir 'Stop Avı' alım fırsatıdır.
    """
    if df.empty or len(df) < 25:
        return {"sweep_detected": False, "confidence": 0, "desc": "Yetersiz veri"}

    df = df.copy()
    if "CMF" not in df.columns:
        df["CMF"] = calculate_chaikin_money_flow(df, period=20)

    # Son 20 günlük en düşük seviye (önceki barlar)
    recent = df.iloc[-25:]
    lowest_20 = recent["Low"].iloc[:-2].min()
    
    prev_bar = recent.iloc[-2]
    last_bar = recent.iloc[-1]

    cmf_val = last_bar.get("CMF", 0.0)

    # 1. Senaryo: Önceki bar 20G dip seviyesinin altına sarktı (stoplar patlatıldı)
    # 2. Senaryo: Son bar hızla toparlayıp desteğin üzerinde kapattı (False Breakdown)
    dipped_below = prev_bar["Low"] < lowest_20 or last_bar["Low"] < lowest_20
    recovered_above = last_bar["Close"] > lowest_20
    smart_money_inflow = cmf_val > 0.02  # Hacimsel para girişi var

    is_sweep = dipped_below and recovered_above and smart_money_inflow

    if is_sweep:
        return {
            "sweep_detected": True,
            "confidence": 92,
            "type": "🩸 BOĞA STOP AVI (LIQUIDITY SWEEP)",
            "desc": f"20 günlük dip ({lowest_20:.2f} TL) delinip amatör stopları patlatıldı, ardından CMF ({cmf_val:+.2f}) desteğiyle tahta toplandı!",
            "lowest_level": round(lowest_20, 2)
        }
    
    return {"sweep_detected": False, "confidence": 0, "desc": "Normal fiyat hareketi"}

def get_session_microstructure_guard() -> Dict[str, Any]:
    """
    BIST Seans İçi Saat ve Mikro-Yapı Kalkanı:
    Seansın hangi aşamasında olduğumuzu ve o saat diliminin risk karakterini belirler.
    """
    now = datetime.datetime.now()
    curr_time = now.time()

    t_open_trap_start = datetime.time(10, 0)
    t_open_trap_end = datetime.time(10, 25)

    t_midday_start = datetime.time(12, 30)
    t_midday_end = datetime.time(14, 0)

    t_golden_start = datetime.time(16, 0)
    t_golden_end = datetime.time(17, 45)

    if t_open_trap_start <= curr_time <= t_open_trap_end:
        return {
            "session_zone": "⚠️ AÇILIŞ TUZAK BÖLGESİ (10:00 - 10:25)",
            "safe_to_enter": False,
            "rule": "Piyasa emriyle yukarıdan alım YASAK. Sadece önceden girilmiş derin pusu emirleri geçerlidir.",
            "mode": "FREN_MODU"
        }
    elif t_midday_start <= curr_time <= t_midday_end:
        return {
            "session_zone": "🟡 ÖĞLE TESTERE BÖLGESİ (12:30 - 14:00)",
            "safe_to_enter": True,
            "rule": "Hacim düşüktür; yatay bant hareketlerinde acele edilmez, tuzak kırılımlara dikkat edilir.",
            "mode": "SABIR_MODU"
        }
    elif t_golden_start <= curr_time <= t_golden_end:
        return {
            "session_zone": "🟢 ALTIN KURUMSAL SAAT (16:00 - 17:45)",
            "safe_to_enter": True,
            "rule": "Londra ve BofA kapanış akışları devrede. Teyitli trend hareketlerinde en güvenilir işlem saatidir.",
            "mode": "GÜVENLİ_İŞLEM_MODU"
        }
    else:
        return {
            "session_zone": "📊 OLAĞAN SEANS AKIŞI",
            "safe_to_enter": True,
            "rule": "Sistem parametreleri standart pusu ve disiplin kurallarıyla devrede.",
            "mode": "STANDART_MOD"
        }

def scan_sector_lead_lag() -> List[Dict[str, Any]]:
    """
    Sektörel Lider - Takipçi Arbitrajı Taraması:
    Lider hisse güçlü yükselirken arkasından henüz kalkmamış artçı hisseleri yakalar.
    """
    arbitrage_opportunities = []

    for sector_name, group in SECTOR_PAIRS.items():
        leader_changes = []
        for l_tick in group["leaders"]:
            df_l = fetch_data(l_tick, period="5d", interval="1d", use_cache=True)
            if not df_l.empty and len(df_l) >= 2:
                pct = ((df_l["Close"].iloc[-1] / df_l["Close"].iloc[-2]) - 1) * 100
                leader_changes.append(pct)

        if not leader_changes:
            continue

        avg_leader_perf = np.mean(leader_changes)

        # Eğer liderler %1.5'in üzerinde güçlü yükselişteyse takipçileri kontrol et
        if avg_leader_perf >= 1.5:
            for f_tick in group["followers"]:
                df_f = fetch_data(f_tick, period="5d", interval="1d", use_cache=True)
                if not df_f.empty and len(df_f) >= 2:
                    f_pct = ((df_f["Close"].iloc[-1] / df_f["Close"].iloc[-2]) - 1) * 100
                    lag_gap = avg_leader_perf - f_pct

                    # Eğer takipçi geride kalmışsa (en az %1.0 fark) bu bir artçı alım fırsatıdır
                    if lag_gap >= 1.0:
                        arbitrage_opportunities.append({
                            "sector": sector_name,
                            "leader": group["leaders"][0].replace(".IS", ""),
                            "leader_perf": f"%{avg_leader_perf:+.2f}",
                            "follower": f_tick.replace(".IS", ""),
                            "follower_perf": f"%{f_pct:+.2f}",
                            "lag_gap": f"%{lag_gap:+.2f}",
                            "verdict": f"🚀 GECİKMELİ YAKALAMA (Lider koptu, {f_tick.replace('.IS', '')} henüz kalkmadı!)"
                        })

    return arbitrage_opportunities

def evaluate_anti_hype_filter(ticker: str, sentiment_score: int, rsi_val: float) -> Dict[str, Any]:
    """
    Anti-Hype (Sosyal Medya Ters İndikatörü):
    Herkes hisseyi konuşup sosyal medyada tavan yaparken tahta yapıcının mal boşaltmasını engeller.
    """
    clean_t = ticker.replace(".IS", "")

    # Eğer hem sosyal medya skoru aşırı pozitif (+80 üstü) hem de RSI aşırı alım bölgesindeyse (> 70)
    if sentiment_score >= 80 and rsi_val >= 70:
        return {
            "status": "🚨 HYPE TUZAĞI (MAL BOŞALTMA RİSKİ)",
            "allow_trade": False,
            "reason": f"{clean_t} sosyal medyada aşırı coşku (Skor: {sentiment_score}) ve teknik şişme (RSI: {rsi_val:.1f}) içinde. Küçük yatırımcıya dağıtım riski yüksek!",
            "badge": "🛑 DİKKAT: COŞKU TEPE TUZAĞI"
        }
    # Eğer sosyal medya sakin/nötr ama hissede kurumsal para akışı varsa
    elif sentiment_score <= 30 and rsi_val <= 48:
        return {
            "status": "💎 SESSİZ KURUMSAL TOPLAMA",
            "allow_trade": True,
            "reason": f"{clean_t} radar altında, sosyal medyada kimse konuşmuyor ama dipte akıllı para toplanıyor.",
            "badge": "💎 SESSİZ CEVHER"
        }
    else:
        return {
            "status": "🟢 DENGELİ",
            "allow_trade": True,
            "reason": "Duygu ve teknik dengeli seviyede.",
            "badge": "🟢 DENGELİ"
        }

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧠 BIST 360 ASİMETRİK ÜSTÜNLÜK MOTORU (TEST VE İSTİHBARAT)")
    print("="*80)

    # 1. Seans Kalkanı
    guard = get_session_microstructure_guard()
    print(f"\n⏱️  SEANS DİLİMİ: {guard['session_zone']}")
    print(f"   Kural : {guard['rule']}")

    # 2. Sektörel Arbitraj Taraması
    print("\n🎯 SEKTÖREL LİDER - TAKİPÇİ (LEAD-LAG) ANALİZİ:")
    lags = scan_sector_lead_lag()
    if lags:
        for item in lags:
            print(f"   • [{item['sector']}] Lider {item['leader']} ({item['leader_perf']}) -> Takipçi {item['follower']} ({item['follower_perf']}) | Fark: {item['lag_gap']}")
            print(f"     👉 {item['verdict']}")
    else:
        print("   • Şu an sektör liderleri ile takipçiler arasında belirgin kopma yok (Dengeli).")

    # 3. Stop Avı Taraması
    print("\n🩸 STOP AVI (LIQUIDITY SWEEP) TARAMASI (Elit Hisseler):")
    from config import ELITE_LIQUID_TICKERS
    sweep_found = False
    for t in ELITE_LIQUID_TICKERS:
        df_t = fetch_data(t, period="2mo", interval="1d", use_cache=True)
        sw = detect_liquidity_sweep(df_t)
        if sw["sweep_detected"]:
            sweep_found = True
            print(f"   🔥 [{t.replace('.IS', '')}] : {sw['type']}")
            print(f"      {sw['desc']}")
    if not sweep_found:
        print("   • Son barlarda 20 günlük dip stop avı formasyonu görülmedi.")
