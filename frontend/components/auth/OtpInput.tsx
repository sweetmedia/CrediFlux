/** Código de un solo uso en cajas de un dígito (login.html, paso 2). */
import { useRef } from 'react';

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  length?: number;
  disabled?: boolean;
  autoFocus?: boolean;
}

export function OtpInput({ value, onChange, length = 6, disabled, autoFocus }: OtpInputProps) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length }, (_, i) => value[i] ?? '');

  const setAt = (i: number, d: string) => {
    const next = digits.slice();
    next[i] = d;
    onChange(next.join('').slice(0, length));
  };

  return (
    <div className="grid gap-2.5" style={{ gridTemplateColumns: `repeat(${length}, minmax(0, 1fr))` }}>
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          aria-label={`Dígito ${i + 1}`}
          value={d}
          disabled={disabled}
          autoFocus={autoFocus && i === 0}
          className="cf-input cf-input--mono h-12 text-center text-[20px]"
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(-1);
            if (!v) return;
            setAt(i, v);
            refs.current[Math.min(i + 1, length - 1)]?.focus();
          }}
          onKeyDown={(e) => {
            if (e.key !== 'Backspace') return;
            e.preventDefault();
            if (d) {
              setAt(i, '');
            } else if (i > 0) {
              setAt(i - 1, '');
              refs.current[i - 1]?.focus();
            }
          }}
          onPaste={(e) => {
            const pegado = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
            if (!pegado) return;
            e.preventDefault();
            onChange(pegado);
            refs.current[Math.min(pegado.length, length - 1)]?.focus();
          }}
        />
      ))}
    </div>
  );
}
