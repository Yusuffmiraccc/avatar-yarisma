"""Deterministic EKP calculation; this is business logic, not an ML model."""
from __future__ import annotations


def calculate_ekp(total_material_cost: float, external_service_cost: float, predicted_package_count: float) -> float:
    """Return EKP in EUR/package for known costs and a predicted package count.

    Costs must use the same currency; `predicted_package_count` must be > 0.
    """
    values = (total_material_cost, external_service_cost, predicted_package_count)
    if any(not isinstance(x, (int, float)) for x in values):
        raise TypeError("Tüm girdiler sayısal olmalıdır.")
    if total_material_cost < 0 or external_service_cost < 0:
        raise ValueError("Maliyetler negatif olamaz.")
    if predicted_package_count <= 0:
        raise ValueError("Tahmini paket sayısı sıfırdan büyük olmalıdır.")
    return (float(total_material_cost) + float(external_service_cost)) / float(predicted_package_count)
