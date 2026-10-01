"""
BIST 360 - 1 Haftalık Otonom Test ve Sanal Portföy Motoru (Paper Trading Engine)
Kullanıcının müdahale etmesine gerek kalmadan:
1. 100.000 TL sanal sermaye ile başlar.
2. Her hisseye maksimum %10 (10.000 TL) tahsis eder.
3. Alım sinyallerinde otomatik pozisyon açar, stop-loss ve hedef seviyelerini canlı izler.
4. Kâr realizasyonu ve zarar kes işlemlerini şeffaf şekilde günlüğe kaydeder.
5. Günlük portföy ekstresini ekrana ve e-postaya iletir.
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from tabulate import tabulate

from config import (
    DATA_DIR, DEFAULT_INITIAL_CAPITAL, MAX_POSITION_SIZE_PCT,
    POSITION_ALLOCATION_TL, MAX_OPEN_POSITIONS, MIN_CASH_RESERVE_TL
)
from data_loader import fetch_data

PORTFOLIO_FILE = DATA_DIR / "paper_portfolio.json"

def load_portfolio() -> Dict[str, Any]:
    """Portföy durumunu yükler veya sıfırdan 5.000 TL ile başlatır."""
    if PORTFOLIO_FILE.exists():
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Başlangıç Durumu (5.000 TL Mikro-Portföy)
    today_str = datetime.date.today().isoformat()
    portfolio = {
        "start_date": today_str,
        "initial_capital": DEFAULT_INITIAL_CAPITAL,
        "cash": DEFAULT_INITIAL_CAPITAL,
        "total_equity": DEFAULT_INITIAL_CAPITAL,
        "day_start_equity": DEFAULT_INITIAL_CAPITAL,
        "last_snapshot_date": today_str,
        "open_positions": {},      # {ticker: {entry_price, lots, cost, stop_loss, target_1, target_2, entry_date, reason, half_sold}}
        "closed_trades": [],       # list of {ticker, entry_price, exit_price, lots, pnl_tl, pnl_pct, exit_reason, exit_date}
        "daily_history": []        # list of daily snapshots
    }
    save_portfolio(portfolio)
    return portfolio

def save_portfolio(portfolio: Dict[str, Any]):
    """Portföyü diske kaydeder."""
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[HATA] Portföy kaydedilemedi: {e}")

def open_paper_position(ticker: str, price: float, stop_loss: float, target_1: float, target_2: float, reason: str) -> bool:
    """Otonom alım işlemi gerçekleştirir (5.000 TL bütçe için ~2.000 TL tahsis)."""
    portfolio = load_portfolio()
    clean_t = ticker.replace(".IS", "")

    # Zaten açık pozisyon var mı?
    if clean_t in portfolio["open_positions"]:
        return False

    # Maksimum açık pozisyon kontrolü (Maksimum 2 açık hisse)
    if len(portfolio["open_positions"]) >= MAX_OPEN_POSITIONS:
        print(f"[OTONOM TEST] Portföy dolu (Maksimum {MAX_OPEN_POSITIONS} açık pozisyona ulaşıldı), {clean_t} alınmadı.")
        return False

    # Pozisyon Büyüklüğü: ~2.000 TL tahsis
    available_cash = portfolio["cash"]
    if available_cash < 500.0:
        print(f"[OTONOM TEST] Yetersiz nakit ({available_cash:,.0f} TL), {clean_t} alınamadı.")
        return False

    target_allocation = min(POSITION_ALLOCATION_TL, available_cash)
    lots = int(target_allocation // price)
    
    # Eğer hisse fiyatı 2.000 TL'den biraz yüksekse (örn: 2.100 TL) ve nakit yetiyorsa 1 lot al
    if lots <= 0 and available_cash >= price and price <= (POSITION_ALLOCATION_TL * 1.25):
        lots = 1

    if lots <= 0:
        print(f"[OTONOM TEST] Fiyat ({price:.2f} TL) tahsis bütçesini aşıyor, {clean_t} alınamadı.")
        return False

    total_cost = round(lots * price, 2)
    portfolio["cash"] = round(portfolio["cash"] - total_cost, 2)

    portfolio["open_positions"][clean_t] = {
        "ticker": clean_t,
        "entry_price": price,
        "lots": lots,
        "initial_lots": lots,
        "cost": total_cost,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "entry_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "reason": reason,
        "half_sold": False
    }

    save_portfolio(portfolio)
    print(f"\n🟢 [OTONOM ALIM GERÇEKLEŞTİ] {clean_t} | {lots} Lot @ {price:.2f} TL (Tutar: {total_cost:,.0f} TL)")
    print(f"   🛑 Stop-Loss: {stop_loss:.2f} TL | 🎯 Hedef 1: {target_1:.2f} TL | Kalan Nakit: {portfolio['cash']:,.0f} TL")
    return True

def update_paper_positions() -> List[Dict[str, Any]]:
    """Açık pozisyonları canlı fiyatlarla denetler; kâr al veya zarar kes uygular."""
    portfolio = load_portfolio()
    events = []

    if not portfolio["open_positions"]:
        return events

    tickers_to_remove = []

    for clean_t, pos in portfolio["open_positions"].items():
        sym = f"{clean_t}.IS"
        df = fetch_data(sym, period="5d", interval="1d", use_cache=False)
        if df.empty:
            continue

        curr_price = df["Close"].iloc[-1]
        lots = pos["lots"]
        entry_price = pos["entry_price"]
        stop_loss = pos["stop_loss"]
        target_1 = pos["target_1"]
        target_2 = pos["target_2"]

        # 1. Stop-Loss Kontrolü (Zarar Kes)
        if curr_price <= stop_loss:
            pnl_tl = round((curr_price - entry_price) * lots, 2)
            pnl_pct = round(((curr_price / entry_price) - 1) * 100, 2)
            portfolio["cash"] = round(portfolio["cash"] + (lots * curr_price), 2)

            portfolio["closed_trades"].append({
                "ticker": clean_t,
                "entry_price": entry_price,
                "exit_price": curr_price,
                "lots": lots,
                "pnl_tl": pnl_tl,
                "pnl_pct": pnl_pct,
                "exit_reason": "🛑 STOP-LOSS TETİKLENDİ",
                "exit_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            tickers_to_remove.append(clean_t)
            events.append({
                "ticker": clean_t,
                "event": "STOP-LOSS",
                "pnl_tl": pnl_tl,
                "pnl_pct": pnl_pct,
                "price": curr_price
            })
            continue

        # 2. Hedef 1 Kontrolü (Kâr Al %50 ve Stopu Başa Başa Çek)
        if curr_price >= target_1 and not pos.get("half_sold", False):
            sell_lots = lots // 2
            if sell_lots > 0:
                pnl_tl = round((curr_price - entry_price) * sell_lots, 2)
                pnl_pct = round(((curr_price / entry_price) - 1) * 100, 2)
                portfolio["cash"] = round(portfolio["cash"] + (sell_lots * curr_price), 2)

                pos["lots"] = lots - sell_lots
                pos["half_sold"] = True
                pos["stop_loss"] = entry_price  # Stop maliyete çekildi!

                portfolio["closed_trades"].append({
                    "ticker": clean_t,
                    "entry_price": entry_price,
                    "exit_price": curr_price,
                    "lots": sell_lots,
                    "pnl_tl": pnl_tl,
                    "pnl_pct": pnl_pct,
                    "exit_reason": "🎯 HEDEF 1 KÂR AL (%50 Realize)",
                    "exit_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                events.append({
                    "ticker": clean_t,
                    "event": "HEDEF 1 KÂR AL",
                    "pnl_tl": pnl_tl,
                    "pnl_pct": pnl_pct,
                    "price": curr_price
                })

        # 3. Hedef 2 Kontrolü (Tam Kapanış)
        if curr_price >= target_2:
            rem_lots = pos["lots"]
            pnl_tl = round((curr_price - entry_price) * rem_lots, 2)
            pnl_pct = round(((curr_price / entry_price) - 1) * 100, 2)
            portfolio["cash"] = round(portfolio["cash"] + (rem_lots * curr_price), 2)

            portfolio["closed_trades"].append({
                "ticker": clean_t,
                "entry_price": entry_price,
                "exit_price": curr_price,
                "lots": rem_lots,
                "pnl_tl": pnl_tl,
                "pnl_pct": pnl_pct,
                "exit_reason": "🚀 HEDEF 2 ANA TREND KÂR AL (Pozisyon Kapatıldı)",
                "exit_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            tickers_to_remove.append(clean_t)
            events.append({
                "ticker": clean_t,
                "event": "HEDEF 2 KÂR AL",
                "pnl_tl": pnl_tl,
                "pnl_pct": pnl_pct,
                "price": curr_price
            })

    for t in tickers_to_remove:
        portfolio["open_positions"].pop(t, None)

    save_portfolio(portfolio)
    return events

def get_portfolio_summary_report() -> Dict[str, Any]:
    """Portföyün anlık kâr/zarar ve varlık durumunu hesaplar."""
    portfolio = load_portfolio()
    cash = portfolio["cash"]
    unrealized_pnl = 0.0
    current_stock_value = 0.0
    today_str = datetime.date.today().isoformat()

    # Gün başlangıç sermayesini yönet
    last_snap = portfolio.get("last_snapshot_date", today_str)
    day_start_equity = portfolio.get("day_start_equity", portfolio.get("initial_capital", DEFAULT_INITIAL_CAPITAL))

    if last_snap != today_str:
        # Yeni gün başladı; dünkü kapanış bugünün açılışıdır
        day_start_equity = portfolio.get("total_equity", portfolio["initial_capital"])
        portfolio["day_start_equity"] = day_start_equity
        portfolio["last_snapshot_date"] = today_str
        save_portfolio(portfolio)

    open_pos_rows = []
    for clean_t, pos in portfolio["open_positions"].items():
        sym = f"{clean_t}.IS"
        df = fetch_data(sym, period="5d", interval="1d", use_cache=True)
        curr_p = df["Close"].iloc[-1] if not df.empty else pos["entry_price"]
        lots = pos["lots"]
        pos_val = lots * curr_p
        pos_cost = lots * pos["entry_price"]
        pnl = pos_val - pos_cost
        pnl_p = ((curr_p / pos["entry_price"]) - 1) * 100

        current_stock_value += pos_val
        unrealized_pnl += pnl

        open_pos_rows.append({
            "Hisse": clean_t,
            "Lot": f"{lots} Adet",
            "Maliyet": f"{pos['entry_price']:.2f} TL",
            "Son Fiyat": f"{curr_p:.2f} TL",
            "Piyasa Değeri": f"{pos_val:,.0f} TL",
            "Kâr/Zarar": f"{pnl:+,.0f} TL (%{pnl_p:+.1f})",
            "Stop-Loss": f"{pos['stop_loss']:.2f} TL",
            "Hedef": f"{pos['target_1']:.2f} TL"
        })

    realized_pnl = sum(t["pnl_tl"] for t in portfolio["closed_trades"])
    total_equity = cash + current_stock_value
    portfolio["total_equity"] = round(total_equity, 2)
    save_portfolio(portfolio)

    total_return_pct = ((total_equity / portfolio["initial_capital"]) - 1) * 100
    daily_pnl_tl = round(total_equity - day_start_equity, 2)
    daily_pnl_pct = round((daily_pnl_tl / day_start_equity) * 100, 2) if day_start_equity > 0 else 0.0

    # Bugün kapatılan işlemler
    closed_today = [
        t for t in portfolio.get("closed_trades", [])
        if t.get("exit_date", "").startswith(today_str)
    ]
    realized_today_tl = sum(t["pnl_tl"] for t in closed_today)

    return {
        "start_date": portfolio.get("start_date", ""),
        "today_date": today_str,
        "initial_capital": portfolio["initial_capital"],
        "day_start_equity": day_start_equity,
        "cash": cash,
        "stock_value": current_stock_value,
        "total_equity": total_equity,
        "daily_pnl_tl": daily_pnl_tl,
        "daily_pnl_pct": daily_pnl_pct,
        "realized_today_tl": realized_today_tl,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_return_pct": total_return_pct,
        "open_positions": open_pos_rows,
        "closed_trades_count": len(portfolio["closed_trades"]),
        "closed_trades_today": closed_today,
        "closed_trades": portfolio["closed_trades"][-5:]  # Son 5 kapalı işlem
    }

def record_daily_snapshot() -> Dict[str, Any]:
    """19:00 günlük kapanış anında gün sonu değerini kaydeder."""
    portfolio = load_portfolio()
    rep = get_portfolio_summary_report()
    today_str = datetime.date.today().isoformat()

    snapshot = {
        "date": today_str,
        "time": "19:00",
        "day_start_equity": rep["day_start_equity"],
        "total_equity": rep["total_equity"],
        "cash": rep["cash"],
        "stock_value": rep["stock_value"],
        "daily_pnl_tl": rep["daily_pnl_tl"],
        "daily_pnl_pct": rep["daily_pnl_pct"],
        "total_return_pct": rep["total_return_pct"],
        "open_positions_count": len(rep["open_positions"]),
        "closed_today_count": len(rep["closed_trades_today"])
    }

    # Bugünün kaydı zaten varsa güncelle, yoksa ekle
    history = portfolio.get("daily_history", [])
    history = [h for h in history if h.get("date") != today_str]
    history.append(snapshot)
    portfolio["daily_history"] = history
    portfolio["last_snapshot_date"] = today_str
    save_portfolio(portfolio)
    return rep

if __name__ == "__main__":
    rep = get_portfolio_summary_report()
    print("\n" + "="*80)
    print("📊 BIST 360 - 1 HAFTALIK OTONOM TEST PORTFÖYÜ DURUMU")
    print("="*80)
    print(f"Başlangıç: {rep['start_date']} | Başlangıç Sermayesi: {rep['initial_capital']:,.0f} TL")
    print(f"Kasadaki Nakit : {rep['cash']:,.0f} TL")
    print(f"Hisse Varlığı  : {rep['stock_value']:,.0f} TL")
    print(f"Toplam Varlık  : {rep['total_equity']:,.0f} TL | Toplam Getiri: %{rep['total_return_pct']:+.2f}")
    print(f"Realize Kâr    : {rep['realized_pnl']:+,.0f} TL | Açık Kâr/Zarar: {rep['unrealized_pnl']:+,.0f} TL\n")

    if rep["open_positions"]:
        print("📌 AÇIK POZİSYONLAR:")
        df_p = pd.DataFrame(rep["open_positions"])
        print(tabulate(df_p, headers="keys", tablefmt="fancy_grid", showindex=False))
    else:
        print("📌 Şu anda açık pozisyon yok (Tamamı Nakitte).")
