'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { contractsAPI } from '@/lib/api/contracts';
import { useAuth } from '@/lib/contexts/AuthContext';

// Importación dinámica de SignatureCanvas para evitar problemas de SSR
const SignatureCanvas = dynamic(() => import('react-signature-canvas'), {
  ssr: false,
  loading: () => <div className="w-full h-48 bg-slate-100 animate-pulse rounded-lg"></div>
});

export default function SignContractPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated, user } = useAuth();
  const contractId = params.id as string;

  const signaturePadRef = useRef<any>(null);
  const [contract, setContract] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState('');
  const [signType, setSignType] = useState<'customer' | 'officer'>('customer');
  const [useSimpleSign, setUseSimpleSign] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }
    loadContract();
  }, [contractId, isAuthenticated]);

  const loadContract = async () => {
    try {
      setLoading(true);
      const data = await contractsAPI.getContract(contractId);
      setContract(data);
    } catch (err: any) {
      setError(err.message || 'Error al cargar el contrato');
    } finally {
      setLoading(false);
    }
  };

  const clearSignature = () => {
    signaturePadRef.current?.clear();
  };

  const handleSign = async () => {
    if (!useSimpleSign && signaturePadRef.current?.isEmpty()) {
      setError('Por favor dibuje su firma');
      return;
    }

    try {
      setSigning(true);
      setError('');

      const data: any = {};
      if (!useSimpleSign && signaturePadRef.current) {
        data.signature_data = signaturePadRef.current.toDataURL();
      }

      // Sign based on type
      if (signType === 'customer') {
        await contractsAPI.signCustomer(contractId, data.signature_data);
      } else {
        await contractsAPI.signOfficer(contractId, data.signature_data);
      }

      // Redirect back to contract detail
      router.push(`/contracts/${contractId}`);
    } catch (err: any) {
      setError(err.message || 'Error al firmar el contrato');
      setSigning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Cargando contrato...</p>
        </div>
      </div>
    );
  }

  if (error && !contract) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-red-800 font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => router.push(`/contracts/${contractId}`)}
            className="mt-4 text-red-600 underline"
          >
            Volver al contrato
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            Firmar Contrato
          </h1>
          <p className="text-slate-600">
            Contrato: <span className="font-semibold">{contract?.contract_number}</span>
          </p>
          <p className="text-slate-600">
            Cliente: <span className="font-semibold">{contract?.customer_name}</span>
          </p>
        </div>

        {/* Sign Type Selection */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Tipo de Firma
          </h2>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="customer"
                checked={signType === 'customer'}
                onChange={(e) => setSignType(e.target.value as 'customer')}
                className="mr-2"
                disabled={!!contract?.customer_signed_at}
              />
              <span className={contract?.customer_signed_at ? 'text-slate-400' : ''}>
                Cliente {contract?.customer_signed_at && '(Ya firmado)'}
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="officer"
                checked={signType === 'officer'}
                onChange={(e) => setSignType(e.target.value as 'officer')}
                className="mr-2"
                disabled={!!contract?.officer_signed_at}
              />
              <span className={contract?.officer_signed_at ? 'text-slate-400' : ''}>
                Oficial de Crédito {contract?.officer_signed_at && '(Ya firmado)'}
              </span>
            </label>
          </div>
        </div>

        {/* Signature Method */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-900">
              Firma
            </h2>
            <label className="flex items-center text-sm">
              <input
                type="checkbox"
                checked={useSimpleSign}
                onChange={(e) => setUseSimpleSign(e.target.checked)}
                className="mr-2"
              />
              Firma simple (sin dibujo)
            </label>
          </div>

          {!useSimpleSign ? (
            <div>
              <div className="border-2 border-slate-300 rounded-lg mb-4">
                <SignatureCanvas
                  ref={signaturePadRef}
                  canvasProps={{
                    className: 'w-full h-48 cursor-crosshair',
                    style: { background: 'white' }
                  }}
                  backgroundColor="white"
                />
              </div>
              <button
                onClick={clearSignature}
                className="text-sm text-slate-600 hover:text-slate-900 underline"
              >
                Limpiar firma
              </button>
            </div>
          ) : (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-800 text-sm">
                Se registrará la firma sin imagen. Solo se marcará la fecha y hora de firma.
              </p>
            </div>
          )}
        </div>

        {/* Contract Preview */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Vista Previa del Contrato
          </h2>
          <div className="prose prose-sm max-w-none">
            <div className="bg-slate-50 rounded-lg p-4 max-h-96 overflow-y-auto">
              <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans">
                {contract?.content || 'No hay contenido disponible'}
              </pre>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4 justify-end">
          <button
            onClick={() => router.push(`/contracts/${contractId}`)}
            className="px-6 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50"
            disabled={signing}
          >
            Cancelar
          </button>
          <button
            onClick={handleSign}
            disabled={signing}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300"
          >
            {signing ? 'Firmando...' : 'Firmar Contrato'}
          </button>
        </div>
      </div>
    </div>
  );
}
