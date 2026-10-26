import Decimal from 'decimal.js';

Decimal.set({ precision: 28, rounding: Decimal.ROUND_HALF_UP });
export const decimal = (value: string | number | null | undefined) => new Decimal(value ?? 0);
export const moneyExact = (value: string | number | null | undefined) => decimal(value).toDecimalPlaces(4, Decimal.ROUND_HALF_UP);
export const isDecimalPositive = (value: string) => { try { return new Decimal(value).gt(0); } catch { return false; } };
export const isDecimalNonNegative = (value: string) => { try { return new Decimal(value).gte(0); } catch { return false; } };

function localizedDecimal(value: Decimal, fixedPlaces?: number) {
  let text = fixedPlaces == null ? value.toFixed() : value.toFixed(fixedPlaces, Decimal.ROUND_HALF_UP);
  let [integer, fraction] = text.split('.');
  if (fixedPlaces == null) fraction = fraction?.replace(/0+$/, '');
  integer = integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${integer}${fraction ? `,${fraction}` : ''}`;
}

export const moneyDisplay = (value: string | number | null | undefined, currency = 'EUR') => value == null
  ? '—'
  : `${localizedDecimal(moneyExact(value).toDecimalPlaces(2, Decimal.ROUND_HALF_UP), 2)} ${currency === 'EUR' ? '€' : currency}`;
export const amountDisplay = (value: string | number | null | undefined) => value == null ? '—' : localizedDecimal(decimal(value));
export const dateDisplay = (value?: string | null) => value
  ? new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Istanbul' }).format(new Date(value))
  : '—';
export const dayDisplay = (value?: string | null) => value
  ? new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeZone: 'Europe/Istanbul' }).format(new Date(value))
  : '—';
export const percentDisplay = (value: string | number | null | undefined) => value == null
  ? '—'
  : `${localizedDecimal(decimal(value).toDecimalPlaces(2, Decimal.ROUND_HALF_UP), 2)}%`;
