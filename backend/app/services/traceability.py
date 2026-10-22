"""İleri/geri izleme: yalnızca kayıtlı genealogy ve sevkiyat satırlarına dayanır (AI/tahmin yok)."""

from collections import defaultdict, deque
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import (ButcheringOrder, Customer, InventoryBalance, Lot, LotGenealogyEdge, Product, ProductionOrder,
                        ReworkOrder, Shipment, ShipmentLine, Supplier)
from app.schemas.common import ApiModel, Dec
from app.services import costing, stock

ZERO = Decimal("0")
SECOND_TIER_NOTE = ("İkinci kademe dağıtım yalnızca sistemde kayıtlıysa gösterilir; "
                    "kayıtlı olmayan alt dağıtım tahmin edilmez.")


class LotNode(ApiModel):
    lot_id: int
    lot_code: str
    product_code: str
    product_name: str
    depth: int
    role: str  # ORIGIN | DERIVED | ANCESTOR
    unit_code: str
    produced_quantity: Dec
    on_hand_quantity: Dec
    origin_share: Dec | None = None  # kayıtlı kenarlardan hesaplanan kaynak payı (0..1)
    is_blocked: bool
    via_process_type: str | None = None
    via_process_code: str | None = None
    supplier_code: str | None = None
    supplier_name: str | None = None


class ShipmentHit(ApiModel):
    customer_id: int
    customer_code: str
    customer_name: str
    phone: str | None = None
    email: str | None = None
    lot_id: int
    lot_code: str
    shipment_id: int
    shipment_code: str
    shipped_at: str | None = None
    quantity: Dec
    unit_code: str


class CustomerImpact(ApiModel):
    customer_id: int
    customer_code: str
    customer_name: str
    phone: str | None = None
    email: str | None = None
    lots: dict[str, Dec]
    total_quantity: Dec


class ForwardResult(ApiModel):
    origin_lot_codes: list[str]
    lots: list[LotNode]
    shipments: list[ShipmentHit]
    customers: list[CustomerImpact]
    remaining_stock_total: Dec
    second_tier: list = []
    second_tier_note: str = SECOND_TIER_NOTE


class BackwardResult(ApiModel):
    target_lot_code: str
    lots: list[LotNode]
    orders: list[dict]
    suppliers: list[dict]


def _lot(db: Session, lot_id: int) -> Lot:
    lot = db.get(Lot, lot_id)
    if lot is None:
        raise not_found("Lot", lot_id)
    return lot


def _proc_code(db: Session, ptype: str, pid: int) -> str | None:
    model = {"PRODUCTION": ProductionOrder, "BUTCHERING": ButcheringOrder, "REWORK": ReworkOrder}.get(ptype)
    obj = db.get(model, pid) if model else None
    return obj.order_code if obj else None


def _node(db: Session, lot: Lot, depth: int, role: str, share=None, via=None) -> LotNode:
    prod = db.get(Product, lot.product_id)
    bal = db.get(InventoryBalance, lot.id)
    sup = db.get(Supplier, lot.supplier_id) if lot.supplier_id else None
    return LotNode(lot_id=lot.id, lot_code=lot.lot_code, product_code=prod.code, product_name=prod.name, depth=depth,
                   role=role, unit_code=lot.unit_code, produced_quantity=lot.initial_quantity,
                   on_hand_quantity=bal.on_hand_quantity if bal else ZERO, origin_share=share,
                   is_blocked=stock.active_block(db, lot.id) is not None,
                   via_process_type=via[0] if via else None, via_process_code=via[1] if via else None,
                   supplier_code=sup.code if sup else None, supplier_name=sup.name if sup else None)


def forward(db: Session, origin_ids: list[int]) -> ForwardResult:
    origins = [_lot(db, i) for i in origin_ids]
    depth: dict[int, int] = {o.id: 0 for o in origins}
    via: dict[int, tuple[str, str | None]] = {}
    edges_into: dict[int, list[LotGenealogyEdge]] = defaultdict(list)
    q = deque(o.id for o in origins)
    while q:
        cur = q.popleft()
        for e in db.scalars(select(LotGenealogyEdge).where(LotGenealogyEdge.source_lot_id == cur)):
            edges_into[e.target_lot_id].append(e)
            if e.target_lot_id not in depth:  # ziyaret kümesi: döngü koruması
                depth[e.target_lot_id] = depth[cur] + 1
                via[e.target_lot_id] = (e.process_type, _proc_code(db, e.process_type, e.process_id))
                q.append(e.target_lot_id)

    share: dict[int, Decimal] = {o.id: Decimal("1") for o in origins}

    def share_of(lot_id: int, seen=frozenset()) -> Decimal:
        if lot_id in share:
            return share[lot_id]
        lot = db.get(Lot, lot_id)
        total = lot.initial_quantity or Decimal("1")
        acc = ZERO
        for e in edges_into[lot_id]:
            if e.source_lot_id in seen or e.source_lot_id not in depth:
                continue
            acc += share_of(e.source_lot_id, seen | {lot_id}) * e.target_quantity
        share[lot_id] = min(costing.q6(acc / total), Decimal("1"))
        return share[lot_id]

    nodes: list[LotNode] = []
    for lid in sorted(depth, key=lambda i: (depth[i], i)):
        lot = db.get(Lot, lid)
        nodes.append(_node(db, lot, depth[lid], "ORIGIN" if lid in origin_ids else "DERIVED", share_of(lid), via.get(lid)))

    hits: list[ShipmentHit] = []
    rows = db.execute(
        select(ShipmentLine, Shipment, Customer, Lot).join(Shipment, Shipment.id == ShipmentLine.shipment_id)
        .join(Customer, Customer.id == Shipment.customer_id).join(Lot, Lot.id == ShipmentLine.lot_id)
        .where(ShipmentLine.lot_id.in_(list(depth)), Shipment.status == "SHIPPED")
        .order_by(Shipment.shipped_at, ShipmentLine.id))
    for sl, sh, cu, lot in rows:
        hits.append(ShipmentHit(customer_id=cu.id, customer_code=cu.code, customer_name=cu.name, phone=cu.phone,
                                email=cu.email, lot_id=lot.id, lot_code=lot.lot_code, shipment_id=sh.id,
                                shipment_code=sh.shipment_code,
                                shipped_at=sh.shipped_at.isoformat(timespec="microseconds") + "Z" if sh.shipped_at else None,
                                quantity=sl.quantity, unit_code=sl.unit_code))
    by_cust: dict[int, CustomerImpact] = {}
    for h in hits:
        ci = by_cust.setdefault(h.customer_id, CustomerImpact(
            customer_id=h.customer_id, customer_code=h.customer_code, customer_name=h.customer_name, phone=h.phone,
            email=h.email, lots={}, total_quantity=ZERO))
        ci.lots[h.lot_code] = ci.lots.get(h.lot_code, ZERO) + h.quantity
        ci.total_quantity += h.quantity
    remaining = sum((n.on_hand_quantity for n in nodes), ZERO)
    return ForwardResult(origin_lot_codes=[o.lot_code for o in origins], lots=nodes, shipments=hits,
                         customers=sorted(by_cust.values(), key=lambda c: c.customer_code),
                         remaining_stock_total=remaining)


def backward(db: Session, lot_id: int) -> BackwardResult:
    target = _lot(db, lot_id)
    depth = {target.id: 0}
    via: dict[int, tuple[str, str | None]] = {}
    orders: dict[tuple[str, int], dict] = {}
    q = deque([target.id])
    while q:
        cur = q.popleft()
        for e in db.scalars(select(LotGenealogyEdge).where(LotGenealogyEdge.target_lot_id == cur)):
            key = (e.process_type, e.process_id)
            orders.setdefault(key, {"process_type": e.process_type, "process_id": e.process_id,
                                    "order_code": _proc_code(db, e.process_type, e.process_id), "inputs": []})
            orders[key]["inputs"].append({"lot_id": e.source_lot_id, "quantity": format(e.source_quantity, "f"),
                                          "unit_code": e.source_unit_code, "into_lot_id": e.target_lot_id})
            if e.source_lot_id not in depth:
                depth[e.source_lot_id] = depth[cur] + 1
                via[e.source_lot_id] = (e.process_type, _proc_code(db, e.process_type, e.process_id))
                q.append(e.source_lot_id)
    nodes = [_node(db, db.get(Lot, i), d, "ORIGIN" if i == target.id else "ANCESTOR", None, via.get(i))
             for i, d in sorted(depth.items(), key=lambda kv: (kv[1], kv[0]))]
    suppliers = {}
    for n in nodes:
        if n.supplier_code:
            suppliers[n.supplier_code] = {"code": n.supplier_code, "name": n.supplier_name}
    return BackwardResult(target_lot_code=target.lot_code, lots=nodes, orders=list(orders.values()),
                          suppliers=list(suppliers.values()))


def graph(db: Session, lot_id: int) -> dict:
    """Web görselleştirme: bağlı lot bileşeni + müşteri düğümleri (kayıtlı sevkiyatlar)."""
    seen = {lot_id}
    q = deque([lot_id])
    edges: list[dict] = []
    while q:
        cur = q.popleft()
        for e in db.scalars(select(LotGenealogyEdge).where(
                (LotGenealogyEdge.source_lot_id == cur) | (LotGenealogyEdge.target_lot_id == cur))):
            edges.append({"id": f"e{e.id}", "source": f"lot:{e.source_lot_id}", "target": f"lot:{e.target_lot_id}",
                          "kind": e.process_type, "quantity": format(e.source_quantity, "f"),
                          "unit_code": e.source_unit_code, "process_code": _proc_code(db, e.process_type, e.process_id)})
            for nxt in (e.source_lot_id, e.target_lot_id):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
    nodes = []
    for lid in sorted(seen):
        n = _node(db, db.get(Lot, lid), 0, "LOT")
        nodes.append({"id": f"lot:{lid}", "type": "LOT", "label": n.lot_code, "product": n.product_name,
                      "on_hand": format(n.on_hand_quantity, "f"), "unit_code": n.unit_code, "is_blocked": n.is_blocked,
                      "is_focus": lid == lot_id})
    customers = {}
    for sl, sh, cu in db.execute(select(ShipmentLine, Shipment, Customer)
                                 .join(Shipment, Shipment.id == ShipmentLine.shipment_id)
                                 .join(Customer, Customer.id == Shipment.customer_id)
                                 .where(ShipmentLine.lot_id.in_(seen), Shipment.status == "SHIPPED")):
        customers[cu.id] = cu.name
        edges.append({"id": f"s{sl.id}", "source": f"lot:{sl.lot_id}", "target": f"customer:{cu.id}", "kind": "SHIPMENT",
                      "quantity": format(sl.quantity, "f"), "unit_code": sl.unit_code, "process_code": sh.shipment_code})
    for cid, name in customers.items():
        nodes.append({"id": f"customer:{cid}", "type": "CUSTOMER", "label": name})
    return {"nodes": nodes, "edges": edges}
