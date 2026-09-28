"""
Gelişmiş BIST Backtesting (Geriye Dönük Test) Motoru
Gerçekçi komisyon, kayma (slippage), Dinamik Stop-Loss, Kâr Al (Take-Profit)
ve İz Süren Stop (Trailing Stop) mantığı içerir.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd

from config import (
    DEFAULT_INITIAL_CAPITAL,
    DEFAULT_COMMISSION_RATE,
    DEFAULT_SLIPPAGE,
    DEFAULT_STOP_LOSS_PCT,
    DEFAULT_TAKE_PROFIT_PCT,
    DEFAULT_TRAILING_STOP_PCT
)
from strategies.base import BaseStrategy

@dataclass
class Trade:
    entry_date: Any
    entry_price: float
    shares: int
    exit_date: Optional[Any] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_days: int = 0

@dataclass
class BacktestResult:
    ticker: str
    strategy_name: str
    initial_capital: float
    final_equity: float
    total_return_pct: float
    buy_hold_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    df_with_signals: pd.DataFrame = field(default_factory=pd.DataFrame)

class Backtester:
    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        commission_rate: float = DEFAULT_COMMISSION_RATE,
        slippage: float = DEFAULT_SLIPPAGE,
        stop_loss_pct: float = DEFAULT_STOP_LOSS_PCT,
        take_profit_pct: float = DEFAULT_TAKE_PROFIT_PCT,
        trailing_stop_pct: float = DEFAULT_TRAILING_STOP_PCT,
        use_trailing_stop: bool = True
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.use_trailing_stop = use_trailing_stop

    def run(self, df: pd.DataFrame, ticker: str = "BIST") -> BacktestResult:
        if df.empty or len(df) < 30:
            raise ValueError("Yetersiz veri. En az 30 bar gereklidir.")

        # Strateji sinyallerini üret
        df = self.strategy.generate_signals(df).copy()

        capital = self.initial_capital
        shares = 0
        current_trade: Optional[Trade] = None
        trades: List[Trade] = []
        equity_records = []
        highest_price_in_trade = 0.0

        for i in range(len(df)):
            date = df.index[i]
            row = df.iloc[i]
            close = row["Close"]
            high = row["High"]
            low = row["Low"]
            signal = row.get("Signal", 0)

            # 1. Açık Pozisyon Kontrolü ve Risk Yönetimi (Stop-Loss / Take-Profit / Trailing Stop)
            if shares > 0 and current_trade is not None:
                # En yüksek fiyatı güncelle (Trailing Stop için)
                if high > highest_price_in_trade:
                    highest_price_in_trade = high

                exit_price = None
                exit_reason = ""

                # Stop-Loss Kontrolü
                stop_price = current_trade.entry_price * (1.0 - self.stop_loss_pct)
                # İz Süren Stop Kontrolü
                trailing_stop_price = highest_price_in_trade * (1.0 - self.trailing_stop_pct)
                if self.use_trailing_stop and trailing_stop_price > stop_price:
                    stop_price = trailing_stop_price

                # Take-Profit Kontrolü
                tp_price = current_trade.entry_price * (1.0 + self.take_profit_pct)

                if low <= stop_price:
                    exit_price = stop_price * (1.0 - self.slippage)
                    exit_reason = "İz Süren Stop" if (self.use_trailing_stop and stop_price == trailing_stop_price) else "Stop-Loss"
                elif high >= tp_price:
                    exit_price = tp_price * (1.0 - self.slippage)
                    exit_reason = "Kâr Al (Take-Profit)"
                elif signal == -1:
                    exit_price = close * (1.0 - self.slippage)
                    exit_reason = row.get("Reason", "Strateji Çıkış Sinyali")

                # Pozisyondan Çıkış
                if exit_price is not None:
                    # Komisyon düş
                    net_revenue = (shares * exit_price) * (1.0 - self.commission_rate)
                    capital += net_revenue

                    current_trade.exit_date = date
                    current_trade.exit_price = round(exit_price, 2)
                    current_trade.exit_reason = exit_reason
                    total_cost = current_trade.shares * current_trade.entry_price
                    current_trade.pnl = round(net_revenue - total_cost, 2)
                    current_trade.pnl_pct = round((current_trade.pnl / total_cost) * 100.0, 2)
                    
                    trades.append(current_trade)
                    shares = 0
                    current_trade = None
                    highest_price_in_trade = 0.0

            # 2. Yeni Pozisyon Açma (AL Sinyali)
            elif shares == 0 and signal == 1:
                buy_price = close * (1.0 + self.slippage)
                cost_per_share = buy_price * (1.0 + self.commission_rate)
                
                # Mevcut sermaye ile alınabilecek lot miktarı (BIST'te 1 hisse adedi)
                shares_to_buy = int(capital // cost_per_share)
                
                if shares_to_buy > 0:
                    total_outlay = shares_to_buy * cost_per_share
                    capital -= total_outlay
                    shares = shares_to_buy
                    highest_price_in_trade = buy_price
                    
                    current_trade = Trade(
                        entry_date=date,
                        entry_price=round(buy_price, 2),
                        shares=shares_to_buy
                    )

            # Günlük Portföy Değeri (Nakit + Açık Pozisyon Piyasa Değeri)
            current_portfolio_value = capital + (shares * close)
            equity_records.append((date, current_portfolio_value))

        # Son gün hala açık pozisyon varsa piyasa fiyatından kapat
        if shares > 0 and current_trade is not None:
            last_date = df.index[-1]
            last_price = df.iloc[-1]["Close"]
            net_revenue = (shares * last_price) * (1.0 - self.commission_rate)
            capital += net_revenue
            current_trade.exit_date = last_date
            current_trade.exit_price = round(last_price, 2)
            current_trade.exit_reason = "Test Sonu Otomatik Kapatma"
            total_cost = current_trade.shares * current_trade.entry_price
            current_trade.pnl = round(net_revenue - total_cost, 2)
            current_trade.pnl_pct = round((current_trade.pnl / total_cost) * 100.0, 2)
            trades.append(current_trade)

        equity_curve = pd.Series(
            [val for _, val in equity_records],
            index=[dt for dt, _ in equity_records],
            name="Portfolio_Value"
        )

        # İstatistiklerin Hesaplanması
        final_equity = equity_curve.iloc[-1] if not equity_curve.empty else self.initial_capital
        total_return_pct = ((final_equity - self.initial_capital) / self.initial_capital) * 100.0

        # Al ve Tut (Buy & Hold) Karşılaştırması
        initial_close = df.iloc[0]["Close"]
        final_close = df.iloc[-1]["Close"]
        buy_hold_return_pct = ((final_close - initial_close) / initial_close) * 100.0

        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl <= 0)
        win_rate_pct = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profits = sum(t.pnl for t in trades if t.pnl > 0)
        gross_losses = abs(sum(t.pnl for t in trades if t.pnl < 0))
        profit_factor = (gross_profits / gross_losses) if gross_losses > 0 else (99.0 if gross_profits > 0 else 0.0)

        # Maksimum Çekilme (Max Drawdown)
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        max_drawdown_pct = abs(float(drawdown.min())) * 100.0 if not drawdown.empty else 0.0

        # Günlük Getiriler ve Sharpe Oranı (Yıllık %35 risksiz faiz varsayımı - TR piyasası)
        daily_returns = equity_curve.pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() != 0:
            # Yıllık Sharpe (252 işlem günü)
            risk_free_daily = 0.35 / 252.0
            excess_return = daily_returns.mean() - risk_free_daily
            sharpe_ratio = float((excess_return / daily_returns.std()) * np.sqrt(252))
        else:
            sharpe_ratio = 0.0

        return BacktestResult(
            ticker=ticker,
            strategy_name=self.strategy.name,
            initial_capital=self.initial_capital,
            final_equity=round(final_equity, 2),
            total_return_pct=round(total_return_pct, 2),
            buy_hold_return_pct=round(buy_hold_return_pct, 2),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate_pct=round(win_rate_pct, 1),
            profit_factor=round(profit_factor, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            trades=trades,
            equity_curve=equity_curve,
            df_with_signals=df
        )
