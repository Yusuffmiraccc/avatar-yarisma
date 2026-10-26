import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDownLeft, ArrowUpRight, Download, Search } from 'lucide-react';
import type { components } from '../api/generated';
import { apiGet } from '../api/client';
type ForwardResult = components['schemas']['ForwardResult'];
type BackwardResult = components['schemas']['BackwardResult'];
import { amountDisplay } from '../lib/format';
import { downloadCsv } from '../lib/csv';
import { Button, DataTable, Field, PageHeader, Panel, StateMessage, StatusBadge } from '../components/UI';

type LotNode = components['schemas']['LotNode'];
type ShipmentHit = components['schemas']['ShipmentHit'];

export function TraceabilityPage() {
  const [draftCode, setDraftCode] = useState('ET-2026-001');
  const [code, setCode] = useState('ET-2026-001');
  const forward = useQuery({ queryKey: ['trace-forward', code], queryFn: () => apiGet<ForwardResult>(`/traceability/lots/by-code/${encodeURIComponent(code)}/forward`), enabled: Boolean(code) });
  const backward = useQuery({ queryKey: ['trace-backward', code], queryFn: () => apiGet<BackwardResult>(`/traceability/lots/by-code/${encodeURIComponent(code)}/backward`), enabled: Boolean(code) });
  const exportRows = (forward.data?.shipments || []).map((shipment) => ({ lot_kodu: shipment.lot_code, urun: shipment.lot_id, sevkiyat: shipment.shipment_code, market: shipment.customer_name, market_kodu: shipment.customer_code, miktar: shipment.quantity, birim: shipment.unit_code, sevk_tarihi: shipment.shipped_at || '' }));
  return <>
    <PageHeader eyebrow="LOT GENEALOGY" title="Lot izlenebilirliği" description="Hammadde lotundan sevkiyata ileri; mamul lotundan tedarikçiye geri izleme." actions={<Button variant="secondary" disabled={!exportRows.length} onClick={() => downloadCsv('lot-izlenebilirligi.csv', exportRows)}><Download size={14} />İleri iz CSV</Button>} />
    <Panel title="Lot koduyla ara" subtitle="Sonraki dağıtım yalnızca backend’de kayıtlıysa gösterilir."><form className="trace-search" onSubmit={(event) => { event.preventDefault(); setCode(draftCode.trim()); }}><Field label="Lot kodu"><input value={draftCode} onChange={(event) => setDraftCode(event.target.value)} placeholder="ET-2026-001" /></Field><Button type="submit"><Search size={15} />İzini sür</Button></form></Panel>
    <div className="trace-overview">
      <Panel title="İleri izleme" subtitle="Hammadde → üretim → mamul lotları → sevkiyat → kayıtlı marketler">
        {forward.isLoading ? <StateMessage kind="loading" /> : forward.isError ? <StateMessage kind="error" onRetry={() => void forward.refetch()} /> : forward.data && <>
          <div className="trace-flow"><div className="trace-node trace-origin"><span>GİRİŞ LOTU</span><strong>{forward.data.origin_lot_codes.join(', ') || code}</strong></div><ArrowUpRight size={19} /><div className="trace-node"><span>ETKİLENEN LOTLAR</span><strong>{forward.data.lots.length}</strong></div><ArrowUpRight size={19} /><div className="trace-node"><span>SEVKİYAT SATIRLARI</span><strong>{forward.data.shipments.length}</strong></div><ArrowUpRight size={19} /><div className="trace-node"><span>KAYITLI MARKETLER</span><strong>{forward.data.customers.length}</strong></div></div>
          <div className="detail-grid trace-stats"><div className="detail-item"><span>Kalan stok toplamı</span><strong>{amountDisplay(forward.data.remaining_stock_total)}</strong></div><div className="detail-item"><span>İzlenen lot</span><strong>{code}</strong></div><div className="detail-item"><span>İkinci kademe</span><strong>{forward.data.second_tier?.length ? `${forward.data.second_tier.length} kayıt` : 'Kayıt yok'}</strong></div></div>
          <Panel title="Lot ilişkileri" className="nested-panel"><DataTable rows={forward.data.lots as LotNode[]} rowKey={(lot) => lot.lot_id} columns={[{ key: 'lot', title: 'Lot', render: (lot) => <span className="cell-stack"><strong>{lot.lot_code}</strong><small>{lot.product_code} · {lot.product_name}</small></span> }, { key: 'role', title: 'İlişki', render: (lot) => lot.role.replaceAll('_', ' ') }, { key: 'process', title: 'Süreç', render: (lot) => lot.via_process_code ? `${lot.via_process_code} · ${lot.via_process_type}` : '—' }, { key: 'produced', title: 'Üretilen', render: (lot) => `${amountDisplay(lot.produced_quantity)} ${lot.unit_code}`, align: 'right' }, { key: 'stock', title: 'Kalan', render: (lot) => `${amountDisplay(lot.on_hand_quantity)} ${lot.unit_code}`, align: 'right' }, { key: 'blocked', title: 'Durum', render: (lot) => <StatusBadge value={lot.is_blocked ? 'BLOCKED' : 'ACTIVE'} /> }]} emptyText="Kayıtlı ileri lot ilişkisi bulunamadı." /></Panel>
          <Panel title="Sevkiyatlar ve marketler" className="nested-panel"><DataTable rows={forward.data.shipments as ShipmentHit[]} rowKey={(row) => `${row.shipment_id}-${row.lot_id}-${row.customer_id}`} columns={[{ key: 'lot', title: 'Lot', render: (row) => <strong>{row.lot_code}</strong> }, { key: 'shipment', title: 'Sevkiyat', render: (row) => row.shipment_code }, { key: 'market', title: 'Market', render: (row) => <span className="cell-stack"><strong>{row.customer_name}</strong><small>{row.customer_code}</small></span> }, { key: 'qty', title: 'Miktar', render: (row) => `${amountDisplay(row.quantity)} ${row.unit_code}`, align: 'right' }, { key: 'date', title: 'Sevk tarihi', render: (row) => row.shipped_at ? new Date(row.shipped_at).toLocaleDateString('tr-TR', { timeZone: 'Europe/Istanbul' }) : '—' }]} emptyText="Kayıtlı sevkiyat bulunamadı." /></Panel>
          <div className="info-box">{forward.data.second_tier_note || 'Kayıtlı olmayan sonraki dağıtımlar tahmin edilmez.'}</div>
        </>}
      </Panel>
      <Panel title="Geriye izleme" subtitle="Mamul lotu → hammadde lotları → tedarikçiler ve üretim"><div className="trace-reverse"><ArrowDownLeft size={20} /><span>Aranan lot</span><strong>{backward.data?.target_lot_code || code}</strong></div>
        {backward.isLoading ? <StateMessage kind="loading" /> : backward.isError ? <StateMessage kind="error" onRetry={() => void backward.refetch()} /> : backward.data && <>
          <div className="data-list">{backward.data.lots.map((lot) => <div className="data-list-row" key={lot.lot_id}><span><strong>{lot.lot_code}</strong><small>{lot.product_name} · {lot.role}</small></span><span>{amountDisplay(lot.produced_quantity)} {lot.unit_code}</span></div>)}</div>
          <h3 className="small-heading">Üretim / parçalama emirleri</h3>{backward.data.orders.length ? <div className="data-list">{backward.data.orders.map((order, index) => <div className="data-list-row" key={index}><strong>{String(order.order_code || order.code || order.id || 'İşlem')}</strong><span>{String(order.process_type || order.type || '')}</span></div>)}</div> : <div className="quiet-empty">Kayıtlı emir ilişkisi yok.</div>}
          <h3 className="small-heading">Tedarikçiler</h3>{backward.data.suppliers.length ? <div className="data-list">{backward.data.suppliers.map((supplier, index) => <div className="data-list-row" key={index}><strong>{String(supplier.name || supplier.supplier_name || 'Tedarikçi')}</strong><span>{String(supplier.code || supplier.supplier_code || '')}</span></div>)}</div> : <div className="quiet-empty">Kayıtlı tedarikçi ilişkisi yok.</div>}
        </>}
      </Panel>
    </div>
  </>;
}


