import { describe, expect, it } from 'vitest';
import { amountDisplay, decimal, moneyDisplay } from '../lib/format';
import { visibleCostFields } from '../lib/permissions';
import { receiptSchema } from '../pages/InventoryPages';

const validReceipt = { lot_code: 'ET-2026-001', product_id: '1', supplier_id: '', quantity: '100.000', unit_code: 'KG', unit_cost: '9.7000', expiry_date: '', received_at: '' };

describe('finansal doğruluk ve form kuralları', () => {
  it('para değerini Decimal ile dört basamakta hesaplar ve gösterimde iki basamağa yuvarlar', () => {
    const ekp = decimal('1543.50').div('85').toDecimalPlaces(4).toFixed(4);
    expect(ekp).toBe('18.1588');
    expect(moneyDisplay(ekp)).toBe('18,16 €');
    expect(moneyDisplay('1543.50')).toBe('1.543,50 €');
  });

  it('miktar hassasiyetini kayıpsız metin olarak gösterir', () => {
    expect(amountDisplay('0.125000')).toBe('0,125');
  });

  it('maliyet izinleri olmadığında maliyet sütunlarını tamamen gizler', () => {
    expect(visibleCostFields(['lot_code', 'unit_cost', 'ekp', 'status'], false)).toEqual(['lot_code', 'status']);
    expect(visibleCostFields(['lot_code', 'unit_cost', 'ekp', 'status'], true)).toHaveLength(4);
  });

  it('lot kabulü formu lot kodu, pozitif miktar ve maliyet ister', () => {
    expect(receiptSchema.safeParse(validReceipt).success).toBe(true);
    expect(receiptSchema.safeParse({ ...validReceipt, quantity: '' }).success).toBe(false);
    expect(receiptSchema.safeParse({ ...validReceipt, lot_code: '' }).success).toBe(false);
  });
});
