import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { CircleCheck, CircleX, Info, X } from 'lucide-react';

type Toast = { id: number; message: string; tone: 'success' | 'error' | 'info' };
type ToastContextValue = { notify: (message: string, tone?: Toast['tone']) => void };
const ToastContext = createContext<ToastContextValue | null>(null);
let serial = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const notify = useCallback((message: string, tone: Toast['tone'] = 'success') => {
    const id = ++serial;
    setItems((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), 4800);
  }, []);
  const value = useMemo(() => ({ notify }), [notify]);
  return <ToastContext.Provider value={value}>
    {children}
    <div className="toast-stack" aria-live="polite" aria-atomic="false">
      {items.map((item) => <div key={item.id} className={`toast toast-${item.tone}`} role="status">
        {item.tone === 'success' ? <CircleCheck size={18} /> : item.tone === 'error' ? <CircleX size={18} /> : <Info size={18} />}
        <span>{item.message}</span>
        <button className="icon-button" aria-label="Bildirimi kapat" onClick={() => setItems((current) => current.filter((x) => x.id !== item.id))}><X size={15} /></button>
      </div>)}
    </div>
  </ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
}
