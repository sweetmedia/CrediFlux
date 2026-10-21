'use client';

import { useConfig } from '@/lib/contexts/ConfigContext';
import { formatMoney } from '@/lib/utils/currency';
import { cn } from '@/lib/utils';

interface MoneyProps extends React.HTMLAttributes<HTMLSpanElement> {
  value: number | string | null | undefined;
}

/** Every amount in the UI goes through here: mono, tabular, never wraps. */
export function Money({ value, className, ...props }: MoneyProps) {
  const { config } = useConfig();
  return (
    <span className={cn('font-mono tabular-nums whitespace-nowrap', className)} {...props}>
      {formatMoney(value, config.currency_symbol, config.decimal_places)}
    </span>
  );
}
