import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { components } from './api/generated';
import { apiGet, apiPost, clearSessionTokens, hasRefreshSession, setSessionTokens } from './api/client';

type User = components['schemas']['UserOut'];
type AuthValue = { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => Promise<void>; can: (permission: string) => boolean };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const expired = () => { if (alive) setUser(null); };
    window.addEventListener('avatar:auth-expired', expired);
    void (async () => {
      try {
        if (hasRefreshSession()) {
          const token = await apiPost<{ access_token: string; refresh_token: string }>('/auth/refresh', { refresh_token: window.sessionStorage.getItem('avatar.refresh') });
          setSessionTokens(token);
          const current = await apiGet<User>('/auth/me');
          if (alive) setUser(current);
        }
      } catch {
        clearSessionTokens();
        if (alive) setUser(null);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; window.removeEventListener('avatar:auth-expired', expired); };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiPost<{ access_token: string; refresh_token: string }>('/auth/login', { email, password });
    setSessionTokens(tokens);
    const current = await apiGet<User>('/auth/me');
    setUser(current);
  }, []);

  const logout = useCallback(async () => {
    const refresh = window.sessionStorage.getItem('avatar.refresh');
    try { if (refresh) await apiPost<void>('/auth/logout', { refresh_token: refresh }); }
    finally { clearSessionTokens(); setUser(null); }
  }, []);

  const can = useCallback((permission: string) => Boolean(user?.permissions.includes(permission)), [user]);
  const value = useMemo(() => ({ user, loading, login, logout, can }), [user, loading, login, logout, can]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
