from strategies.base import BaseStrategy
from strategies.supertrend_ema import SuperTrendEMAStrategy
from strategies.rsi_bollinger import RSIBollingerStrategy
from strategies.macd_volume import MACDVolumeStrategy
from strategies.ensemble import EnsembleStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy
from strategies.bist_alpha_master import BISTAlphaMasterStrategy
from strategies.bist_sniper import BISTSniperStrategy

AVAILABLE_STRATEGIES = {
    "supertrend": SuperTrendEMAStrategy,
    "rsi_bb": RSIBollingerStrategy,
    "macd_vol": MACDVolumeStrategy,
    "ensemble": EnsembleStrategy,
    "momentum": MomentumBreakoutStrategy,
    "alpha": BISTAlphaMasterStrategy,
    "sniper": BISTSniperStrategy,
}

__all__ = [
    "BaseStrategy",
    "SuperTrendEMAStrategy",
    "RSIBollingerStrategy",
    "MACDVolumeStrategy",
    "EnsembleStrategy",
    "MomentumBreakoutStrategy",
    "BISTAlphaMasterStrategy",
    "BISTSniperStrategy",
    "AVAILABLE_STRATEGIES",
]
