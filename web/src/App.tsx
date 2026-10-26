import { lazy, Suspense, useState } from 'react';
import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, ArrowUpRight, Bell, Boxes, ChartNoAxesCombined, ChevronDown, ClipboardList, Factory,
  FileText, FlaskConical, LayoutDashboard, LogOut, Menu, PackageCheck, Scissors, ShieldAlert, ShoppingCart,
  Truck, Users, X, type LucideIcon,
} from 'lucide-react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from './auth';
import { useToast } from './components/Toast';
import { Button, ErrorText, Field, StateMessage } from './components/UI';

const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const PurchasesPage = lazy(() => import('./pages/InventoryPages').then((module) => ({ default: module.PurchasesPage })));
const InventoryPage = lazy(() => import('./pages/InventoryPages').then((module) => ({ default: module.InventoryPage })));
const ProductionPage = lazy(() => import('./pages/ProductionPage').then((module) => ({ default: module.ProductionPage })));
const ButcheringPage = lazy(() => import('./pages/ButcheringPage').then((module) => ({ default: module.ButcheringPage })));
const SalesPage = lazy(() => import('./pages/SalesPages').then((module) => ({ default: module.SalesPage })));
const ShipmentsPage = lazy(() => import('./pages/SalesPages').then((module) => ({ default: module.ShipmentsPage })));
const TraceabilityPage = lazy(() => import('./pages/TraceabilityPage').then((module) => ({ default: module.TraceabilityPage })));
const RecallPage = lazy(() => import('./pages/RecallPage').then((module) => ({ default: module.RecallPage })));
const ReportsPage = lazy(() => import('./pages/InsightsPages').then((module) => ({ default: module.ReportsPage })));
const AiPage = lazy(() => import('./pages/InsightsPages').then((module) => ({ default: module.AiPage })));
const AlertsPage = lazy(() => import('./pages/InsightsPages').then((module) => ({ default: module.AlertsPage })));
const AdminPage = lazy(() => import('./pages/AdminPages').then((module) => ({ default: module.AdminPage })));
const AuditPage = lazy(() => import('./pages/AdminPages').then((module) => ({ default: module.AuditPage })));
const DocumentsPage = lazy(() => import('./pages/AdminPages').then((module) => ({ default: module.DocumentsPage })));
const navGroups: Array<{ label: string; items: Array<{ to: string; label: string; permission: string; icon: LucideIcon }> }> = [
  { label: 'GENEL BAKIŞ', items: [{ to: '/dashboard', label: 'Ana pano', permission: 'reports:read', icon: LayoutDashboard }] },
  { label: 'OPERASYON', items: [
    { to: '/purchases', label: 'Alış & kabul', permission: 'lots:receive', icon: PackageCheck },
    { to: '/inventory', label: 'Lot & stok', permission: 'inventory:read', icon: Boxes },
    { to: '/production', label: 'Üretim', permission: 'production:read', icon: Factory },
    { to: '/butchering', label: 'Kuzu parçalama', permission: 'butchering:read', icon: Scissors },
    { to: '/sales', label: 'Satışlar', permission: 'sales:read', icon: ShoppingCart },
    { to: '/shipments', label: 'Sevkiyat', permission: 'shipments:read', icon: Truck },
  ] },
  { label: 'KALİTE & ANALİZ', items: [
    { to: '/traceability', label: 'Lot izlenebilirliği', permission: 'traceability:read', icon: Activity },
    { to: '/recalls', label: 'Geri çağırmalar', permission: 'recalls:read', icon: ShieldAlert },
    { to: '/reports', label: 'Raporlar', permission: 'reports:read', icon: ChartNoAxesCombined },
    { to: '/ai', label: 'Yapay zekâ', permission: 'ai:read', icon: FlaskConical },
    { to: '/alerts', label: 'Anomali uyarıları', permission: 'alerts:read', icon: AlertTriangle },
  ] },
  { label: 'YÖNETİM', items: [
    { to: '/admin', label: 'Kullanıcılar', permission: 'users:manage', icon: Users },
    { to: '/audit', label: 'Denetim kayıtları', permission: 'audit:read', icon: ClipboardList },
    { to: '/documents', label: 'Belgeler', permission: 'documents:manage', icon: FileText },
  ] },
];

function LoginPage() {
  const { login } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<unknown>(null);
  const schema = z.object({ email: z.string().email('Geçerli bir e-posta yazın.'), password: z.string().min(1, 'Parola gerekli.') });
  const form = useForm<{ email: string; password: string }>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } });
  const submit = form.handleSubmit(async (values) => {
    setFormError(null);
    try { await login(values.email, values.password); notify('Oturum açıldı.'); navigate('/dashboard', { replace: true }); }
    catch (error) { setFormError(error); }
  });
  return <div className="login-screen"><div className="login-art"><div className="brand brand-large"><span className="brand-mark">A</span><span>AVATAR</span></div><div className="login-art-copy"><span className="eyebrow">OPERASYON MERKEZİ</span><h1>Üretimden sevkiyata<br />her adım kontrol altında.</h1><p>Stok, maliyet ve lot izlenebilirliği tek bir yerde.</p></div><div className="login-art-bottom"><span>GÜVENİLİR KAYIT · ŞEFFAF OPERASYON</span><span>© AVATAR</span></div></div><div className="login-form-wrap"><form className="login-card" onSubmit={submit}><div className="login-greeting"><span className="eyebrow">YÖNETİM PANELİ</span><h2>Tekrar hoş geldiniz</h2><p>Devam etmek için hesabınıza giriş yapın.</p></div>
    <Field label="E-posta"><input type="email" autoComplete="username" placeholder="ornek@avatar.demo" {...form.register('email')} />{form.formState.errors.email && <small className="field-error">{form.formState.errors.email.message}</small>}</Field>
    <Field label="Parola"><input type="password" autoComplete="current-password" placeholder="Parolanız" {...form.register('password')} />{form.formState.errors.password && <small className="field-error">{form.formState.errors.password.message}</small>}</Field>
    <ErrorText error={formError} />
    <Button type="submit" disabled={form.formState.isSubmitting} className="login-submit">{form.formState.isSubmitting ? 'Giriş yapılıyor…' : 'Giriş yap'}<ArrowUpRight size={17} /></Button>
    <p className="login-note">Demo hesap bilgileri backend README içindeki <code>seed_demo</code> adımında tanımlıdır.</p></form></div></div>;
}

function ProtectedLayout() {
  const { user, loading, logout, can } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  if (loading) return <div className="full-state"><StateMessage kind="loading" message="Oturum doğrulanıyor…" /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  const activeGroup = navGroups.flatMap((group) => group.items).find((item) => location.pathname.startsWith(item.to));
  const pageName = activeGroup?.label || 'AVATAR';
  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><span className="brand-mark">A</span><span>AVATAR</span><span className="brand-version">OPS</span><button className="icon-button mobile-close" aria-label="Menüyü kapat" onClick={() => setMobileOpen(false)}><X size={18} /></button></div>
      <div className="workspace-select"><span className="workspace-avatar">A</span><span><b>AVATAR Gıda</b><small>Operasyon alanı</small></span><ChevronDown size={15} /></div>
      <nav className="side-nav">{navGroups.map((group) => {
        const items = group.items.filter((item) => can(item.permission));
        if (!items.length) return null;
        return <div className="nav-group" key={group.label}><div className="nav-caption">{group.label}</div>{items.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'nav-active' : ''}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{to === '/alerts' && <span className="nav-pip" />}</NavLink>)}</div>;
      })}</nav>
      <div className="sidebar-footer"><div className="user-avatar">{user.display_name.slice(0, 1).toUpperCase()}</div><div className="sidebar-user"><b>{user.display_name}</b><small>{user.roles.map((role) => role.toLowerCase().replaceAll('_', ' ')).join(' · ')}</small></div><button className="icon-button" title="Çıkış yap" onClick={() => void logout()}><LogOut size={17} /></button></div>
    </aside>
    {mobileOpen && <button aria-label="Menüyü kapat" className="sidebar-scrim" onClick={() => setMobileOpen(false)} />}
    <main className="main-area"><header className="topbar"><div className="topbar-left"><button className="icon-button menu-toggle" aria-label="Menüyü aç" onClick={() => setMobileOpen(true)}><Menu size={19} /></button><div className="breadcrumbs"><span>AVATAR</span><i>/</i><b>{pageName}</b></div></div><div className="topbar-right"><div className="topbar-status"><span className="online-dot" />API bağlantısı</div><NavLink to="/alerts" className="top-icon" aria-label="Uyarılar"><Bell size={18} /></NavLink><div className="top-user"><span className="user-avatar user-avatar-small">{user.display_name.slice(0, 1).toUpperCase()}</span><span>{user.display_name}</span></div></div></header><div className="content-area"><Suspense fallback={<StateMessage kind="loading" />}><Outlet /></Suspense></div><footer className="app-footer"><span>AVATAR · Operasyon ve izlenebilirlik</span><span>Yönetim paneli</span></footer></main>
  </div>;
}

function PermissionPage({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { can } = useAuth();
  if (!can(permission)) return <div className="permission-denied"><ShieldAlert size={28} /><h2>Bu sayfa için yetkiniz yok</h2><p>İşlem izinleri sunucu tarafında da doğrulanır.</p></div>;
  return children;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  return <Routes><Route path="/login" element={loading ? <div className="full-state"><StateMessage kind="loading" /></div> : user ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
    <Route element={<ProtectedLayout />}>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<PermissionPage permission="reports:read"><DashboardPage /></PermissionPage>} />
      <Route path="/purchases" element={<PermissionPage permission="lots:receive"><PurchasesPage /></PermissionPage>} />
      <Route path="/inventory" element={<PermissionPage permission="inventory:read"><InventoryPage /></PermissionPage>} />
      <Route path="/production" element={<PermissionPage permission="production:read"><ProductionPage /></PermissionPage>} />
      <Route path="/butchering" element={<PermissionPage permission="butchering:read"><ButcheringPage /></PermissionPage>} />
      <Route path="/sales" element={<PermissionPage permission="sales:read"><SalesPage /></PermissionPage>} />
      <Route path="/shipments" element={<PermissionPage permission="shipments:read"><ShipmentsPage /></PermissionPage>} />
      <Route path="/traceability" element={<PermissionPage permission="traceability:read"><TraceabilityPage /></PermissionPage>} />
      <Route path="/recalls" element={<PermissionPage permission="recalls:read"><RecallPage /></PermissionPage>} />
      <Route path="/reports" element={<PermissionPage permission="reports:read"><ReportsPage /></PermissionPage>} />
      <Route path="/ai" element={<PermissionPage permission="ai:read"><AiPage /></PermissionPage>} />
      <Route path="/alerts" element={<PermissionPage permission="alerts:read"><AlertsPage /></PermissionPage>} />
      <Route path="/admin" element={<PermissionPage permission="users:manage"><AdminPage /></PermissionPage>} />
      <Route path="/audit" element={<PermissionPage permission="audit:read"><AuditPage /></PermissionPage>} />
      <Route path="/documents" element={<PermissionPage permission="documents:manage"><DocumentsPage /></PermissionPage>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Route></Routes>;
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}


