import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { useRouter } from '@/lib/navigation';
import Link from '@/lib/navigation/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { TwoFactorSetup } from '@/components/auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Activación obligatoria de la verificación en dos pasos (Task 15).
 *
 * El dueño y los administradores autorizan reversos de pagos con su código
 * TOTP, así que la API les responde 403 `2fa_required` hasta que la activen
 * y `lib/api/client.ts` los trae aquí. La página va dentro del shell
 * (sesión iniciada); el asistente es `TwoFactorSetup`, que al final muestra
 * los códigos de respaldo con `BackupCodesDisplay`.
 */
export default function Setup2FAPage() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const [abierto, setAbierto] = useState(false);

  const alTerminar = async () => {
    try {
      await refreshUser();
    } catch {
      // El dashboard vuelve a cargar el perfil; la 2FA ya quedó activa en el servidor.
    }
    router.replace('/dashboard');
  };

  const yaActiva = Boolean(user?.is_2fa_enabled);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-4 py-10">
      <Card>
        <CardHeader>
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <ShieldCheck className="h-6 w-6 text-primary" aria-hidden="true" />
          </div>
          <CardTitle className="text-2xl">Activa la verificación en dos pasos</CardTitle>
          <CardDescription>
            Tu cuenta es de dueño o administrador: para seguir necesitas activar la verificación
            en dos pasos. Así puedes autorizar reversos de pagos.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {yaActiva ? (
            <>
              <p className="text-sm text-muted-foreground">
                La verificación en dos pasos ya está activa en tu cuenta.
              </p>
              <Button asChild>
                <Link href="/dashboard">Ir al panel</Link>
              </Button>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                Necesitas una aplicación de autenticación en tu teléfono (Google Authenticator,
                Microsoft Authenticator, Authy u otra). Escanearás un código QR, confirmarás con el
                código de 6 dígitos y guardarás tus códigos de respaldo. Mientras no la actives, sólo
                podrás cerrar sesión o configurarla.
              </p>
              <Button onClick={() => setAbierto(true)}>Activar verificación en dos pasos</Button>
            </>
          )}
        </CardContent>
      </Card>

      <TwoFactorSetup isOpen={abierto} onClose={() => setAbierto(false)} onSuccess={alTerminar} />
    </main>
  );
}
