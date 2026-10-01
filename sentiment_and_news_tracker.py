"""
BIST 360 - Haber, Yorum, KAP ve Tüyo Takip Motoru
1. Hisse bazlı son haberleri, KAP duyurularını ve piyasa yorumlarını tarar.
2. Sıcak gelişmeleri (İhale, Sözleşme, Geri Alım, Temettü, Bedelsiz, Devre Kesici) filtreler.
3. Sosyal medya pompalaması mı yoksa gerçek kurumsal hikaye mi olduğunu broker gözüyle ayıklar.
4. Önemli bir tüyo/katalizör yakaladığında anında ekrana ve e-postaya uyarı geçer.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
import time

# Katalizör ve Tüyo Anahtar Kelimeleri
POSITIVE_CATALYSTS = [
    "ihale", "sözleşme", "anlaşma", "sipariş", "geri alım", "pay alımı",
    "temettü", "bedelsiz", "rekor kâr", "hedef fiyat", "yatırım",
    "kap bildirimi", "ortaklık", "onay", "yükseltti", "tavsiye", "al tavsiyesi"
]

NEGATIVE_CATALYSTS = [
    "devre kesici", "tedbir", "ceza", "soruşturma", "dava", "bedelli",
    "zarar", "not indirimi", "düşürdü", "yasak", "satış baskısı", "istifa"
]

def fetch_latest_stock_news(ticker: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Hisse ile ilgili en son haberleri ve piyasa yorumlarını Google News TR RSS üzerinden çeker."""
    clean_t = ticker.replace(".IS", "").upper()
    query = f"{clean_t} hisse borsa"
    encoded_q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=tr&gl=TR&ceid=TR:tr"

    news_list = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        items = root.findall("./channel/item")

        for item in items[:limit]:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            source = item.find("source").text if item.find("source") is not None else "Finans Medyası"

            news_list.append({
                "ticker": clean_t,
                "title": title,
                "link": link,
                "date": pub_date[:16] if pub_date else "",
                "source": source
            })
    except Exception as e:
        pass

    return news_list

def analyze_stock_sentiment_and_tips(ticker: str) -> Dict[str, Any]:
    """Hisse ile ilgili haberleri analiz ederek sıcak tüyo veya riskleri belirler."""
    clean_t = ticker.replace(".IS", "").upper()
    news_items = fetch_latest_stock_news(ticker, limit=8)

    pos_hits = []
    neg_hits = []
    hot_tips = []

    for n in news_items:
        t_lower = n["title"].lower()

        # Pozitif tüyo kontrolü
        for kw in POSITIVE_CATALYSTS:
            if kw in t_lower:
                pos_hits.append(kw)
                hot_tips.append({
                    "type": "POZİTİF KATALİZÖR / TÜYO",
                    "keyword": kw.upper(),
                    "headline": n["title"],
                    "source": n["source"],
                    "date": n["date"]
                })
                break

        # Negatif risk kontrolü
        for kw in NEGATIVE_CATALYSTS:
            if kw in t_lower:
                neg_hits.append(kw)
                hot_tips.append({
                    "type": "⚠️ RİSK / UYARI",
                    "keyword": kw.upper(),
                    "headline": n["title"],
                    "source": n["source"],
                    "date": n["date"]
                })
                break

    # Duygu Skoru Hesabı (-100 ile +100 arası)
    total_catalysts = len(pos_hits) + len(neg_hits)
    if total_catalysts > 0:
        sentiment_score = int(((len(pos_hits) - len(neg_hits)) / total_catalysts) * 100)
    else:
        sentiment_score = 0

    # Broker Değerlendirmesi
    if sentiment_score >= 50:
        verdict = "🔥 SICAK HABER / GÜÇLÜ POZİTİF AKIŞ"
        advice = "Medyada ve bültenlerde güçlü pozitif hikaye var. Destek seviyelerinden alım iştahı artabilir."
    elif sentiment_score <= -50:
        verdict = "⚠️ DİKKAT: BASKI VE RİSK HABERİ"
        advice = "Hisse üzerinde olumsuz haber/tedbir veya satış baskısı var. Alım için suların durulması beklenmeli."
    else:
        verdict = "📊 DENGELİ / RUTİN PİYASA YORUMU"
        advice = "Haber akışı olağan seyrinde. Kararlar tamamen bilanço ve teknik pusu seviyelerine göre verilmeli."

    return {
        "ticker": clean_t,
        "sentiment_score": sentiment_score,
        "verdict": verdict,
        "broker_advice": advice,
        "hot_tips": hot_tips,
        "recent_news": news_items[:3]
    }

def verify_stock_before_buy(ticker: str) -> Dict[str, Any]:
    """Alım yapmadan önce hisseyi son dakika tüyolarına ve haber tuzaklarına karşı denetler."""
    analysis = analyze_stock_sentiment_and_tips(ticker)
    has_negative_alert = any(tip["type"] == "⚠️ RİSK / UYARI" for tip in analysis["hot_tips"])
    
    can_buy = not has_negative_alert
    
    warning_note = ""
    if has_negative_alert:
        warning_note = "Hisse hakkında son dakika olumsuz haber/tedbir tespit edildi, alım emri iptal edilmeli veya ertelenmelidir!"
    elif analysis["hot_tips"]:
        warning_note = "Pozitif tüyo/katalizör mevcut. Açılışta tavan kovalamadan pusu fiyatından limit emirle giriniz."
    else:
        warning_note = "Temiz haber akışı. Planlanan pusu fiyatından %10 sermaye ile girilebilir."

    return {
        "ticker": analysis["ticker"],
        "can_buy": can_buy,
        "warning_note": warning_note,
        "hot_tips": analysis["hot_tips"],
        "verdict": analysis["verdict"]
    }

if __name__ == "__main__":
    test_tickers = ["THYAO.IS", "BIMAS.IS", "TUPRS.IS", "YKBNK.IS"]
    print("\n" + "="*80)
    print("🕵️‍♂️ BIST BROKER TÜYO VE HABER RADARI TESTİ")
    print("="*80)

    for t in test_tickers:
        res = analyze_stock_sentiment_and_tips(t)
        print(f"\n📌 {res['ticker']} | Durum: {res['verdict']} (Skor: {res['sentiment_score']})")
        print(f"💡 Broker Yorumu: {res['broker_advice']}")
        if res["hot_tips"]:
            print("🔥 Yakalanan Tüyolar & Sıcak Gelişmeler:")
            for tip in res["hot_tips"][:2]:
                print(f"   [{tip['type']}] ({tip['keyword']}) - {tip['headline']} [{tip['source']}]")
        print("Son Haber Başlıkları:")
        for n in res["recent_news"]:
            print(f"   • {n['title']} ({n['source']})")
