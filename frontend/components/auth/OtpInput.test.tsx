import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { OtpInput } from './OtpInput';

function Controlado({ onChange }: { onChange: (v: string) => void }) {
  const [v, setV] = useState('');
  return (
    <OtpInput
      value={v}
      onChange={(x) => {
        setV(x);
        onChange(x);
      }}
    />
  );
}

const cajas = () => screen.getAllByRole('textbox');

describe('OtpInput', () => {
  it('pegar un código de 6 dígitos llena las seis cajas', () => {
    const onChange = vi.fn();
    render(<Controlado onChange={onChange} />);
    fireEvent.paste(cajas()[0], { clipboardData: { getData: () => '123 456' } });
    expect(onChange).toHaveBeenLastCalledWith('123456');
    expect(cajas().map((c) => (c as HTMLInputElement).value)).toEqual(['1', '2', '3', '4', '5', '6']);
  });

  it('un dígito avanza a la siguiente caja; una letra no hace nada', () => {
    const onChange = vi.fn();
    render(<Controlado onChange={onChange} />);
    fireEvent.change(cajas()[0], { target: { value: 'a' } });
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.change(cajas()[0], { target: { value: '7' } });
    expect(onChange).toHaveBeenLastCalledWith('7');
    expect(cajas()[1]).toHaveFocus();
  });

  it('retroceso en una caja vacía vuelve a la anterior y la borra', () => {
    const onChange = vi.fn();
    render(<Controlado onChange={onChange} />);
    fireEvent.change(cajas()[0], { target: { value: '7' } });
    fireEvent.keyDown(cajas()[1], { key: 'Backspace' });
    expect(cajas()[0]).toHaveFocus();
    expect(onChange).toHaveBeenLastCalledWith('');
  });

  it('el autocompletado del sistema escribe el código entero en la primera caja y se reparte', () => {
    const onChange = vi.fn();
    render(<Controlado onChange={onChange} />);
    fireEvent.change(cajas()[0], { target: { value: '123456' } });
    expect(onChange).toHaveBeenLastCalledWith('123456');
    expect(cajas().map((c) => (c as HTMLInputElement).value)).toEqual(['1', '2', '3', '4', '5', '6']);
  });

  it('cada caja tiene su nombre', () => {
    render(<Controlado onChange={() => {}} />);
    expect(cajas().map((c) => c.getAttribute('aria-label'))).toEqual([
      'Dígito 1', 'Dígito 2', 'Dígito 3', 'Dígito 4', 'Dígito 5', 'Dígito 6',
    ]);
  });
});
