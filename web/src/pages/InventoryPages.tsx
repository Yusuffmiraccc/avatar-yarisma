import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Eye, Plus, RefreshCw, SlidersHorizontal } from 'lucide-react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { apiGet, apiPost } from '../api/client';
import type { components } from '../api/generated';
import type { Page } from '../api/types';
import { qk } from '../lib/queryKeys';
import { invalidateInventoryQueries } from '../lib/invalidate';
import { amountDisplay, dayDisplay, isDecimalNonNegative, isDecimalPositive, moneyDisplay } from '../lib/format';
import { downloadCsv } from '../lib/csv';
import { useAuth } from '../auth';
import { useToast } from '../components/Toast';
import { Button, ConfirmDialog, DataTable, ErrorText, Field, Modal, PageHeader, Panel, SearchBox, StateMessage, StatusBadge } from '../components/UI';

type Lot = components['schemas']['LotOut'];
type Movement = components['schemas']['MovementOut'];
type Product = components['schemas']['ProductOut'];
type Supplier = components['schemas']['SupplierOut'];

const receivedDateKey = (value?: string | null) => value
  ? new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Istanbul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
  : '';

export const receiptSchema = z.object({ lot_code: z.string().trim().min(1, 'Lot kodu zorunludur.'), product_id: z.string().min(1, 'Ürün seçin.'), supplier_id: z.string().optional(), quantity: z.string().refine((value) => isDecimalPositive(value), 'Miktar sıfırdan büyük olmalı.'), unit_code: z.string().min(1), unit_cost: z.string().refine((value) => isDecimalNonNegative(value), 'Birim maliyet geçersiz.'), expiry_date: z.string().optional(), received_at: z.string().optional() });
type ReceiptValues = z.infer<typeof receiptSchema>;

export function PurchasesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [supplier, setSupplier] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const { notify } = useToast();
  const form = useForm<ReceiptValues>({ resolver: zodResolver(receiptSchema), defaultValues: { lot_code: '', product_id: '', supplier_id: '', quantity: '', unit_code: '', unit_cost: '', expiry_date: '', received_at: '' } });
  const lots = useQuery({ queryKey: qk.lots(page, search), queryFn: () => apiGet<Page<Lot>>('/lots', { page, page_size: 20, q: search || undefined }) });
  const products = useQuery({ queryKey: qk.products, queryFn: () => apiGet<Page<Product>>('/products', { page: 1, page_size: 100 }) });
  const suppliers = useQuery({ queryKey: qk.suppliers, queryFn: () => apiGet<Page<Supplier>>('/suppliers', { page: 1, page_size: 100 }) });
  const mutation = useMutation({ mutationFn: (values: ReceiptValues) => apiPost<void>('/lots/receipts', { lot_code: values.lot_code.trim(), product_id: Number(values.product_id), supplier_id: values.supplier_id ? Number(values.supplier_id) : null, quantity: values.quantity, unit_code: values.unit_code, unit_cost: values.unit_cost, expiry_date: values.expiry_date || null, received_at: values.received_at ? new Date(values.received_at).toISOString() : null }), onSuccess: async () => { await invalidateInventoryQueries(queryClient); notify('Lot kabul edildi ve stok defteri güncellendi.'); setShowForm(false); form.reset(); } });
  const filtered = useMemo(() => (lots.data?.items || []).filter((lot) => {
    const receiptDay = receivedDateKey(lot.received_at);
    return (!search || `${lot.lot_code} ${lot.product_name || ''} ${lot.product_code || ''}`.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr')))
      && (!supplier || String(lot.supplier_id ?? '') === supplier)
      && (!dateFrom || (receiptDay !== '' && receiptDay >= dateFrom))
      && (!dateTo || (receiptDay !== '' && receiptDay <= dateTo));
  }), [lots.data, search, supplier, dateFrom, dateTo]);
  const columns = [
    { key: 'lot', title: 'Lot / ürün', render: (lot: Lot) => <span className="cell-stack"><strong>{lot.lot_code}</strong><small>{lot.product_name || lot.product_code || `Ürün #${lot.product_id}`}</small></span> },
    { key: 'supplier', title: 'Tedarikçi', render: (lot: Lot) => suppliers.data?.items.find((item) => item.id === lot.supplier_id)?.name || '—' },
    { key: 'received', title: 'Kabul tarihi', render: (lot: Lot) => dayDisplay(lot.received_at) },
    { key: 'qty', title: 'Kabul miktarı', render: (lot: Lot) => `${amountDisplay(lot.initial_quantity)} ${lot.unit_code}`, align: 'right' as const },
    { key: 'expiry', title: 'Son tüketim', render: (lot: Lot) => dayDisplay(lot.expiry_date) },
    ...(can('costs:read') ? [{ key: 'cost', title: 'Birim maliyet', render: (lot: Lot) => lot.unit_cost == null ? '—' : moneyDisplay(lot.unit_cost), align: 'right' as const }] : []),
    { key: 'status', title: 'Durum', render: (lot: Lot) => <StatusBadge value={lot.is_blocked ? 'BLOCKED' : lot.status} /> },
  ];
  return <>
    <PageHeader eyebrow="TEDARİK & HAMMADDE" title="Alış ve lot kabulü" description="Kabul edilen ham madde lotlarını ve tedarik ilişkilerini yönetin." actions={<Button onClick={() => setShowForm(true)}><Plus size={15} />Lot kabul et</Button>} />
    <Panel title="Alış raporu" subtitle="Lot kabul kayıtlarından oluşturulur; backend’de ayrı bir alış raporu endpoint’i yoktur." actions={<Button variant="secondary" disabled={!filtered.length} onClick={() => downloadCsv('alis-lot-kabulleri.csv', filtered.map((lot) => ({ lot_kodu: lot.lot_code, urun: lot.product_name || lot.product_code, tedarikci: suppliers.data?.items.find((item) => item.id === lot.supplier_id)?.name || '', miktar: lot.initial_quantity, birim: lot.unit_code, kabul_tarihi: lot.received_at || '', son_tuketim: lot.expiry_date || '', ...(can('costs:read') ? { birim_maliyet: lot.unit_cost ?? '' } : {}) })))}><Download size={15} />CSV indir</Button>}>
      <div className="toolbar"><div className="toolbar-left"><SearchBox value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Lot veya ürün ara" /><label className="filter-select"><SlidersHorizontal size={14} /><select aria-label="Tedarikçi filtresi" value={supplier} onChange={(event) => { setSupplier(event.target.value); setPage(1); }}><option value="">Tüm tedarikçiler</option>{suppliers.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="filter-date"><span>Kabul başlangıcı</span><input aria-label="Kabul başlangıç tarihi" type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} /></label><label className="filter-date"><span>Kabul bitişi</span><input aria-label="Kabul bitiş tarihi" type="date" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} /></label></div><div className="toolbar-right"><span className="muted-count">{filtered.length} / {lots.data?.total ?? 0} kayıt</span></div></div>
      <div className="info-box compact-info">Lot kodu araması API filtresini kullanır. Tedarikçi ve kabul tarihi filtreleri API bu filtreleri sunmadığı için yüklenen sayfaya uygulanır.</div>
      {lots.isLoading ? <StateMessage kind="loading" /> : lots.isError ? <StateMessage kind="error" onRetry={() => void lots.refetch()} /> : <DataTable rows={filtered} columns={columns} rowKey={(lot) => lot.id} page={page} pageSize={20} total={lots.data?.total} onPageChange={setPage} emptyText="Bu filtrelerle eşleşen kabul edilmiş lot yok." />}
    </Panel>
    <div className="info-box">Fatura/irsaliye okuma endpoint’i mevcut. Çıkarılan bilgiler taslak olarak incelenmeli ve kullanıcı onayıyla kaydedilmelidir; otomatik kayıt yapılmaz.</div>
    {showForm && <Modal title="Hammadde lotu kabul et" onClose={() => setShowForm(false)}><form onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <div className="field-grid"><Field label="Lot numarası"><input placeholder="ET-2026-001" {...form.register('lot_code')} />{form.formState.errors.lot_code && <small className="field-error">{form.formState.errors.lot_code.message}</small>}</Field>
        <Field label="Ürün"><select className="select" {...form.register('product_id')}><option value="">Ürün seçin</option>{products.data?.items.map((item) => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select>{form.formState.errors.product_id && <small className="field-error">{form.formState.errors.product_id.message}</small>}</Field>
        <Field label="Tedarikçi"><select className="select" {...form.register('supplier_id')}><option value="">Seçilmedi</option>{suppliers.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
        <Field label="Miktar"><input type="text" inputMode="decimal" placeholder="100.000" {...form.register('quantity')} />{form.formState.errors.quantity && <small className="field-error">{form.formState.errors.quantity.message}</small>}</Field>
        <Field label="Birim"><input placeholder="KG" {...form.register('unit_code')} /></Field>
        <Field label="Birim maliyet (€)"><input type="text" inputMode="decimal" placeholder="9.7000" {...form.register('unit_cost')} />{form.formState.errors.unit_cost && <small className="field-error">{form.formState.errors.unit_cost.message}</small>}</Field>
        <Field label="Kabul zamanı"><input type="datetime-local" {...form.register('received_at')} /></Field>
        <Field label="Son tüketim tarihi"><input type="date" {...form.register('expiry_date')} /></Field>
      </div><ErrorText error={mutation.error} />
      <div className="form-actions"><Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Vazgeç</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Kaydediliyor…' : 'Kabul et'}</Button></div>
    </form></Modal>}
  </>;
}

const moveSchema = z.object({ lot_id: z.string().min(1, 'Lot seçin.'), quantity: z.string().refine((value) => isDecimalPositive(value), 'Miktar sıfırdan büyük olmalı.'), to_location: z.string().trim().min(1, 'Hedef depo/konum gerekli.') });
const adjustSchema = z.object({ lot_id: z.string().min(1, 'Lot seçin.'), direction: z.enum(['IN', 'OUT']), quantity: z.string().refine((value) => isDecimalPositive(value), 'Miktar sıfırdan büyük olmalı.') });

export function InventoryPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [blocked, setBlocked] = useState('');
  const [selectedLotId, setSelectedLotId] = useState<number | null>(null);
  const [modal, setModal] = useState<'transfer' | 'adjust' | null>(null);
  const [confirm, setConfirm] = useState<{ kind: 'transfer' | 'adjust'; values: z.infer<typeof moveSchema> | z.infer<typeof adjustSchema> } | null>(null);
  const [reason, setReason] = useState('');
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const { notify } = useToast();
  const lots = useQuery({ queryKey: qk.lots(page, search), queryFn: () => apiGet<Page<Lot>>('/lots', { page, page_size: 20, q: search || undefined }) });
  const movements = useQuery({ queryKey: qk.movements(1), queryFn: () => apiGet<Page<Movement>>('/inventory/movements', { page: 1, page_size: 100 }) });
  const detail = useQuery({ queryKey: ['lot-detail', selectedLotId], queryFn: () => apiGet<Lot>(`/lots/${selectedLotId}`), enabled: selectedLotId != null });
  const transferForm = useForm<z.infer<typeof moveSchema>>({ resolver: zodResolver(moveSchema), defaultValues: { lot_id: '', quantity: '', to_location: '' } });
  const adjustForm = useForm<z.infer<typeof adjustSchema>>({ resolver: zodResolver(adjustSchema), defaultValues: { lot_id: '', direction: 'OUT', quantity: '' } });
  const movementMutation = useMutation({ mutationFn: async (payload: { kind: 'transfer' | 'adjust'; body: Record<string, unknown> }) => payload.kind === 'transfer' ? apiPost<void>('/inventory/transfers', payload.body) : apiPost<void>('/inventory/adjustments', payload.body), onSuccess: async () => { await invalidateInventoryQueries(queryClient); notify('Stok defteri güncellendi.'); setModal(null); setConfirm(null); setReason(''); } });
  const unblockMutation = useMutation({ mutationFn: ({ lotId, reasonText }: { lotId: number; reasonText: string }) => apiPost<Lot>(`/lots/${lotId}/unblock`, { reason: reasonText }), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['lots'] }), queryClient.invalidateQueries({ queryKey: ['lot-detail'] }), queryClient.invalidateQueries({ queryKey: ['movements'] })]); notify('Lot blokajı kaldırıldı ve denetlendi.'); setSelectedLotId(null); } });
  const visibleLots = useMemo(() => (lots.data?.items || []).filter((lot) => (!search || `${lot.lot_code} ${lot.product_name || ''} ${lot.product_code || ''}`.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr'))) && (blocked === '' || String(lot.is_blocked) === blocked)), [lots.data, search, blocked]);
  const selected = detail.data;
  const openConfirm = (kind: 'transfer' | 'adjust', values: z.infer<typeof moveSchema> | z.infer<typeof adjustSchema>) => { setConfirm({ kind, values }); setReason(''); };
  const columns = [
    { key: 'code', title: 'Lot kodu', render: (lot: Lot) => <button className="table-link" onClick={() => setSelectedLotId(lot.id)}><strong>{lot.lot_code}</strong><small>{lot.product_name || lot.product_code}</small></button> },
    { key: 'balance', title: 'Bakiye', render: (lot: Lot) => `${amountDisplay(lot.on_hand_quantity)} ${lot.unit_code}`, align: 'right' as const },
    { key: 'location', title: 'Konum', render: (lot: Lot) => lot.location_code || '—' },
    { key: 'expiry', title: 'Son tüketim', render: (lot: Lot) => dayDisplay(lot.expiry_date) },
    ...(can('costs:read') ? [{ key: 'cost', title: 'Birim maliyet', render: (lot: Lot) => lot.unit_cost == null ? '—' : moneyDisplay(lot.unit_cost), align: 'right' as const }] : []),
    { key: 'status', title: 'Durum', render: (lot: Lot) => <StatusBadge value={lot.is_blocked ? 'BLOCKED' : lot.status} /> },
    { key: 'actions', title: '', render: (lot: Lot) => <Button variant="quiet" aria-label={`${lot.lot_code} detayını aç`} onClick={() => setSelectedLotId(lot.id)}><Eye size={15} /></Button> },
  ];
  return <>
    <PageHeader eyebrow="STOK DEFTERİ" title="Lot ve stok yönetimi" description="Lot bakiyeleri, blokaj durumu ve kayıtlı stok hareketleri." actions={<>
      {can('inventory:adjust') && <Button variant="secondary" onClick={() => setModal('transfer')}><RefreshCw size={15} />Depo transferi</Button>}{can('inventory:adjust') && <Button onClick={() => setModal('adjust')}><Plus size={15} />Stok düzelt</Button>}
    </>} />
    <Panel title="Lot bakiyeleri" subtitle="Giriş ve çıkışlar her zaman lot bazında izlenir." actions={<Button variant="secondary" disabled={!visibleLots.length} onClick={() => downloadCsv('lot-stok-bakiyeleri.csv', visibleLots.map((lot) => ({ lot_kodu: lot.lot_code, urun: lot.product_name || lot.product_code, bakiye: lot.on_hand_quantity, birim: lot.unit_code, konum: lot.location_code, bloke: lot.is_blocked, ...(can('costs:read') ? { birim_maliyet: lot.unit_cost ?? '' } : {}) })))}><Download size={15} />CSV indir</Button>}>
      <div className="toolbar"><SearchBox value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Lot veya ürün ara" /><select className="select status-filter" aria-label="Bloke filtresi" value={blocked} onChange={(event) => setBlocked(event.target.value)}><option value="">Tüm durumlar</option><option value="true">Bloke</option><option value="false">Bloke değil</option></select></div>
      {lots.isLoading ? <StateMessage kind="loading" /> : lots.isError ? <StateMessage kind="error" onRetry={() => void lots.refetch()} /> : <DataTable rows={visibleLots} columns={columns} rowKey={(lot) => lot.id} page={page} pageSize={20} total={lots.data?.total} onPageChange={setPage} />}
    </Panel>
    <Panel title="Stok hareketleri" subtitle="Append-only stok defteri · OUT yalnızca sevkiyat/dispatch ile oluşur." actions={<Button variant="secondary" onClick={() => void movements.refetch()}><RefreshCw size={14} />Yenile</Button>}>
      {movements.isLoading ? <StateMessage kind="loading" /> : movements.isError ? <StateMessage kind="error" onRetry={() => void movements.refetch()} /> : <DataTable rows={movements.data?.items || []} rowKey={(row) => row.id} columns={[
        { key: 'date', title: 'Tarih', render: (row) => dayDisplay(row.occurred_at) },
        { key: 'lot', title: 'Lot', render: (row) => <strong>{row.lot_code || `#${row.lot_id}`}</strong> },
        { key: 'direction', title: 'Yön', render: (row) => <StatusBadge value={row.direction} /> },
        { key: 'type', title: 'Hareket', render: (row) => row.movement_type.replaceAll('_', ' ') },
        { key: 'qty', title: 'Miktar', render: (row) => `${amountDisplay(row.quantity)} ${row.unit_code}`, align: 'right' },
        { key: 'source', title: 'Kaynak', render: (row) => `${row.source_type} · ${row.source_id}` },
        { key: 'location', title: 'Konum', render: (row) => row.location_code || '—' },
      ]} />}
    </Panel>
    {selectedLotId != null && <Modal title={selected ? selected.lot_code : 'Lot detayı'} onClose={() => setSelectedLotId(null)}>{detail.isLoading ? <StateMessage kind="loading" /> : detail.isError ? <StateMessage kind="error" onRetry={() => void detail.refetch()} /> : selected && <>
      <div className="detail-grid"><div className="detail-item"><span>Ürün</span><strong>{selected.product_name || selected.product_code || `#${selected.product_id}`}</strong></div><div className="detail-item"><span>Başlangıç miktarı</span><strong>{amountDisplay(selected.initial_quantity)} {selected.unit_code}</strong></div><div className="detail-item"><span>Mevcut bakiye</span><strong>{amountDisplay(selected.on_hand_quantity)} {selected.unit_code}</strong></div><div className="detail-item"><span>Durum</span><strong><StatusBadge value={selected.is_blocked ? 'BLOCKED' : selected.status} /></strong></div><div className="detail-item"><span>Son tüketim</span><strong>{dayDisplay(selected.expiry_date)}</strong></div><div className="detail-item"><span>Konum</span><strong>{selected.location_code}</strong></div>{can('costs:read') && <div className="detail-item"><span>Birim maliyet</span><strong>{selected.unit_cost == null ? '—' : moneyDisplay(selected.unit_cost)}</strong></div>}</div>
      {selected.is_blocked && <div className="danger-box modal-note">Bu lot bloke. Satış ve sevkiyat backend tarafından reddedilmelidir.</div>}
      {selected.is_blocked && can('lots:unblock') && <div className="unblock-inline"><Field label="Blokajı kaldırma gerekçesi"><input minLength={5} placeholder="En az 5 karakter" value={reason} onChange={(event) => setReason(event.target.value)} /></Field><Button variant="danger" disabled={reason.trim().length < 5 || unblockMutation.isPending} onClick={() => void unblockMutation.mutateAsync({ lotId: selected.id, reasonText: reason.trim() }).catch(() => undefined)}>Gerekçeyle blokajı kaldır</Button><ErrorText error={unblockMutation.error} /></div>}
      <Panel title="Bu lotun defter satırları" className="nested-panel">{(movements.data?.items || []).filter((row) => row.lot_id === selected.id).length ? <DataTable rows={(movements.data?.items || []).filter((row) => row.lot_id === selected.id)} rowKey={(row) => row.id} columns={[{ key: 'date', title: 'Tarih', render: (row) => dayDisplay(row.occurred_at) }, { key: 'direction', title: 'Yön', render: (row) => row.direction }, { key: 'type', title: 'Hareket', render: (row) => row.movement_type }, { key: 'qty', title: 'Miktar', render: (row) => `${amountDisplay(row.quantity)} ${row.unit_code}` }]} /> : <StateMessage kind="empty" message="Bu lot için mevcut sayfada hareket yok." />}</Panel>
    </>}</Modal>}
    {modal === 'transfer' && <Modal title="Depo transferi" onClose={() => setModal(null)}><form onSubmit={transferForm.handleSubmit((values) => openConfirm('transfer', values))}><Field label="Lot"><select className="select" {...transferForm.register('lot_id')}><option value="">Lot seçin</option>{lots.data?.items.map((lot) => <option key={lot.id} value={lot.id}>{lot.lot_code} · {amountDisplay(lot.on_hand_quantity)} {lot.unit_code}</option>)}</select></Field><Field label="Miktar"><input inputMode="decimal" {...transferForm.register('quantity')} /></Field><Field label="Hedef konum"><input placeholder="DEPO-2" {...transferForm.register('to_location')} /></Field><div className="form-actions"><Button variant="secondary" type="button" onClick={() => setModal(null)}>Vazgeç</Button><Button type="submit">Devam et</Button></div></form></Modal>}
    {modal === 'adjust' && <Modal title="Gerekçeli stok düzeltmesi" onClose={() => setModal(null)}><form onSubmit={adjustForm.handleSubmit((values) => openConfirm('adjust', values))}><Field label="Lot"><select className="select" {...adjustForm.register('lot_id')}><option value="">Lot seçin</option>{lots.data?.items.map((lot) => <option key={lot.id} value={lot.id}>{lot.lot_code} · {amountDisplay(lot.on_hand_quantity)} {lot.unit_code}</option>)}</select></Field><Field label="Yön"><select className="select" {...adjustForm.register('direction')}><option value="OUT">Çıkış düzeltmesi</option><option value="IN">Giriş düzeltmesi</option></select></Field><Field label="Miktar"><input inputMode="decimal" {...adjustForm.register('quantity')} /></Field><div className="warning-box">Düzeltme stok defterine yeni bir hareket ekler; mevcut bakiye doğrudan değiştirilmez.</div><div className="form-actions"><Button variant="secondary" type="button" onClick={() => setModal(null)}>Vazgeç</Button><Button type="submit">Devam et</Button></div></form></Modal>}
    {confirm && <ConfirmDialog title={confirm.kind === 'adjust' ? 'Stok düzeltmesini onayla' : 'Depo transferini onayla'} description="Bu işlem stok defterine kaydedilecek ve audit kaydı oluşturulacaktır." confirmLabel="İşlemi kaydet" destructive={confirm.kind === 'adjust'} requireReason reasonLabel="İşlem gerekçesi" busy={movementMutation.isPending} onClose={() => setConfirm(null)} onConfirm={async (why) => { setReason(why); const values = confirm.values; await movementMutation.mutateAsync({ kind: confirm.kind, body: confirm.kind === 'transfer' ? { ...values, lot_id: Number(values.lot_id), reason: why } : { ...values, lot_id: Number(values.lot_id), reason: why, movement_type: 'ADJUSTMENT' } }); }} />}
  </>;
}



