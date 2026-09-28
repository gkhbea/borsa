"""
Gelişmiş Etkileşimli Grafik ve Raporlama Modülü
Plotly ile kurumsal düzeyde HTML raporu ve şamdan grafiği üretir.
"""
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from config import REPORTS_DIR
from backtester import BacktestResult

def create_interactive_chart(result: BacktestResult, output_path: Path = None) -> Path:
    """
    Backtest sonucunu şamdan grafiği, al-sat sinyalleri, indikatörler ve
    portföy büyüme eğrisi ile tek bir interaktif HTML raporu olarak kaydeder.
    """
    if output_path is None:
        clean_ticker = result.ticker.replace(".", "_")
        output_path = REPORTS_DIR / f"backtest_{clean_ticker}_{result.strategy_name[:10].strip()}.html"

    df = result.df_with_signals

    # 3 Alt Grafik Alanı:
    # 1. Fiyat Şamdanları + İndikatörler + Al/Sat Okları (row=1, 60% yükseklik)
    # 2. Hacim ve/veya RSI (row=2, 20% yükseklik)
    # 3. Portföy Büyüme Eğrisi vs Al-Tut (row=3, 20% yükseklik)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.55, 0.20, 0.25],
        subplot_titles=(
            f"{result.ticker} Fiyat ve Sinyal Analizi ({result.strategy_name})",
            "İşlem Hacmi (Volume)",
            "Portföy Değeri (TL) vs Al ve Tut (Benchmark)"
        )
    )

    # 1. Fiyat Şamdanları (Candlestick)
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Fiyat",
            increasing_line_color="#00C076",
            decreasing_line_color="#FF3B30",
            showlegend=False
        ),
        row=1, col=1
    )

    # Hareketli Ortalamalar (varsa)
    if "EMA_21" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA_21"], name="EMA 21", line=dict(color="#FF9500", width=1.5)), row=1, col=1)
    if "EMA_50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA_50"], name="EMA 50", line=dict(color="#007AFF", width=1.5)), row=1, col=1)

    # SuperTrend (varsa)
    if "SuperTrend" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["SuperTrend"], name="SuperTrend", line=dict(color="#AF52DE", width=1.8, dash="dot")), row=1, col=1)

    # Bollinger Bantları (varsa)
    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Üst", line=dict(color="rgba(150,150,150,0.5)", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Alt", line=dict(color="rgba(150,150,150,0.5)", width=1)), row=1, col=1)

    # Gerçekleşen Alım ve Satım İşaretçileri (Trades)
    buy_dates = [t.entry_date for t in result.trades]
    buy_prices = [t.entry_price for t in result.trades]
    exit_dates = [t.exit_date for t in result.trades if t.exit_date is not None]
    exit_prices = [t.exit_price for t in result.trades if t.exit_price is not None]
    exit_hover = [f"Sebep: {t.exit_reason}<br>Getiri: %{t.pnl_pct}" for t in result.trades if t.exit_date is not None]

    if buy_dates:
        fig.add_trace(
            go.Scatter(
                x=buy_dates,
                y=buy_prices,
                mode="markers",
                marker=dict(symbol="triangle-up", size=13, color="#00C076", line=dict(width=1.5, color="white")),
                name="AL Girişi",
                hovertext=[f"Lot: {t.shares}<br>Fiyat: {t.entry_price} TL" for t in result.trades]
            ),
            row=1, col=1
        )

    if exit_dates:
        fig.add_trace(
            go.Scatter(
                x=exit_dates,
                y=exit_prices,
                mode="markers",
                marker=dict(symbol="triangle-down", size=13, color="#FF3B30", line=dict(width=1.5, color="white")),
                name="SAT / Çıkış",
                hovertext=exit_hover
            ),
            row=1, col=1
        )

    # 2. Hacim Çubukları (Volume)
    colors = ["#00C076" if c >= o else "#FF3B30" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Hacim",
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )

    # 3. Portföy Değeri vs Al & Tut Eğrisi
    if not result.equity_curve.empty:
        # Benchmark hesapla (Al ve Tut sermaye simülasyonu)
        first_close = df.loc[result.equity_curve.index[0], "Close"]
        buy_hold_equity = result.initial_capital * (df.loc[result.equity_curve.index, "Close"] / first_close)

        fig.add_trace(
            go.Scatter(
                x=result.equity_curve.index,
                y=result.equity_curve.values,
                name="Algoritmik Bot Portföyü",
                line=dict(color="#00C076", width=2.5)
            ),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=buy_hold_equity.index,
                y=buy_hold_equity.values,
                name="Sadece Al & Tut (BIST Hisse)",
                line=dict(color="#8E8E93", width=1.5, dash="dash")
            ),
            row=3, col=1
        )

    # Başlık ve Tasarım Teması (Modern Dark Finansal Arayüz)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#12151A",
        plot_bgcolor="#181C24",
        title=dict(
            text=f"<b>BIST Algoritmik Bot Raporu: {result.ticker}</b> | Toplam Getiri: %{result.total_return_pct} (Al-Tut: %{result.buy_hold_return_pct}) | Kazanma: %{result.win_rate_pct}",
            font=dict(size=18, color="#FFFFFF")
        ),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=80, b=40),
        height=900
    )

    fig.write_html(str(output_path))
    return output_path
