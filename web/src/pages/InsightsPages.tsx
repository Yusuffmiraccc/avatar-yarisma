import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Download, RefreshCw, Sparkles } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { components } from '../api/generated';
import { apiGet, apiPost } from '../api/client';
import type { CostRow, LedgerIntegrity, ModelSummary, Page, Valuation } from '../api/types';
import { qk } from '../lib/queryKeys';
import { amountDisplay, dateDisplay, decimal, moneyDisplay } from '../lib/format';
import { downloadCsv } from '../lib/csv';
import { visibleCostFields } from '../lib/permissions';
import { useAuth } from '../auth';
import { useToast } from '../components/Toast';
import { Button, DataTable, ErrorText, Field, PageHeader, Panel, SearchBox, StateMessage, StatusBadge } from '../components/UI';

type Lot = components['schemas']['LotOut'];
type Movement = components['schemas']['MovementOut'];
type Sale = components['schemas']['SaleOut'];
type Shipment = components['schemas']['ShipmentOut'];
type Recall = components['schemas']['RecallOut'];
type Butchering = components['schemas']['ButcheringOrderOut'];
type Prediction = components['schemas']['PredictionOut'];
type Alert = components['schemas']['AlertOut'];

type Tab = 'purchases' | 'production' | 'butchering' | 'movements' | 'sales' | 'recalls' | 'valuation' | 'ledger';
const tabs: Array<{ id: Tab; label: string }> = [
  { id: 'purchases', label: 'Alış' }, { id: 'production', label: 'Üretim & maliyet' }, { id: 'butchering', label: 'Parçalama' },
  { id: 'movements', label: 'Lot hareketleri' }, { id: 'sales', label: 'Satış & sevkiyat' }, { id: 'recalls', label: 'Geri çağırma' },
  { id: 'valuation', label: 'Stok değerleme' }, { id: 'ledger', label: 'Defter bütünlüğü' },
];
type ReportRow = Record<string, unknown>;
const fieldLabels: Record<string, string> = { lot_code: 'Lot', lot: 'Lot', product_name: 'Ürün', product_code: 'Ürün kodu', supplier_name: 'Tedarikçi', customer_name: 'Market', order_code: 'Emir', shipment_code: 'Sevkiyat', sale_code: 'Satış', recall_code: 'Geri çağırma', status: 'Durum', direction: 'Yön', movement_type: 'Hareket', quantity: 'Miktar', unit_code: 'Birim', occurred_at: 'Tarih', received_at: 'Kabul tarihi', shipped_at: 'Sevk tarihi', created_at: 'Oluşturulma', expiry_date: 'Son tüketim', total_cost: 'Toplam maliyet', total_input_cost: 'Hammadde maliyeti', total_service_cost: 'Hizmet maliyeti', ekp: 'EKP', ekp_display: 'EKP', vkp: 'VKP', gross_profit_per_unit: 'Brüt kâr / birim', margin_percent: 'Marj', output_quantity: 'Üretim miktarı', actual_output_quantity: 'Gerçek üretim', planned_quantity: 'Planlanan miktar', total_amount: 'Toplam', stock_movement_id: 'Stok hareketi', value: 'Stok değeri', on_hand: 'Bakiye', product_type: 'Ürün türü', animal_type: 'Hayvan türü', input_weight: 'Giriş ağırlığı', allocated_total: 'Dağıtılan maliyet', total_purchase_cost: 'Alış maliyeti', consistent: 'Tutarlı', id: 'Kayıt no', reason_code: 'Neden', severity: 'Önem', message: 'Mesaj' };
const isCostKey = (key: string) => /(cost|ekp|vkp|margin|profit|value|price)/i.test(key);

function reportRows(tab: Tab, data: unknown): ReportRow[] {
  if (tab === 'ledger') return (data as LedgerIntegrity | undefined)?.mismatches || [];
  const candidate = data as { items?: unknown[] } | unknown[] | undefined;
  if (Array.isArray(candidate)) return candidate as ReportRow[];
  return Array.isArray(candidate?.items) ? candidate.items as ReportRow[] : [];
}
function cellValue(key: string, value: unknown, canReadCosts: boolean) {
  if (value == null || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Evet' : 'Hayır';
  if (key === 'status' || key === 'severity' || key === 'direction') return <StatusBadge value={String(value)} />;
  if (typeof value === 'string' && /(date|_at)$/.test(key)) return dateDisplay(value);
  if (isCostKey(key) && canReadCosts && typeof value === 'string') return moneyDisplay(value);
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function ReportsPage() {
  const [tab, setTab] = useState<Tab>('purchases');
  const [search, setSearch] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const { can } = useAuth();
  const purchases = useQuery({ queryKey: ['report', 'purchases'], queryFn: () => apiGet<Page<Lot>>('/lots', { page: 1, page_size: 100 }), enabled: tab === 'purchases' });
  const production = useQuery({ queryKey: qk.productionCosts, queryFn: () => apiGet<{ items: CostRow[] }>('/reports/production-costs'), enabled: tab === 'production' });
  const butchering = useQuery({ queryKey: ['report', 'butchering'], queryFn: () => apiGet<Page<Butchering>>('/butchering-orders', { page: 1, page_size: 100 }), enabled: tab === 'butchering' });
  const movements = useQuery({ queryKey: ['report', 'movements'], queryFn: () => apiGet<Page<Movement>>('/inventory/movements', { page: 1, page_size: 100 }), enabled: tab === 'movements' });
  const sales = useQuery({ queryKey: ['report', 'sales'], queryFn: async () => { const [saleRows, shipRows] = await Promise.all([apiGet<Page<Sale>>('/sales', { page: 1, page_size: 100 }), apiGet<Page<Shipment>>('/shipments', { page: 1, page_size: 100 })]); return { items: [...saleRows.items.map((row) => ({ ...row, record_type: 'SALE' })), ...shipRows.items.map((row) => ({ ...row, record_type: 'SHIPMENT' }))] }; }, enabled: tab === 'sales' });
  const recalls = useQuery({ queryKey: ['report', 'recalls'], queryFn: () => apiGet<Page<Recall>>('/recalls', { page: 1, page_size: 100 }), enabled: tab === 'recalls' });
  const valuation = useQuery({ queryKey: qk.valuation, queryFn: () => apiGet<Valuation>('/reports/stock-valuation'), enabled: tab === 'valuation' });
  const ledger = useQuery({ queryKey: qk.ledger, queryFn: () => apiGet<LedgerIntegrity>('/reports/ledger-integrity'), enabled: tab === 'ledger' });
  const query = { purchases, production, butchering, movements, sales, recalls, valuation, ledger }[tab];
  const rawData = query.data;
  const allRows = reportRows(tab, rawData);
  const dateRows = useMemo(() => allRows.filter((row) => {
    const text = Object.entries(row).filter(([key]) => can('costs:read') || !isCostKey(key)).map(([, value]) => String(value ?? '')).join(' ').toLocaleLowerCase('tr');
    if (search && !text.includes(search.toLocaleLowerCase('tr'))) return false;
    const date = row.occurred_at || row.received_at || row.sold_at || row.shipped_at || row.started_at || row.created_at;
    if (fromDate && date && new Date(String(date)) < new Date(`${fromDate}T00:00:00`)) return false;
    if (toDate && date && new Date(String(date)) > new Date(`${toDate}T23:59:59`)) return false;
    return true;
  }), [allRows, search, fromDate, toDate, can]);
  const first = dateRows[0];
  const columns = first ? visibleCostFields(Object.keys(first), can('costs:read')).map((key) => ({ key, title: fieldLabels[key] || key.replaceAll('_', ' '), render: (row: ReportRow) => cellValue(key, row[key], can('costs:read')), align: ['quantity', 'on_hand', 'value', 'total_cost', 'total_amount'].includes(key) ? 'right' as const : 'left' as const })) : [];
  const exportRows = dateRows.map((row) => Object.fromEntries(visibleCostFields(Object.keys(row), can('costs:read')).map((key) => [key, row[key]])));
  const isLoading = query.isLoading;
  const isError = query.isError;
  const title = tabs.find((item) => item.id === tab)?.label || 'Rapor';
  return <>
    <PageHeader eyebrow="OPERASYONEL ANALİTİK" title="Raporlar" description="Canlı API kayıtlarını filtreleyin ve CSV olarak dışa aktarın." />
    <div className="tab-strip" role="tablist" aria-label="Rapor türü">{tabs.map((item) => <button role="tab" aria-selected={item.id === tab} className={`tab-button ${item.id === tab ? 'tab-active' : ''}`} key={item.id} onClick={() => { setTab(item.id); setSearch(''); }}>{item.label}</button>)}</div>
    <Panel title={title} subtitle={tab === 'purchases' ? 'Backend’de ayrı alış raporu yoktur; lot kabul kayıtları gösterilir.' : tab === 'sales' ? 'Satış ve sevkiyat kayıtları ayrı operasyonlar olarak birleştirilmiştir.' : 'Kaynak endpoint kayıtları · güncel sayfa'} actions={<Button variant="secondary" disabled={!exportRows.length} onClick={() => downloadCsv(`rapor-${tab}.csv`, exportRows)}><Download size={14} />CSV indir</Button>}>
      <div className="toolbar report-toolbar"><SearchBox value={search} onChange={setSearch} placeholder="Rapor satırlarında ara" /><div className="filter-row"><label className="date-filter"><span>Başlangıç</span><input aria-label="Başlangıç tarihi" type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label><label className="date-filter"><span>Bitiş</span><input aria-label="Bitiş tarihi" type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label></div></div>
      {tab === 'valuation' && can('costs:read') && (rawData as Valuation | undefined)?.total_value != null && <div className="valuation-total"><span>Toplam stok değeri</span><strong>{moneyDisplay((rawData as Valuation).total_value)}</strong></div>}
      {tab === 'ledger' && ledger.data && <div className={ledger.data.consistent ? 'inline-success' : 'danger-box'}>{ledger.data.consistent ? 'Defter ve lot bakiyeleri tutarlı.' : `${ledger.data.mismatches?.length || 0} defter tutarsızlığı bulundu.`}</div>}
      {isLoading ? <StateMessage kind="loading" /> : isError ? <StateMessage kind="error" onRetry={() => void query.refetch()} /> : <DataTable rows={dateRows} rowKey={(row) => String(row.id ?? row.order_code ?? row.lot_code ?? JSON.stringify(row))} columns={columns} emptyText="Bu filtrelerle eşleşen rapor kaydı bulunamadı." />}
    </Panel>
  </>;
}

const prodPredictSchema = z.object({ production_order_id: z.string().min(1, 'Üretim emri seçin.') });
const butchPredictSchema = z.object({ animal_type: z.string().trim().min(1, 'Hayvan türü gerekli.'), input_weight: z.string().refine((value) => { try { return decimal(value).gt(0); } catch { return false; } }, 'Ağırlık pozitif olmalı.') });

type ProductionOrder = components['schemas']['ProductionOrderOut'];
function metricsText(value: unknown) {
  if (value == null) return 'Henüz ölçüm yok';
  try { return JSON.stringify(value, null, 2); } catch { return String(value); }
}
function predictionChartRows(predictions: Prediction[], canReadCosts: boolean) {
  return predictions.filter((item) => item.actual_value != null || (canReadCosts && item.actual_cost != null)).slice(0, 12).reverse().map((item) => {
    const actual = item.actual_value;
    const predicted = item.predicted_value;
    const baseline = item.baseline_value;
    const valueError = actual != null && predicted != null ? decimal(predicted).minus(actual).abs() : null;
    const baselineError = actual != null && baseline != null ? decimal(baseline).minus(actual).abs() : null;
    return { name: String(item.id), model: valueError?.toNumber() ?? 0, baseline: baselineError?.toNumber() ?? 0 };
  });
}

export function AiPage() {
  const { can } = useAuth();
  const { notify } = useToast();
  const queryClient = useQueryClient();
  const models = useQuery({ queryKey: qk.models, queryFn: () => apiGet<ModelSummary>('/ai/models') });
  const predictions = useQuery({ queryKey: qk.predictions, queryFn: () => apiGet<Page<Prediction>>('/ai/predictions', { page: 1, page_size: 50 }) });
  const productionOrders = useQuery({ queryKey: qk.production(1), queryFn: () => apiGet<Page<ProductionOrder>>('/production-orders', { page: 1, page_size: 100 }) });
  const prodForm = useForm<z.infer<typeof prodPredictSchema>>({ resolver: zodResolver(prodPredictSchema), defaultValues: { production_order_id: '' } });
  const butchForm = useForm<z.infer<typeof butchPredictSchema>>({ resolver: zodResolver(butchPredictSchema), defaultValues: { animal_type: 'LAMB', input_weight: '' } });
  const [error, setError] = useState<unknown>(null);
  const train = useMutation({ mutationFn: () => apiPost<Record<string, unknown>>('/ai/models/train'), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: qk.models }), queryClient.invalidateQueries({ queryKey: qk.predictions })]); notify('Model eğitimi tamamlandı.'); } });
  const predict = useMutation({ mutationFn: ({ path, body }: { path: string; body: unknown }) => apiPost<Prediction>(path, body), onSuccess: async (prediction) => { await Promise.all([queryClient.invalidateQueries({ queryKey: qk.predictions }), queryClient.invalidateQueries({ queryKey: ['prediction', prediction.id] })]); notify('Tahmin üretildi. Gerçek kayıtların yerine geçmez.'); setError(null); } });
  const chartRows = predictionChartRows(predictions.data?.items || [], can('costs:read'));
  const summary = models.data || {};
  return <>
    <PageHeader eyebrow="MODEL DESTEKLİ KARAR" title="Yapay zekâ" description="Tahminler analiz içindir; kesin stok, maliyet ve lot kayıtlarının yerine geçmez." actions={can('ai:run') ? <Button variant="secondary" onClick={() => train.mutate()} disabled={train.isPending}><RefreshCw size={14} />{train.isPending ? 'Eğitiliyor…' : 'Modelleri eğit'}</Button> : undefined} />
    <div className="warning-box ai-disclaimer">Model verisi sentetik veya sınırlı olabilir. Model sürümü, örnek sayısı ve holdout/cross-validation metrikleri aşağıda kaynaktan gelen haliyle gösterilir.</div>
    <div className="model-grid">{models.isLoading ? <Panel><StateMessage kind="loading" /></Panel> : models.isError ? <Panel><StateMessage kind="error" onRetry={() => void models.refetch()} /></Panel> : Object.entries(summary).map(([key, value]) => {
      const model = value as Record<string, unknown>;
      const metrics = model.metrics as Record<string, unknown> | null;
      const limitations = Array.isArray(model.limitations) ? model.limitations as string[] : [];
      return <Panel title={key === 'production_yield' ? 'Üretim verimi & EKP' : key === 'butchering_output' ? 'Kuzu parça ağırlıkları' : key.replaceAll('_', ' ')} subtitle={String(model.model_name || model.kind || key)} key={key}>
        <div className="model-meta"><div><span>Model sürümü</span><strong>{String(model.version || '—')}</strong></div><div><span>Eğitim örneği</span><strong>{model.n_samples == null ? '—' : String(model.n_samples)}</strong></div><div><span>Eğitim zamanı</span><strong>{model.trained_at ? dateDisplay(String(model.trained_at)) : '—'}</strong></div></div>
        <details className="metrics-details"><summary>Doğrulama ve holdout metrikleri</summary><pre>{metricsText(metrics)}</pre></details>
        {limitations.map((note) => <div className="model-limitation" key={note}>{note}</div>)}
        {model.n_samples != null && Number(model.n_samples) < 30 && <div className="warning-box model-warning">Örnek sayısı 30’dan az; backend model yerine baseline kullanıyor.</div>}
      </Panel>;
    })}</div>
    <div className="two-column"><Panel title="Üretim tahmini" subtitle="Üretim emrinden beklenen verim ve EKP"><form onSubmit={prodForm.handleSubmit((values) => { setError(null); void predict.mutateAsync({ path: '/ai/production-yield/predict', body: { production_order_id: Number(values.production_order_id) } }).catch(setError); })}><Field label="Üretim emri"><select className="select" {...prodForm.register('production_order_id')}><option value="">Emir seçin</option>{productionOrders.data?.items.map((order) => <option key={order.id} value={order.id}>{order.order_code} · {order.status}</option>)}</select></Field><Button type="submit" disabled={!can('ai:run') || predict.isPending}><Sparkles size={14} />Tahmin et</Button><ErrorText error={error || predict.error} /></form>{!can('ai:run') && <small className="muted-note">Tahmin çalıştırmak için ai:run izni gerekir.</small>}</Panel>
      <Panel title="Parçalama verimi tahmini" subtitle="Hayvan türü ve giriş ağırlığından parça ağırlıklarını tahmin eder"><form onSubmit={butchForm.handleSubmit((values) => { setError(null); void predict.mutateAsync({ path: '/ai/butchering-output/predict', body: { animal_type: values.animal_type, input_weight: values.input_weight } }).catch(setError); })}><div className="field-grid"><Field label="Hayvan türü"><input {...butchForm.register('animal_type')} /></Field><Field label="Giriş ağırlığı (kg)"><input inputMode="decimal" {...butchForm.register('input_weight')} /></Field></div><Button type="submit" disabled={!can('ai:run') || predict.isPending}><Sparkles size={14} />Tahmin et</Button><ErrorText error={error || predict.error} /></form></Panel></div>
    <Panel title="Tahmin ve baseline hata karşılaştırması" subtitle="Mutlak hata, yalnızca tahmin ve gerçekleşen değer ikisi de kayıtlıysa çizilir.">
      {predictions.isLoading ? <StateMessage kind="loading" /> : predictions.isError ? <StateMessage kind="error" onRetry={() => void predictions.refetch()} /> : chartRows.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartRows} margin={{ top: 10, right: 12, left: 4, bottom: 5 }}><CartesianGrid stroke="#edf1ec" vertical={false} /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 9 }} /><Tooltip /><Legend /><Bar dataKey="model" name="Model mutlak hatası" fill="#367b58" radius={[4,4,0,0]} /><Bar dataKey="baseline" name="Baseline mutlak hatası" fill="#d8bc79" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer></div> : <StateMessage kind="empty" message="Karşılaştırma için gerçekleşen değer içeren tahmin yok." />}
    </Panel>
    <Panel title="Tahmin geçmişi" actions={<Button variant="secondary" disabled={!predictions.data?.items.length} onClick={() => downloadCsv('ai-tahminleri.csv', (predictions.data?.items || []).map((row) => ({ id: row.id, tur: row.prediction_type, surum: row.model_version, durum: row.status, tahmin: row.predicted_value ?? '', baseline: row.baseline_value ?? '', gercek: row.actual_value ?? '', hata: row.error_value ?? '', ...(can('costs:read') ? { ekp_tahmini: row.predicted_cost ?? '', ekp_baseline: row.baseline_cost ?? '', ekp_gercek: row.actual_cost ?? '' } : {}) })))}><Download size={14} />CSV indir</Button>}>
      {predictions.isLoading ? <StateMessage kind="loading" /> : predictions.isError ? <StateMessage kind="error" onRetry={() => void predictions.refetch()} /> : <DataTable rows={predictions.data?.items || []} rowKey={(row) => row.id} columns={[{ key: 'id', title: 'No', render: (row) => row.id }, { key: 'type', title: 'Tahmin türü', render: (row) => row.prediction_type.replaceAll('_', ' ') }, { key: 'model', title: 'Sürüm', render: (row) => row.model_version }, { key: 'predicted', title: 'Tahmin', render: (row) => row.predicted_value == null ? '—' : amountDisplay(row.predicted_value), align: 'right' }, { key: 'baseline', title: 'Baseline', render: (row) => row.baseline_value == null ? '—' : amountDisplay(row.baseline_value), align: 'right' }, { key: 'actual', title: 'Gerçek', render: (row) => row.actual_value == null ? 'Bekleniyor' : amountDisplay(row.actual_value), align: 'right' }, ...(can('costs:read') ? [{ key: 'cost', title: 'Tahmin EKP', render: (row: Prediction) => row.predicted_cost == null ? '—' : moneyDisplay(row.predicted_cost), align: 'right' as const }] : []), { key: 'metric', title: 'Hata metriği', render: (row) => row.metric_name ? `${row.metric_name} · ${row.error_value ?? '—'}` : '—' }, { key: 'date', title: 'Zaman', render: (row) => dateDisplay(row.created_at) }, { key: 'status', title: 'Durum', render: (row) => <StatusBadge value={row.status} /> }]} />}
    </Panel>
    {can('ai:run') && train.error && <ErrorText error={train.error} />}
  </>;
}

export function AlertsPage() {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const { notify } = useToast();
  const alerts = useQuery({ queryKey: qk.alerts, queryFn: () => apiGet<Page<Alert>>('/alerts', { open_only: true, page, page_size: 50 }) });
  const scan = useMutation({ mutationFn: () => apiPost<Alert[]>('/alerts/scan'), onSuccess: async (items) => { await Promise.all([queryClient.invalidateQueries({ queryKey: qk.alerts }), queryClient.invalidateQueries({ queryKey: qk.dashboard })]); notify(`Tarama tamamlandı · ${items.length} uyarı bulundu.`); } });
  const acknowledge = useMutation({ mutationFn: (id: number) => apiPost<Alert>(`/alerts/${id}/acknowledge`), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: qk.alerts }), queryClient.invalidateQueries({ queryKey: qk.dashboard })]); notify('Uyarı onaylandı.'); } });
  return <>
    <PageHeader eyebrow="KALİTE & ANOMALİ" title="Anomali uyarıları" description="Kural tabanlı tarama sonuçlarını inceleyin ve denetim iziyle onaylayın." actions={can('alerts:manage') ? <Button onClick={() => scan.mutate()} disabled={scan.isPending}><RefreshCw size={14} />{scan.isPending ? 'Taranıyor…' : 'Şimdi tara'}</Button> : undefined} />
    {scan.error && <ErrorText error={scan.error} />}
    <Panel title="Açık uyarılar" subtitle="Anomali taraması stok ve lot kayıtlarını değiştirmez." actions={<span className="muted-count">{alerts.data?.total ?? 0} açık</span>}>
      {alerts.isLoading ? <StateMessage kind="loading" /> : alerts.isError ? <StateMessage kind="error" onRetry={() => void alerts.refetch()} /> : <DataTable rows={alerts.data?.items || []} rowKey={(row) => row.id} page={page} pageSize={50} total={alerts.data?.total} onPageChange={setPage} columns={[{ key: 'date', title: 'Tarih', render: (row) => dateDisplay(row.created_at) }, { key: 'type', title: 'Uyarı', render: (row) => <span className="cell-stack"><strong>{row.alert_type.replaceAll('_', ' ')}</strong><small>{row.entity_type} · #{row.entity_id}</small></span> }, { key: 'message', title: 'Açıklama', render: (row) => row.message }, { key: 'severity', title: 'Önem', render: (row) => <StatusBadge value={row.severity} /> }, { key: 'action', title: '', render: (row) => can('alerts:manage') && !row.acknowledged_at ? <Button variant="secondary" disabled={acknowledge.isPending} onClick={() => acknowledge.mutate(row.id)}>Onayla</Button> : <span>{dateDisplay(row.acknowledged_at)}</span> }]} />}
    </Panel>
  </>;
}


