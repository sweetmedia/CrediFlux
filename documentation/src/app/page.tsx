import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-5xl font-bold mb-4">CrediFlux</h1>
        <p className="text-xl text-muted-foreground mb-8">
          Sistema de Gestión de Préstamos y Cobranzas
        </p>
        <Link
          href="/docs"
          className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
        >
          Ver Documentación
        </Link>
      </div>
    </main>
  );
}
