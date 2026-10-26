import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { AlertTriangle, ArrowLeft, ChevronLeft, ChevronRight, LoaderCircle, Search, X } from 'lucide-react';
import { ApiError } from '../api/client';

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="page-actions">{actions}</div>}</div>;
}
export function Panel({ title, subtitle, actions, children, className = '' }: { title?: string; subtitle?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{(title || actions) && <div className="panel-heading"><div>{title && <h2>{title}</h2>}{subtitle && <p>{subtitle}</p>}</div>{actions}</div>}{children}</section>;
}
export function Button({ children, variant = 'primary', className = '', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'danger' | 'quiet' }) {
  return <button className={`button button-${variant} ${className}`} {...props}>{children}</button>;
}
export function SearchBox({ value, onChange, placeholder = 'Ara…' }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="search-box"><Search size={17} /><input aria-label={placeholder} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>;
}
export function StateMessage({ kind, message, onRetry }: { kind: 'loading' | 'empty' | 'error'; message?: string; onRetry?: () => void }) {
  if (kind === 'loading') return <div className="state-message"><LoaderCircle className="spin" size={22} /><span>{message || 'Bilgiler yükleniyor…'}</span></div>;
  if (kind === 'empty') return <div className="state-message"><span className="state-dot" /><span>{message || 'Gösterilecek kayıt bulunamadı.'}</span></div>;
  return <div className="state-message state-error"><AlertTriangle size={20} /><span>{message || 'Veriler alınamadı.'}</span>{onRetry && <Button variant="secondary" onClick={onRetry}>Tekrar dene</Button>}</div>;
}
export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError && error.status === 429
    ? `Çok sık istek gönderildi. ${error.retryAfterSeconds ? `${error.retryAfterSeconds} saniye sonra` : 'Biraz sonra'} tekrar deneyin.`
    : error instanceof Error ? error.message : 'İşlem tamamlanamadı.';
  return <div className="inline-error" role="alert">{message}</div>;
}
export function StatusBadge({ value }: { value?: string | null }) {
  const normalized = (value || 'UNKNOWN').toUpperCase();
  const tone = ['ACTIVE', 'COMPLETED', 'SHIPPED', 'ACKNOWLEDGED', 'CONTACTED'].includes(normalized) ? 'green'
    : ['DRAFT', 'PENDING', 'IN_PROGRESS', 'UNREACHABLE'].includes(normalized) ? 'amber'
    : ['BLOCKED', 'CANCELLED', 'REVERSED', 'FAILED'].includes(normalized) ? 'red' : 'neutral';
  const labels: Record<string, string> = { ACTIVE: 'Aktif', COMPLETED: 'Tamamlandı', SHIPPED: 'Sevk edildi', DRAFT: 'Taslak', PENDING: 'Bekliyor', IN_PROGRESS: 'Devam ediyor', RESOLVED: 'Çözüldü', CANCELLED: 'İptal', BLOCKED: 'Bloke', OPEN: 'Açık', ACKNOWLEDGED: 'Onaylandı', CONTACTED: 'İletişim kuruldu', UNREACHABLE: 'Ulaşılamadı', NOT_REQUIRED: 'Gerekli değil', FAILED: 'Başarısız', REVERSED: 'Ters kayıt', COMPLETED_WITH_VARIANCE: 'Fark onaylı' };
  return <span className={`badge badge-${tone}`}><i />{labels[normalized] || normalized.replaceAll('_', ' ')}</span>;
}
export function DataTable<T>({ rows, columns, rowKey, page, pageSize, total, onPageChange, emptyText = 'Bu filtrelerle eşleşen kayıt yok.' }: {
  rows: T[]; columns: Array<{ key: string; title: string; render: (row: T) => ReactNode; align?: 'right' | 'left' }>;
  rowKey: (row: T) => string | number; page?: number; pageSize?: number; total?: number; onPageChange?: (page: number) => void; emptyText?: string;
}) {
  const pages = Math.max(1, Math.ceil((total || 0) / (pageSize || 50)));
  return <>
    <div className="table-scroll"><table><thead><tr>{columns.map((column) => <th key={column.key} className={column.align === 'right' ? 'align-right' : ''}>{column.title}</th>)}</tr></thead>
      <tbody>{rows.length ? rows.map((row) => <tr key={rowKey(row)}>{columns.map((column) => <td className={column.align === 'right' ? 'align-right' : ''} key={column.key}>{column.render(row)}</td>)}</tr>) : <tr><td colSpan={columns.length}><div className="table-empty">{emptyText}</div></td></tr>}</tbody>
    </table></div>
    {onPageChange && <div className="table-footer"><span>{total || 0} kayıt · Sayfa {page || 1} / {pages}</span><div><Button variant="quiet" aria-label="Önceki sayfa" disabled={(page || 1) <= 1} onClick={() => onPageChange((page || 1) - 1)}><ChevronLeft size={17} /></Button><Button variant="quiet" aria-label="Sonraki sayfa" disabled={(page || 1) >= pages} onClick={() => onPageChange((page || 1) + 1)}><ChevronRight size={17} /></Button></div></div>}
  </>;
}
export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
export function ConfirmDialog({ title, description, confirmLabel = 'Onayla', destructive = false, requireReason = false, reasonLabel = 'Gerekçe', onClose, onConfirm, busy = false }: {
  title: string; description: string; confirmLabel?: string; destructive?: boolean; requireReason?: boolean; reasonLabel?: string; onClose: () => void; onConfirm: (reason: string) => void | Promise<void>; busy?: boolean;
}) {
  const [reason, setReason] = useState('');
  const valid = !requireReason || reason.trim().length >= 5;
  useEffect(() => { const key = (event: KeyboardEvent) => { if (event.key === 'Escape' && !busy) onClose(); }; window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key); }, [busy, onClose]);
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
      <div className="modal-icon"><AlertTriangle size={21} /></div><button className="icon-button modal-close" aria-label="Pencereyi kapat" onClick={onClose}><X size={18} /></button>
      <h2 id="dialog-title">{title}</h2><p>{description}</p>
      {requireReason && <Field label={reasonLabel}><textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} minLength={5} /></Field>}
      <div className="modal-actions"><Button variant="secondary" disabled={busy} onClick={onClose}>Vazgeç</Button><Button variant={destructive ? 'danger' : 'primary'} disabled={busy || !valid} onClick={() => void onConfirm(reason.trim())}>{busy && <LoaderCircle size={16} className="spin" />}{confirmLabel}</Button></div>
    </div>
  </div>;
}
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event: FormEvent<HTMLDivElement>) => { if (event.target === event.currentTarget) onClose(); }}><div className="modal modal-wide" role="dialog" aria-modal="true"><button className="icon-button modal-close" aria-label="Pencereyi kapat" onClick={onClose}><X size={18} /></button><h2>{title}</h2>{children}</div></div>;
}
export function BackLink({ onClick, children = 'Geri dön' }: { onClick: () => void; children?: ReactNode }) { return <button className="back-link" onClick={onClick}><ArrowLeft size={16} />{children}</button>; }
