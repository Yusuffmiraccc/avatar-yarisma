"""Çok değişkenli anomali tespiti (IsolationForest). Etiketsiz veride 'olağandışı kombinasyon' arar.

Kural tabanlı z-skoru tek değişkene bakar; bu model verim+maliyet veya parça oranları birlikte alışılmışın dışındaysa
işaretler. Sonuç tahmin değil uyarıdır; ground-truth yoktur, değerlendirme enjekte edilmiş anomalilerle yapılır.
"""

import numpy as np
from sklearn.ensemble import IsolationForest

MIN_SAMPLES = 30
CONTAMINATION = 0.03


def isolation_outliers(x: np.ndarray, contamination: float = CONTAMINATION, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """(aykırı maskesi, anomali skoru) döner; skor yükseldikçe daha anomali. Örnek azsa hiçbir şey işaretlenmez."""
    x = np.asarray(x, float)
    n = len(x)
    if n < MIN_SAMPLES:
        return np.zeros(n, bool), np.zeros(n)
    if not np.isfinite(x).all():
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    sd = x.std(axis=0)
    xs = (x - x.mean(axis=0)) / np.where(sd > 0, sd, 1.0)
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=seed).fit(xs)
    return model.predict(xs) == -1, -model.score_samples(xs)
