/**
 * Single money formatter for the app. Accepts the loose shapes the API returns
 * (numeric strings, null) so callers don't each re-implement the guard.
 */
export const formatMoney = (
  amount: number | string | null | undefined,
  currencySymbol: string,
  decimals = 2
): string => {
  const n = typeof amount === 'string' ? parseFloat(amount) : amount;
  const safe = n === null || n === undefined || Number.isNaN(n) ? 0 : n;
  return `${currencySymbol}${safe.toLocaleString('es-DO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
};

/** @deprecated use formatMoney */
export const formatCurrency = (amount: number, currencySymbol: string): string =>
  formatMoney(amount, currencySymbol);
