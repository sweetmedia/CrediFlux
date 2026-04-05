'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import {
  Loader2,
  Building2,
  Bell,
  Palette,
  ChevronRight,
  Sparkles,
  ShieldCheck,
  SlidersHorizontal,
  UserCircle2,
  Workflow,
  ArrowUpRight,
} from 'lucide-react';

interface SettingsCard {
  title: string;
  description: string;
  eyebrow: string;
  icon: React.ReactNode;
  href: string;
  badge?: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, tenant, isAuthenticated, isLoading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F8FAF7]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  const settingsSections: SettingsCard[] = [
    {
      title: 'Organización y perfil',
      description: 'Negocio, branding, perfil, seguridad, notificaciones y correo en un mismo lugar.',
      eyebrow: 'Core setup',
      icon: <Building2 className="h-5 w-5 text-[#163300]" />,
      href: '/settings/general',
    },
    {
      title: 'Políticas de préstamos',
      description: 'Tasas, montos, plazos, mora, documentos, pagos y reglas operativas.',
      eyebrow: 'Lending engine',
      icon: <Workflow className="h-5 w-5 text-[#163300]" />,
      href: '/settings/loans',
      badge: 'Prioridad',
    },
    {
      title: 'Perfil del usuario',
      description: 'Actualiza tu foto, cargo, bio y datos de tu cuenta.',
      eyebrow: 'Cuenta',
      icon: <UserCircle2 className="h-5 w-5 text-[#163300]" />,
      href: '/settings/general#profile',
    },
    {
      title: 'Seguridad',
      description: 'Contraseña, 2FA, códigos de respaldo y acceso seguro.',
      eyebrow: 'Protección',
      icon: <ShieldCheck className="h-5 w-5 text-[#163300]" />,
      href: '/settings/general#security',
    },
    {
      title: 'Canales y alertas',
      description: 'WhatsApp, email y preferencias de recordatorios para el equipo.',
      eyebrow: 'Comunicaciones',
      icon: <Bell className="h-5 w-5 text-[#163300]" />,
      href: '/settings/general#notifications',
    },
    {
      title: 'Apariencia',
      description: 'Logo, color principal y consistencia visual del tenant.',
      eyebrow: 'Branding',
      icon: <Palette className="h-5 w-5 text-[#163300]" />,
      href: '/settings/general#appearance',
    },
  ];

  const quickNotes = [
    'Primero termina auth, branding y lending defaults.',
    'Después afina notificaciones y automatizaciones.',
    'Todo debe verse limpio, compacto y listo para demo.',
  ];

  return (
    <div className="min-h-screen bg-[#F8FAF7] p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="overflow-hidden rounded-3xl border border-[#163300]/10 bg-white">
          <div className="grid gap-0 lg:grid-cols-[1.4fr,0.9fr]">
            <div className="border-b border-slate-200/70 p-6 lg:border-b-0 lg:border-r lg:p-8">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#163300]/10 bg-[#163300]/5 px-3 py-1 text-xs font-medium text-[#163300]">
                <Sparkles className="h-3.5 w-3.5" />
                Centro de configuración
              </div>

              <h1 className="text-3xl font-semibold tracking-tight text-slate-950 lg:text-4xl">
                Configura CrediFlux para operar y vender sin fricción.
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 lg:text-base">
                Desde aquí ajustas la identidad del negocio, seguridad, comunicaciones y las reglas
                que definen cómo se originan y gestionan los préstamos.
              </p>

              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  href="/settings/general"
                  className="inline-flex items-center gap-2 rounded-xl bg-[#163300] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#0f2400]"
                >
                  Abrir configuración general
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/settings/loans"
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-[#163300]/25 hover:text-[#163300]"
                >
                  Revisar políticas de préstamos
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            <div className="grid gap-3 p-6 lg:p-8">
              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Tenant</p>
                <p className="mt-2 text-lg font-semibold text-slate-950">{tenant?.business_name || tenant?.name || 'CrediFlux'}</p>
                <p className="mt-1 text-sm text-slate-600">Moneda base: {(tenant as any)?.currency_symbol || 'RD$'} · Color: {(tenant as any)?.primary_color || '#163300'}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Sesión activa</p>
                <p className="mt-2 text-lg font-semibold text-slate-950">{user?.email || 'Usuario autenticado'}</p>
                <p className="mt-1 text-sm text-slate-600">Rol: {user?.role || 'owner'} · ajustes sensibles protegidos</p>
              </div>
              <div className="rounded-2xl border border-[#FFE026]/60 bg-[#FFF9D6] p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <SlidersHorizontal className="h-4 w-4 text-[#B58100]" />
                  Checklist rápido
                </div>
                <ul className="mt-3 space-y-2 text-sm text-slate-700">
                  {quickNotes.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#163300]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {settingsSections.map((section) => (
            <Link
              key={section.title}
              href={section.href}
              className="group rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-[#163300]/20 hover:shadow-[0_12px_30px_rgba(15,23,42,0.06)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="rounded-2xl border border-[#163300]/10 bg-[#163300]/5 p-2.5">
                    {section.icon}
                  </div>
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">
                      {section.eyebrow}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <h2 className="text-base font-semibold text-slate-950">{section.title}</h2>
                      {section.badge && (
                        <span className="rounded-full bg-[#FFE026] px-2 py-0.5 text-[11px] font-semibold text-slate-900">
                          {section.badge}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-5 w-5 text-slate-400 transition group-hover:text-[#163300]" />
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-600">{section.description}</p>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}
