import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Eye, Plus, ShieldAlert, Unlock } from 'lucide-react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { components } from '../api/generated';
import { apiGet, apiPatch, apiPost } from '../api/client';
import type { NotificationList, Page } from '../api/types';
type ForwardResult = components['schemas']['ForwardResult'];
import { qk } from '../lib/queryKeys';
import { amountDisplay, dateDisplay } from '../lib/format';
import { downloadCsv } from '../lib/csv';
import { useAuth } from '../auth';
import { useToast } from '../components/Toast';
import { Button, ConfirmDialog, DataTable, ErrorText, Field, Modal, PageHeader, Panel, SearchBox, StateMessage, StatusBadge } from '../components/UI';

type Recall = components['schemas']['RecallOut'];
type Lot = components['schemas']['LotOut'];
type Impact = components['schemas']['ImpactOut'];
const recallSchema = z.object({ recall_code: z.string().trim().min(1), reason_code: z.string().trim().min(1), lot_codes: z.string().trim().min(1), reason_text: z.string().optional() });
const unblockSchema = z.object({ reason: z.string().trim().min(5) });

export function RecallPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [confirm, setConfirm] = useState<'activate' | 'resolve' | 'cancel' | 'unblock' | null>(null);
  const [unblockLot, setUnblockLot] = useState<Lot | null>(null);
  const [writeError, setWriteError] = useState<unknown>(null);
  const queryClient = useQueryClient();
  const { can } = useAuth();
  const { notify } = useToast();
  const recalls = useQuery({ queryKey: qk.recalls(page), queryFn: () => apiGet<Page<Recall>>('/recalls', { page, page_size: 20 }) });
  const detail = useQuery({ queryKey: ['recall-detail', selectedId], queryFn: () => apiGet<Recall>(`/recalls/${selectedId}`), enabled: selectedId != null });
  const simulation = useQuery({ queryKey: ['recall-simulation', selectedId], queryFn: () => apiGet<ForwardResult>(`/recalls/${selectedId}/simulation`), enabled: selectedId != null });
  const notification = useQuery({ queryKey: qk.notifications(selectedId || 0), queryFn: () => apiGet<NotificationList>(`/reports/recalls/${selectedId}/notification-list`), enabled: selectedId != null });
  const lots = useQuery({ queryKey: ['lots', 1, 'recall-unblock'], queryFn: () => apiGet<Page<Lot>>('/lots', { page: 1, page_size: 100 }) });
  const createForm = useForm<z.infer<typeof recallSchema>>({ resolver: zodResolver(recallSchema), defaultValues: { recall_code: '', reason_code: 'QUALITY_ISSUE', lot_codes: '', reason_text: '' } });
  const create = useMutation({ mutationFn: (body: unknown) => apiPost<Recall>('/recalls', body), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['recalls'] }); notify('Geri çağırma taslak olarak oluşturuldu.'); setShowForm(false); createForm.reset(); } });
  const action = useMutation({ mutationFn: ({ kind, recallId }: { kind: 'activate' | 'resolve' | 'cancel'; recallId: number }) => apiPost<Recall>(`/recalls/${recallId}/${kind}`), onSuccess: async (recall, variables) => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['recalls'] }), queryClient.invalidateQueries({ queryKey: ['recall-detail', recall.id] }), queryClient.invalidateQueries({ queryKey: ['recall-simulation', recall.id] }), queryClient.invalidateQueries({ queryKey: ['lots'] }), queryClient.invalidateQueries({ queryKey: ['movements'] }), queryClient.invalidateQueries({ queryKey: qk.dashboard })]); notify(variables.kind === 'activate' ? 'Geri çağırma aktive edildi; backend ilgili lotları bloke etti.' : variables.kind === 'resolve' ? 'Geri çağırma çözüldü. Lot blokajları ayrı işlemle kaldırılır.' : 'Geri çağırma iptal edildi.'); setConfirm(null); setWriteError(null); } });
  const unblock = useMutation({ mutationFn: ({ lotId, reason }: { lotId: number; reason: string }) => apiPost<Lot>(`/lots/${lotId}/unblock`, { reason }), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['lots'] }), queryClient.invalidateQueries({ queryKey: ['recall-detail'] }), queryClient.invalidateQueries({ queryKey: ['recalls'] })]); notify('Lot blokajı ayrı yetki ve gerekçeyle kaldırıldı.'); setUnblockLot(null); setConfirm(null); } });
  const impactUpdate = useMutation({ mutationFn: ({ recallId, impactId, body }: { recallId: number; impactId: number; body: unknown }) => apiPatch<Impact>(`/recalls/${recallId}/impacts/${impactId}`, body), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ['recall-detail'] }), queryClient.invalidateQueries({ queryKey: ['notifications'] })]); notify('Market iletişim durumu güncellendi.'); } });
  const rows = useMemo(() => (recalls.data?.items || []).filter((item) => !search || `${item.recall_code} ${item.reason_code} ${item.status}`.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr'))), [recalls.data, search]);
  const recall = detail.data;
  const activateReady = Boolean(simulation.data) && recall?.status === 'DRAFT';
  const distribution = simulation.data?.shipments || [];
  const marketTotals = (simulation.data?.customers || []).map((customer) => ({ name: customer.customer_name, quantity: customer.total_quantity, lots: Object.entries(customer.lots).map(([lotCode, qty]) => `${lotCode}: ${amountDisplay(qty)}`).join(', ') }));

  if (selectedId != null) return <>
    <button className="back-link" onClick={() => setSelectedId(null)}>← Geri çağırma listesi</button>
    <PageHeader eyebrow="GERİ ÇAĞIRMA VAKA DOSYASI" title={recall?.recall_code || `Vaka #${selectedId}`} description="Simülasyon, etkilenen stoklar ve market iletişim takibi." actions={<div className="inline-actions">
      {can('recalls:manage') && recall?.status === 'DRAFT' && <Button variant="secondary" onClick={() => void simulation.refetch()} disabled={simulation.isFetching}><ShieldAlert size={14} />Etkiyi simüle et</Button>}
      {can('recalls:manage') && activateReady && <Button variant="danger" onClick={() => setConfirm('activate')}><ShieldAlert size={14} />Geri çağırmayı aktive et</Button>}
      {can('recalls:resolve') && recall?.status === 'ACTIVE' && <Button variant="secondary" onClick={() => setConfirm('resolve')}>Vakayı çöz</Button>}
      {can('recalls:manage') && recall?.status === 'DRAFT' && <Button variant="quiet" onClick={() => setConfirm('cancel')}>Taslağı iptal et</Button>}
    </div>} />
    {detail.isLoading ? <Panel><StateMessage kind="loading" /></Panel> : detail.isError ? <Panel><StateMessage kind="error" onRetry={() => void detail.refetch()} /></Panel> : recall && <>
      <div className="detail-grid"><div className="detail-item"><span>Durum</span><strong><StatusBadge value={recall.status} /></strong></div><div className="detail-item"><span>Neden kodu</span><strong>{recall.reason_code}</strong></div><div className="detail-item"><span>Başlatılma</span><strong>{dateDisplay(recall.started_at)}</strong></div><div className="detail-item"><span>Sevk edilen toplam</span><strong>{recall.total_shipped_quantity == null ? '—' : amountDisplay(recall.total_shipped_quantity)}</strong></div></div>
      {recall.reason_text && <div className="info-box spaced-info">{recall.reason_text}</div>}
      {recall.status === 'ACTIVE' && <div className="danger-box spaced-info"><strong>Geri alınamaz aktivasyon:</strong> etkilenen lotlar blokajda kalır. Vakayı çözmek blokajı kaldırmaz; unblock işlemi ayrı izin ve gerekçe gerektirir.</div>}
      <Panel title="Etki simülasyonu" subtitle="Aktivasyondan önce sevkiyat ve market dağılımını doğrulayın." actions={<Button variant="secondary" onClick={() => void simulation.refetch()} disabled={simulation.isFetching}>Simülasyonu yenile</Button>}>
        {simulation.isLoading ? <StateMessage kind="loading" /> : simulation.isError ? <StateMessage kind="error" message="Etki simülasyonu alınamadı." onRetry={() => void simulation.refetch()} /> : simulation.data && <>
          <div className="detail-grid"><div className="detail-item"><span>Etkilenen lot</span><strong>{simulation.data.lots.length}</strong></div><div className="detail-item"><span>Kayıtlı sevkiyat satırı</span><strong>{simulation.data.shipments.length}</strong></div><div className="detail-item"><span>Kayıtlı market</span><strong>{simulation.data.customers.length}</strong></div><div className="detail-item"><span>Kalan etkilenen stok</span><strong>{amountDisplay(simulation.data.remaining_stock_total)}</strong></div></div>
          <Panel title="Market bazlı dağılım" className="nested-panel"><DataTable rows={marketTotals} rowKey={(item) => item.name} columns={[{ key: 'market', title: 'Market', render: (item) => <strong>{item.name}</strong> }, { key: 'qty', title: 'Toplam miktar', render: (item) => amountDisplay(item.quantity), align: 'right' }, { key: 'lots', title: 'Lot / miktar', render: (item) => item.lots || '—' }]} emptyText="Kayıtlı market dağılımı bulunamadı." /></Panel>
          <Panel title="Sevkiyat kayıtları" className="nested-panel"><DataTable rows={distribution} rowKey={(item) => `${item.shipment_id}-${item.lot_id}-${item.customer_id}`} columns={[{ key: 'market', title: 'Market', render: (item) => item.customer_name }, { key: 'shipment', title: 'Sevkiyat', render: (item) => item.shipment_code }, { key: 'lot', title: 'Lot', render: (item) => item.lot_code }, { key: 'qty', title: 'Miktar', render: (item) => `${amountDisplay(item.quantity)} ${item.unit_code}`, align: 'right' }]} emptyText="Sevkiyat kaydı bulunamadı." /></Panel>
        </>}
      </Panel>
      <Panel title="Etkilenen market iletişim listesi" subtitle={notification.data?.second_tier_note || 'İkinci kademe dağıtım yalnızca kayıtlıysa gösterilir.'} actions={<Button variant="secondary" disabled={!notification.data?.items.length} onClick={() => downloadCsv(`${recall.recall_code}-iletisim.csv`, notification.data?.items || [])}><Download size={14} />CSV indir</Button>}>
        {notification.isLoading ? <StateMessage kind="loading" /> : notification.isError ? <StateMessage kind="error" onRetry={() => void notification.refetch()} /> : notification.data && <DataTable rows={notification.data.items} rowKey={(item) => `${item.customer_code}-${item.lot_code}`} columns={[{ key: 'market', title: 'Market', render: (item) => <span className="cell-stack"><strong>{item.customer_name}</strong><small>{item.customer_code}</small></span> }, { key: 'lot', title: 'Lot', render: (item) => item.lot_code }, { key: 'qty', title: 'Miktar', render: (item) => `${amountDisplay(item.quantity)} ${item.unit_code}`, align: 'right' }, { key: 'contact', title: 'İletişim', render: (item) => <span>{item.email || '—'}<small>{item.phone || ''}</small></span> }, { key: 'status', title: 'İletişim durumu', render: (item) => <StatusBadge value={item.contact_status} /> }]} />}
      </Panel>
      <Panel title="Recall lotları" subtitle="Çözüm ve stok blokajı kaldırma ayrı işlemlerdir."><DataTable rows={recall.lots || []} rowKey={(lot) => lot.lot_id} columns={[{ key: 'lot', title: 'Lot', render: (lot) => <strong>{lot.lot_code}</strong> }, { key: 'role', title: 'İlişki', render: (lot) => lot.role }, { key: 'blocked', title: 'Bloke zamanı', render: (lot) => dateDisplay(lot.blocked_at) }, { key: 'action', title: '', render: (lot) => { const liveLot = lots.data?.items.find((item) => item.id === lot.lot_id); return can('lots:unblock') && recall.status === 'RESOLVED' && liveLot?.is_blocked ? <Button variant="secondary" onClick={() => { setUnblockLot(liveLot); setConfirm('unblock'); }}><Unlock size={13} />Blokajı kaldır</Button> : <StatusBadge value={liveLot?.is_blocked ? 'BLOCKED' : 'ACTIVE'} />; } }]} />{recall.status === 'RESOLVED' && !can('lots:unblock') && <div className="info-box">Blokajı kaldırmak için lots:unblock yetkisi gerekir.</div>}</Panel>
      {(recall.impacts || []).length > 0 && <Panel title="Market iletişim durumları" subtitle="Durum güncellemeleri denetim kaydına alınır."><DataTable rows={recall.impacts || []} rowKey={(impact) => impact.id} columns={[{ key: 'market', title: 'Market', render: (impact) => <span className="cell-stack"><strong>{impact.customer_name || impact.customer_code || `#${impact.customer_id}`}</strong><small>{impact.lot_code}</small></span> }, { key: 'qty', title: 'Miktar', render: (impact) => `${amountDisplay(impact.quantity)} ${impact.unit_code}`, align: 'right' }, { key: 'status', title: 'İletişim', render: (impact) => can('recalls:manage') ? <select className="inline-control status-control" aria-label={`${impact.customer_name || impact.customer_id} iletişim durumu`} value={impact.contact_status} disabled={impactUpdate.isPending} onChange={(event) => void impactUpdate.mutateAsync({ recallId: recall.id, impactId: impact.id, body: { contact_status: event.target.value, notes: impact.notes } }).catch(setWriteError)}><option value="PENDING">Bekliyor</option><option value="CONTACTED">İletişim kuruldu</option><option value="ACKNOWLEDGED">Onaylandı</option><option value="UNREACHABLE">Ulaşılamadı</option><option value="NOT_REQUIRED">Gerekli değil</option></select> : <StatusBadge value={impact.contact_status} /> }]} /><ErrorText error={impactUpdate.error} /></Panel>}      {writeError && <ErrorText error={writeError} />}
    </>}
    {confirm && confirm !== 'unblock' && <ConfirmDialog title={confirm === 'activate' ? 'Geri çağırmayı aktive et' : confirm === 'resolve' ? 'Geri çağırmayı çöz' : 'Geri çağırma taslağını iptal et'} description={confirm === 'activate' ? 'Bu kritik aktivasyon atomik olarak etkilenen lotları bloke eder ve yeni stok çıkışını durdurur. Aktivasyon geri alınamaz; çözüm blokajı kaldırmaz.' : confirm === 'resolve' ? 'Vaka RESOLVED olur. Etkilenen lotlar blokajda kalır ve ayrı yetkiyle açılır.' : 'Taslak geri çağırma iptal edilecektir.'} confirmLabel={confirm === 'activate' ? 'Aktivasyonu onayla' : confirm === 'resolve' ? 'Vakayı çöz' : 'Taslağı iptal et'} destructive={confirm === 'activate' || confirm === 'cancel'} busy={action.isPending} onClose={() => setConfirm(null)} onConfirm={async () => { try { await action.mutateAsync({ kind: confirm, recallId: selectedId }); } catch (error) { setWriteError(error); } }} />}
    {confirm === 'unblock' && unblockLot && <UnblockDialog lot={unblockLot} busy={unblock.isPending} error={unblock.error} onClose={() => { setConfirm(null); setUnblockLot(null); }} onConfirm={(reason) => unblock.mutateAsync({ lotId: unblockLot.id, reason })} />}
  </>;

  return <>
    <PageHeader eyebrow="KALİTE GÜVENCESİ" title="Geri çağırmalar" description="Simülasyon yapın, marketleri doğrulayın ve gereken onaylarla vakayı yönetin." actions={can('recalls:manage') ? <Button onClick={() => setShowForm(true)}><Plus size={15} />Geri çağırma oluştur</Button> : undefined} />
    <Panel title="Geri çağırma kayıtları" actions={<Button variant="secondary" disabled={!rows.length} onClick={() => downloadCsv('geri-cagirmalar.csv', rows.map((row) => ({ kod: row.recall_code, durum: row.status, neden: row.reason_code, baslangic: row.started_at || '', sevk_miktari: row.total_shipped_quantity ?? '' })))}><Download size={14} />CSV indir</Button>}>
      <div className="toolbar"><SearchBox value={search} onChange={setSearch} placeholder="Vaka kodu, neden veya durum ara" /><span className="muted-count">{recalls.data?.total ?? 0} kayıt</span></div>
      {recalls.isLoading ? <StateMessage kind="loading" /> : recalls.isError ? <StateMessage kind="error" onRetry={() => void recalls.refetch()} /> : <DataTable rows={rows} rowKey={(row) => row.id} page={page} pageSize={20} total={recalls.data?.total} onPageChange={setPage} columns={[{ key: 'code', title: 'Geri çağırma', render: (row) => <button className="table-link" onClick={() => setSelectedId(row.id)}><strong>{row.recall_code}</strong><small>{row.reason_code}</small></button> }, { key: 'lots', title: 'Lot', render: (row) => row.lots?.map((lot) => lot.lot_code).join(', ') || '—' }, { key: 'date', title: 'Başlangıç', render: (row) => dateDisplay(row.started_at) }, { key: 'status', title: 'Durum', render: (row) => <StatusBadge value={row.status} /> }, { key: 'action', title: '', render: (row) => <Button variant="quiet" aria-label={`${row.recall_code} detayını aç`} onClick={() => setSelectedId(row.id)}><Eye size={15} /></Button> }]} />}
    </Panel>
    {showForm && <Modal title="Geri çağırma taslağı oluştur" onClose={() => setShowForm(false)}><form onSubmit={createForm.handleSubmit((values) => create.mutate({ recall_code: values.recall_code, reason_code: values.reason_code, lot_codes: values.lot_codes.split(/[\n,;]+/).map((code) => code.trim()).filter(Boolean), reason_text: values.reason_text || null }))}><div className="field-grid"><Field label="Vaka kodu"><input placeholder="GERI-2026-001" {...createForm.register('recall_code')} /></Field><Field label="Neden kodu"><input placeholder="QUALITY_ISSUE" {...createForm.register('reason_code')} /></Field></div><Field label="Sorunlu lot kodları" hint="Birden çok kodu virgül veya satır sonuyla ayırın."><textarea placeholder="ET-2026-001" {...createForm.register('lot_codes')} /></Field><Field label="Gerekçe"><textarea placeholder="Kalite incelemesinde tespit edilen bulgu" {...createForm.register('reason_text')} /></Field><div className="info-box">Önce taslak oluşturun, sonra etki simülasyonunu inceleyin. Aktivasyon açık onay ister.</div><ErrorText error={create.error} /><div className="form-actions"><Button type="submit" disabled={create.isPending}>Taslağı oluştur</Button></div></form></Modal>}
  </>;
}

function UnblockDialog({ lot, busy, error, onClose, onConfirm }: { lot: Lot; busy: boolean; error: unknown; onClose: () => void; onConfirm: (reason: string) => Promise<unknown> }) {
  const form = useForm<z.infer<typeof unblockSchema>>({ resolver: zodResolver(unblockSchema), defaultValues: { reason: '' } });
  return <Modal title={`${lot.lot_code} blokajını kaldır`} onClose={onClose}><div className="warning-box">Geri çağırmanın RESOLVED olması blokajı otomatik kaldırmaz. Bu ayrı işlem audit kaydı üretir.</div><form onSubmit={form.handleSubmit(async ({ reason }) => { try { await onConfirm(reason); } catch { return; } })}><Field label="Gerekçe"><textarea minLength={5} {...form.register('reason')} /></Field><ErrorText error={error} /><div className="form-actions"><Button variant="secondary" type="button" onClick={onClose}>Vazgeç</Button><Button variant="danger" type="submit" disabled={busy}>Blokajı kaldır</Button></div></form></Modal>;
}




