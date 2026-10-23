"""Saf maliyet fonksiyonları (DB'siz). Tüm hesaplar Decimal; yuvarlama ROUND_HALF_UP, para 4 basamak."""

from decimal import ROUND_HALF_UP, Decimal

Q4 = Decimal("0.0001")
Q6 = Decimal("0.000001")
ZERO = Decimal(0)


def q4(x: Decimal) -> Decimal:
    return x.quantize(Q4, rounding=ROUND_HALF_UP)


def q6(x: Decimal) -> Decimal:
    return x.quantize(Q6, rounding=ROUND_HALF_UP)


def display2(x: Decimal) -> Decimal:
    """Raporlama gösterimi (2 basamak). Saklanan değer 4 basamaktır."""
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def line_total(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    return q4(quantity * unit_cost)


def unit_cost(total: Decimal, quantity: Decimal) -> Decimal:
    if quantity <= 0:
        raise ValueError("Miktar pozitif olmalıdır.")
    return q4(total / quantity)


def allocate(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """total tutarını ağırlıklarla orantılı dağıtır; yuvarlama artığı SON satıra verilir.

    Garanti: sum(sonuç) == total (assert ile korunur).
    """
    if not weights:
        raise ValueError("Dağıtım için en az bir ağırlık gerekir.")
    w_sum = sum(weights, ZERO)
    if w_sum <= 0:
        raise ValueError("Ağırlık toplamı pozitif olmalıdır.")
    total = q4(total)
    parts = [q4(total * w / w_sum) for w in weights[:-1]]
    parts.append(total - sum(parts, ZERO))
    assert sum(parts, ZERO) == total
    return parts


def allocate_quantity(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """allocate ile aynı mantık, 6 basamaklı miktarlar için."""
    w_sum = sum(weights, ZERO)
    parts = [q6(total * w / w_sum) for w in weights[:-1]]
    parts.append(total - sum(parts, ZERO))
    return parts


def margin(vkp: Decimal, ekp: Decimal) -> dict[str, Decimal]:
    gross = q4(vkp - ekp)
    pct = q4((gross / vkp) * 100) if vkp else ZERO
    return {"gross_profit_per_unit": gross, "margin_percent": pct}
