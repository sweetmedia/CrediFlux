/**
 * Format currency with dynamic symbol from tenant configuration
 */
export const formatCurrency = (amount: number, currencySymbol: string): string => {
  return `${currencySymbol}${amount.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`;
};
