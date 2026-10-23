"""İleri/geri izleme: yalnızca kayıtlı genealogy ve sevkiyat satırlarına dayanır (AI/tahmin yok)."""

from collections import defaultdict
from decimal import Decimal

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import (
    ButcheringOrder,
    Customer,
    InventoryBalance,
    Lot,
    LotBlock,
    LotGenealogyEdge,
    Product,
    ProductionOrder,
    ReworkOrder,
    Shipment,
    ShipmentLine,
    Supplier,
)
from app.schemas.common import ApiModel, Dec
from app.services import costing, stock

ZERO = Decimal(0)
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
    second_tier: list = Field(default_factory=list)
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
    return _node_loaded(lot, depth, role, prod, bal, sup, stock.active_block(db, lot.id) is not None, share, via)


def _node_loaded(lot, depth, role, prod, bal, sup, blocked, share=None, via=None) -> LotNode:
    return LotNode(lot_id=lot.id, lot_code=lot.lot_code, product_code=prod.code, product_name=prod.name, depth=depth,
                   role=role, unit_code=lot.unit_code, produced_quantity=lot.initial_quantity,
                   on_hand_quantity=bal.on_hand_quantity if bal else ZERO, origin_share=share,
                   is_blocked=blocked,
                   via_process_type=via[0] if via else None, via_process_code=via[1] if via else None,
                   supplier_code=sup.code if sup else None, supplier_name=sup.name if sup else None)


def _process_codes(db: Session, edges: list[LotGenealogyEdge]) -> dict[tuple[str, int], str | None]:
    models = {"PRODUCTION": ProductionOrder, "BUTCHERING": ButcheringOrder, "REWORK": ReworkOrder}
    ids_by_type: dict[str, set[int]] = defaultdict(set)
    for edge in edges:
        if edge.process_type in models:
            ids_by_type[edge.process_type].add(edge.process_id)
    result = {}
    for process_type, ids in ids_by_type.items():
        model = models[process_type]
        for row in db.scalars(select(model).where(model.id.in_(ids))):
            result[(process_type, row.id)] = row.order_code
    return result


def forward(db: Session, origin_ids: list[int]) -> ForwardResult:
    unique_origin_ids = set(origin_ids)
    lot_map = {lot.id: lot for lot in db.scalars(select(Lot).where(Lot.id.in_(unique_origin_ids)))}
    origins = [lot_map.get(i) or _lot(db, i) for i in origin_ids]
    depth: dict[int, int] = {o.id: 0 for o in origins}
    via: dict[int, tuple[str, str | None]] = {}
    edges_into: dict[int, list[LotGenealogyEdge]] = defaultdict(list)
    frontier = list(depth)
    while frontier:
        wave_edges = list(db.scalars(select(LotGenealogyEdge).where(
            LotGenealogyEdge.source_lot_id.in_(frontier)).order_by(LotGenealogyEdge.id)))
        newly_reached = []
        new_edges = []
        for e in wave_edges:
            edges_into[e.target_lot_id].append(e)
            if e.target_lot_id not in depth:  # ziyaret kümesi: döngü koruması
                depth[e.target_lot_id] = depth[e.source_lot_id] + 1
                newly_reached.append(e.target_lot_id)
                new_edges.append(e)
        process_codes = _process_codes(db, new_edges)
        for edge in new_edges:
            via[edge.target_lot_id] = (edge.process_type, process_codes.get((edge.process_type, edge.process_id)))
        frontier = newly_reached

    visited_ids = set(depth)
    if visited_ids - lot_map.keys():
        lot_map.update({lot.id: lot for lot in db.scalars(select(Lot).where(Lot.id.in_(visited_ids - lot_map.keys())))})

    share: dict[int, Decimal] = {o.id: Decimal(1) for o in origins}

    def share_of(lot_id: int, seen=frozenset()) -> Decimal:
        if lot_id in share:
            return share[lot_id]
        lot = lot_map[lot_id]
        total = lot.initial_quantity or Decimal(1)
        acc = ZERO
        for e in edges_into[lot_id]:
            if e.source_lot_id in seen or e.source_lot_id not in depth:
                continue
            acc += share_of(e.source_lot_id, seen | {lot_id}) * e.target_quantity
        share[lot_id] = min(costing.q6(acc / total), Decimal(1))
        return share[lot_id]

    product_ids = {lot.product_id for lot in lot_map.values()}
    supplier_ids = {lot.supplier_id for lot in lot_map.values() if lot.supplier_id is not None}
    products = {row.id: row for row in db.scalars(select(Product).where(Product.id.in_(product_ids)))} if product_ids else {}
    balances = {row.lot_id: row for row in db.scalars(select(InventoryBalance).where(
        InventoryBalance.lot_id.in_(visited_ids)))} if visited_ids else {}
    suppliers = {row.id: row for row in db.scalars(select(Supplier).where(Supplier.id.in_(supplier_ids)))} if supplier_ids else {}
    blocked_ids = set(db.scalars(select(LotBlock.lot_id).where(
        LotBlock.lot_id.in_(visited_ids), LotBlock.unblocked_at.is_(None)))) if visited_ids else set()
    nodes: list[LotNode] = []
    for lid in sorted(depth, key=lambda i: (depth[i], i)):
        lot = lot_map[lid]
        nodes.append(_node_loaded(lot, depth[lid], "ORIGIN" if lid in unique_origin_ids else "DERIVED",
                                  products[lot.product_id], balances.get(lid), suppliers.get(lot.supplier_id),
                                  lid in blocked_ids, share_of(lid), via.get(lid)))

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
    edges = []
    frontier = [target.id]
    while frontier:
        rows = db.scalars(select(LotGenealogyEdge).where(LotGenealogyEdge.target_lot_id.in_(frontier))
                          .order_by(LotGenealogyEdge.id)).all()
        edges.extend(rows)
        next_frontier = []
        for edge in rows:
            if edge.source_lot_id not in depth:
                depth[edge.source_lot_id] = depth[edge.target_lot_id] + 1
                next_frontier.append(edge.source_lot_id)
        frontier = next_frontier
    codes = _process_codes(db, edges)
    orders: dict[tuple[str, int], dict] = {}
    for edge in edges:
        key = (edge.process_type, edge.process_id)
        orders.setdefault(key, {"process_type": edge.process_type, "process_id": edge.process_id,
                                "order_code": codes.get(key), "inputs": []})
        orders[key]["inputs"].append({"lot_id": edge.source_lot_id, "quantity": format(edge.source_quantity, "f"),
                                      "unit_code": edge.source_unit_code, "into_lot_id": edge.target_lot_id})
        if edge.source_lot_id != target.id:
            via[edge.source_lot_id] = (edge.process_type, codes.get(key))
    lot_map = {row.id: row for row in db.scalars(select(Lot).where(Lot.id.in_(depth)))}
    product_ids = {lot.product_id for lot in lot_map.values()}
    supplier_ids = {lot.supplier_id for lot in lot_map.values() if lot.supplier_id is not None}
    products = {row.id: row for row in db.scalars(select(Product).where(Product.id.in_(product_ids)))} if product_ids else {}
    balances = {row.lot_id: row for row in db.scalars(select(InventoryBalance).where(InventoryBalance.lot_id.in_(depth)))}
    suppliers = {row.id: row for row in db.scalars(select(Supplier).where(Supplier.id.in_(supplier_ids)))} if supplier_ids else {}
    blocked = set(db.scalars(select(LotBlock.lot_id).where(LotBlock.lot_id.in_(depth), LotBlock.unblocked_at.is_(None))))
    nodes = [_node_loaded(lot_map[i], depth[i], "ORIGIN" if i == target.id else "ANCESTOR",
                          products[lot_map[i].product_id], balances.get(i), suppliers.get(lot_map[i].supplier_id),
                          i in blocked, None, via.get(i)) for i in sorted(depth, key=lambda x: (depth[x], x))]
    suppliers = {}
    for n in nodes:
        if n.supplier_code:
            suppliers[n.supplier_code] = {"code": n.supplier_code, "name": n.supplier_name}
    return BackwardResult(target_lot_code=target.lot_code, lots=nodes, orders=list(orders.values()),
                          suppliers=list(suppliers.values()))


def graph(db: Session, lot_id: int) -> dict:
    """Web görselleştirme: bağlı lot bileşeni + müşteri düğümleri (kayıtlı sevkiyatlar)."""
    seen = {lot_id}
    frontier = {lot_id}
    edge_map = {}
    while frontier:
        rows = db.scalars(select(LotGenealogyEdge).where(
            LotGenealogyEdge.source_lot_id.in_(frontier) | LotGenealogyEdge.target_lot_id.in_(frontier))
            .order_by(LotGenealogyEdge.id)).all()
        next_frontier = set()
        for edge in rows:
            edge_map[edge.id] = edge
            for nxt in (edge.source_lot_id, edge.target_lot_id):
                if nxt not in seen:
                    seen.add(nxt)
                    next_frontier.add(nxt)
        frontier = next_frontier
    genes = list(edge_map.values())
    process_codes = _process_codes(db, genes)
    edges = [{"id": f"e{edge.id}", "source": f"lot:{edge.source_lot_id}", "target": f"lot:{edge.target_lot_id}",
              "kind": edge.process_type, "quantity": format(edge.source_quantity, "f"),
              "unit_code": edge.source_unit_code, "process_code": process_codes.get((edge.process_type, edge.process_id))}
             for edge in genes]
    lot_map = {row.id: row for row in db.scalars(select(Lot).where(Lot.id.in_(seen)))}
    products = {row.id: row for row in db.scalars(select(Product).where(
        Product.id.in_({lot.product_id for lot in lot_map.values()})))}
    balances = {row.lot_id: row for row in db.scalars(select(InventoryBalance).where(InventoryBalance.lot_id.in_(seen)))}
    blocked = set(db.scalars(select(LotBlock.lot_id).where(LotBlock.lot_id.in_(seen), LotBlock.unblocked_at.is_(None))))
    nodes = [{"id": f"lot:{lid}", "type": "LOT", "label": lot_map[lid].lot_code,
              "product": products[lot_map[lid].product_id].name,
              "on_hand": format(balances[lid].on_hand_quantity, "f") if lid in balances else "0",
              "unit_code": lot_map[lid].unit_code, "is_blocked": lid in blocked, "is_focus": lid == lot_id}
             for lid in sorted(seen)]
    shipment_rows = db.execute(select(ShipmentLine, Shipment, Customer)
                               .join(Shipment, Shipment.id == ShipmentLine.shipment_id)
                               .join(Customer, Customer.id == Shipment.customer_id)
                               .where(ShipmentLine.lot_id.in_(seen), Shipment.status == "SHIPPED"))
    customers = {}
    for sl, sh, cu in shipment_rows:
        customers[cu.id] = cu.name
        edges.append({"id": f"s{sl.id}", "source": f"lot:{sl.lot_id}", "target": f"customer:{cu.id}", "kind": "SHIPMENT",
                      "quantity": format(sl.quantity, "f"), "unit_code": sl.unit_code, "process_code": sh.shipment_code})
    for cid, name in customers.items():
        nodes.append({"id": f"customer:{cid}", "type": "CUSTOMER", "label": name})
    return {"nodes": nodes, "edges": edges}
