/** Vitrina mínima del DS para las pruebas e2e del tema (sólo en desarrollo). */
export default function DsShowcase() {
  return (
    <div className="cf-root min-h-screen bg-cream p-8">
      <button type="button" className="cf-btn cf-btn--primary" data-testid="primary">
        Registrar pago
      </button>
      <p className="mt-4 text-sage-600" data-testid="muted">Texto secundario</p>
      <div className="cf-paper mt-6 bg-white p-6 text-forest-900" data-testid="paper">
        Contrato de préstamo
      </div>
    </div>
  );
}
