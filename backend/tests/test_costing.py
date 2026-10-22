from decimal import Decimal as D

from app.services import costing as c


def test_pdf_reference_scenario_ekp():
    inputs = [c.line_total(D("100"), D("9.70")), c.line_total(D("2"), D("24.00")), c.line_total(D("5"), D("11.60"))]
    assert inputs == [D("970.0000"), D("48.0000"), D("58.0000")]
    service = c.line_total(D("85"), D("5.50"))
    assert service == D("467.5000")
    total = sum(inputs, D("0")) + service
    assert total == D("1543.5000")
    ekp = c.unit_cost(total, D("85"))
    assert ekp == D("18.1588") and c.display2(ekp) == D("18.16")


def test_allocate_sums_exactly_with_residual_on_last():
    parts = c.allocate(D("100"), [D("1"), D("1"), D("1")])
    assert parts == [D("33.3333"), D("33.3333"), D("33.3334")]
    assert sum(parts) == D("100.0000")


def test_allocate_by_weight_property():
    import random
    rnd = random.Random(7)
    for _ in range(200):
        w = [D(str(rnd.randint(1, 5000))) / D("100") for _ in range(rnd.randint(1, 9))]
        total = D(str(rnd.randint(1, 10**7))) / D("100")
        assert sum(c.allocate(total, w)) == c.q4(total)


def test_lamb_source_inconsistency_arithmetic():
    assert c.line_total(D("25"), D("11.50")) == D("287.5000")
    assert c.line_total(D("25"), D("11.50")) != D("351.00")
