"""
Temel Strateji Sınıfı (Base Strategy Interface)
Tüm algoritmik stratejiler bu sınıftan miras alır.
"""
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Verilen fiyata ve indikatörlere göre al-sat sinyalleri üretir.
        
        Geri dönen DataFrame'de bulunması gereken sütunlar:
          - 'Signal': 1 (AL), -1 (SAT), 0 (BEKLE/TUT)
          - 'Reason': Sinyalin tetiklenme sebebi (örn: 'SuperTrend Boğa + EMA 21/50 Kesişimi')
        """
        pass

    def __str__(self) -> str:
        return self.name
