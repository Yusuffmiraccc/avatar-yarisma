import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ConfirmDialog } from '../components/UI';

describe('kritik işlem onayı', () => {
  it('gerekçe tamamlanmadan işlemi açmaz ve onaydan sonra gerekçeyi iletir', () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog title="Stok düzeltmesi" description="Deftere yazılacak." requireReason reasonLabel="Gerekçe" confirmLabel="Onayla" onClose={() => undefined} onConfirm={onConfirm} />);
    const button = screen.getByRole('button', { name: 'Onayla' });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Gerekçe'), { target: { value: 'Sayım farkı' } });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    expect(onConfirm).toHaveBeenCalledWith('Sayım farkı');
  });
});
