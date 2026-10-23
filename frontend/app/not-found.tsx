import Link from '@/lib/navigation/link';

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-8 text-center">
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="font-display text-heading-xl">Esta página no existe</h1>
      <Link href="/dashboard" className="text-sm font-medium underline underline-offset-4">
        Volver al panel
      </Link>
    </div>
  );
}
