import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, ArrowRight, Boxes, Factory, PackageCheck, ShieldAlert, Truck, WalletCards } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiGet } from '../api/client';
import type { components } from '../api/generated';
import type { Dashboard, Page } from '../api/types';
import { qk } from '../lib/queryKeys';
import { dateDisplay, moneyDisplay } from '../lib/format';
import { PageHeader, Panel, StateMessage, StatusBadge } from '../components/UI';
import { useAuth } from '../auth';

type Recall = components['schemas']['RecallOut'];
type Alert = components['schemas']['AlertOut'];

export function DashboardPage() {
  const { can } = useAuth();
  const dashboard = useQuery({ queryKey: qk.dashboard, queryFn: () => apiGet<Dashboard>('/reports/dashboard') });
  const recalls = useQuery({ queryKey: ['dashboard-recalls'], queryFn: () => apiGet<Page<Recall>>('/recalls', { status: 'ACTIVE', page: 1, page_size: 5 }) });
  const alerts = useQuery({ queryKey: ['dashboard-alerts'], queryFn: () => apiGet<Page<Alert>>('/alerts', { open_only: true, page: 1, page_size: 5 }) });
  const metrics = dashboard.data;
  const cards = useMemo(() => [
    { label: 'Aktif geri çağırma', value: metrics?.active_recalls, note: 'Backend kayıtları', icon: ShieldAlert, tone: 'red' },
    { label: 'Bloke lot', value: metrics?.blocked_lots, note: 'Satış ve sevkiyat koruması aktif', icon: Boxes, tone: 'amber' },
    { label: 'Tamamlanan üretim', value: metrics?.completed_production_orders, note: 'Toplam emir', icon: Factory, tone: '' },
    { label: 'Sevk edilmiş', value: metrics?.shipments_shipped, note: 'Sevkiyat kaydı', icon: Truck, tone: '' },
  ], [metrics]);
  return <>
    <PageHeader eyebrow="OPERASYON MERKEZİ" title="Ana pano" description="Stok, üretim ve kalite operasyonlarının güncel görünümü." actions={<span className="topbar-status"><span className="online-dot" />Canlı API verisi</span>} />
    {dashboard.isLoading ? <Panel><StateMessage kind="loading" /></Panel> : dashboard.isError ? <Panel><StateMessage kind="error" onRetry={() => void dashboard.refetch()} /></Panel> : <>
      <div className="stat-grid">{cards.map(({ label, value, note, icon: Icon, tone }) => <div className="stat-card" key={label}><div className={`stat-icon ${tone}`}><Icon size={16} /></div><div className="stat-label">{label}</div><div className="stat-value">{value ?? '—'}</div><div className="stat-note">{note}</div></div>)}
        {can('costs:read') && <div className="stat-card"><div className="stat-icon"><WalletCards size={16} /></div><div className="stat-label">Stok değeri</div><div className="stat-value">{metrics?.stock_value == null ? '—' : moneyDisplay(metrics.stock_value)}</div><div className="stat-note">Maliyet izni olan kullanıcılar</div></div>}
        <div className="stat-card"><div className="stat-icon amber"><PackageCheck size={16} /></div><div className="stat-label">Stokta lot</div><div className="stat-value">{metrics?.lots_in_stock ?? '—'}</div><div className="stat-note">Pozitif bakiyeli lot</div></div>
        <div className="stat-card"><div className="stat-icon red"><AlertTriangle size={16} /></div><div className="stat-label">Açık uyarı</div><div className="stat-value">{metrics?.open_alerts ?? '—'}</div><div className="stat-note">Henüz onaylanmamış</div></div>
      </div>
      <div className="two-column"><Panel title="Aktif geri çağırmalar" subtitle="Açık kalite olayları" actions={<Link className="text-button" to="/recalls">Tümünü gör <ArrowRight size={13} /></Link>}>
        {recalls.isLoading ? <StateMessage kind="loading" /> : recalls.isError ? <StateMessage kind="error" onRetry={() => void recalls.refetch()} /> : recalls.data?.items.length ? <div className="data-list">{recalls.data.items.map((recall) => <Link to="/recalls" className="data-list-row data-link" key={recall.id}><span><strong>{recall.recall_code}</strong><small>{recall.reason_code} · {dateDisplay(recall.started_at)}</small></span><StatusBadge value={recall.status} /></Link>)}</div> : <StateMessage kind="empty" message="Aktif geri çağırma kaydı yok." />}
      </Panel><Panel title="Son açık uyarılar" subtitle="Anomali tarama sonuçları" actions={<Link className="text-button" to="/alerts">Uyarı merkezi <ArrowRight size={13} /></Link>}>
        {alerts.isLoading ? <StateMessage kind="loading" /> : alerts.isError ? <StateMessage kind="error" onRetry={() => void alerts.refetch()} /> : alerts.data?.items.length ? <div className="data-list">{alerts.data.items.map((alert) => <div className="data-list-row" key={alert.id}><span><strong>{alert.alert_type.replaceAll('_', ' ')}</strong><small>{alert.message}</small></span><StatusBadge value={alert.severity} /></div>)}</div> : <StateMessage kind="empty" message="Açık uyarı bulunmuyor." />}
      </Panel></div>
      <Panel title="Hızlı erişim" subtitle="Sık kullanılan operasyonlar"><div className="quick-link-grid">{[
        { to: '/traceability', title: 'Lot izini sür', caption: 'Hammaddeyi markete kadar takip edin', icon: Activity, permission: 'traceability:read' },
        { to: '/inventory', title: 'Stok hareketleri', caption: 'Lot bakiyeleri ve defteri inceleyin', icon: Boxes, permission: 'inventory:read' },
        { to: '/production', title: 'Üretim emirleri', caption: 'Dış hizmet üretimini yönetin', icon: Factory, permission: 'production:read' },
      ].filter((item) => can(item.permission)).map(({ to, title, caption, icon: Icon }) => <Link to={to} className="quick-link" key={to}><span className="quick-icon"><Icon size={17} /></span><span><b>{title}</b><small>{caption}</small></span><ArrowRight size={15} /></Link>)}</div></Panel>
    </>}
  </>;
}
