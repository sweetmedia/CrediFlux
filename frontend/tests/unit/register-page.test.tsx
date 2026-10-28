import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const registerTenant = vi.hoisted(() => vi.fn());
vi.mock('@/lib/api/auth', () => ({ authAPI: { registerTenant } }));
vi.mock('@/lib/api/rnc', () => ({ rncAPI: { validateRNC: vi.fn().mockResolvedValue({ exists: false }) } }));

import RegisterPage from '@/app/register/page';

function montar() {
  const router = createMemoryRouter([{ path: '/register', element: <RegisterPage /> }], { initialEntries: ['/register'] });
  render(<RouterProvider router={router} />);
}

const escribir = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const clic = async (name: RegExp | string) => {
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name }));
  });
};
const paso = () => screen.getByRole('heading', { level: 1 }).textContent;

async function llenarHastaConfirmar() {
  escribir('Nombre de la empresa', 'Financiera Demo');
  escribir('Dirección web', 'Demo Fin');
  escribir('Correo de la empresa', 'info@demo.do');
  await clic('Continuar');
  escribir('Cédula', '00123451110');
  escribir('Nombre', 'Ana');
  escribir('Apellidos', 'Ramírez');
  escribir('Correo', 'ana@demo.do');
  escribir('Contraseña', 'Rio-Yaque-44');
  escribir('Repite la contraseña', 'Rio-Yaque-44');
  await clic('Continuar');
  fireEvent.click(screen.getByRole('radio', { name: /professional/i }));
  await clic('Continuar');
}

beforeEach(() => {
  registerTenant.mockReset();
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('/register', () => {
  it('son cuatro pasos y no avanza con datos inválidos', async () => {
    montar();
    expect(paso()).toBe('Tu empresa');
    expect(screen.getByText('Paso 1 de 4')).toBeInTheDocument();
    await clic('Continuar');
    expect(paso()).toBe('Tu empresa');
    expect(screen.getByText('Nombre del negocio requerido')).toBeInTheDocument();
  });

  it('confirma lo escrito, permite editar y exige aceptar los términos', async () => {
    montar();
    await llenarHastaConfirmar();
    expect(paso()).toBe('Confirma los datos');
    const resumen = screen.getByRole('region', { name: 'Resumen' });
    expect(within(resumen).getByText('Financiera Demo')).toBeInTheDocument();
    expect(within(resumen).getByText('demo-fin')).toBeInTheDocument();
    expect(within(resumen).getByText('Professional')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Crear cuenta' })).toBeDisabled();

    await clic('Editar empresa');
    expect(paso()).toBe('Tu empresa');
  });

  it('envía el mismo payload de siempre y en 201 pide verificar el correo', async () => {
    registerTenant.mockResolvedValue({ id: 1 });
    montar();
    await llenarHastaConfirmar();
    fireEvent.click(screen.getByRole('checkbox', { name: /acepto los términos/i }));
    await clic('Crear cuenta');
    expect(Object.keys(registerTenant.mock.calls[0][0]).sort()).toEqual(
      [
        'business_name', 'email', 'owner_email', 'owner_first_name', 'owner_id_number', 'owner_last_name',
        'owner_password', 'owner_password_confirm', 'owner_phone', 'phone', 'subdomain', 'subscription_plan', 'tenant_name',
      ].sort(),
    );
    expect(registerTenant.mock.calls[0][0]).toMatchObject({ subdomain: 'demo-fin', tenant_name: 'demo-fin', subscription_plan: 'professional' });
    expect(await screen.findByText(/revisa tu correo para activar tu cuenta/i)).toBeInTheDocument();
  });

  it('en 202 pendiente no dice que ya puedes entrar', async () => {
    registerTenant.mockResolvedValue({ status: 'pending', message: 'x' });
    montar();
    await llenarHastaConfirmar();
    fireEvent.click(screen.getByRole('checkbox', { name: /acepto los términos/i }));
    await clic('Crear cuenta');
    expect(await screen.findByText(/estamos revisando tu solicitud/i)).toBeInTheDocument();
    expect(screen.queryByText(/ya puedes entrar/i)).not.toBeInTheDocument();
  });

  it('un error de la contraseña del dueño vuelve al paso 2 y sale en el campo', async () => {
    registerTenant.mockRejectedValue({ response: { data: { owner_password: ['Esta contraseña es demasiado común.'] } } });
    montar();
    await llenarHastaConfirmar();
    fireEvent.click(screen.getByRole('checkbox', { name: /acepto los términos/i }));
    await clic('Crear cuenta');
    expect(paso()).toBe('Tu cuenta de administrador');
    expect(await screen.findByText('Esta contraseña es demasiado común.')).toBeInTheDocument();
  });
});
