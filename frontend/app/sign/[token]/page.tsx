'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { publicContractAPI } from '@/lib/api/contracts';

// Importación dinámica de SignatureCanvas para evitar problemas de SSR
const SignatureCanvas = dynamic(() => import('react-signature-canvas'), {
  ssr: false,
  loading: () => <div className="w-full h-48 bg-slate-100 animate-pulse rounded-lg"></div>
});

export default function PublicSignPage() {
  const params = useParams();
  const token = params.token as string;

  const signaturePadRef = useRef<any>(null);
  const [contractData, setContractData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadContract();
  }, [token]);

  const loadContract = async () => {
    try {
      setLoading(true);
      const data = await publicContractAPI.getContractByToken(token);
      setContractData(data);
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
    if (signaturePadRef.current?.isEmpty()) {
      setError('Por favor dibuje su firma');
      return;
    }

    try {
      setSigning(true);
      setError('');

      const signatureData = signaturePadRef.current.toDataURL();
      const result = await publicContractAPI.signWithToken(token, signatureData);

      setSuccess(true);
      setSigning(false);
    } catch (err: any) {
      setError(err.message || 'Error al firmar el contrato');
      setSigning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Cargando contrato...</p>
        </div>
      </div>
    );
  }

  if (error && !contractData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <div className="text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Error</h2>
            <p className="text-slate-600 mb-6">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">¡Contrato Firmado!</h2>
            <p className="text-slate-600 mb-6">
              Tu firma ha sido registrada exitosamente.
            </p>
            <p className="text-sm text-slate-500">
              Puedes cerrar esta ventana.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const contract = contractData?.contract;
  const permissions = contractData?.token_permissions;

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 mb-2">
                Firma de Contrato
              </h1>
              <p className="text-slate-600">
                Contrato: <span className="font-semibold">{contract?.contract_number}</span>
              </p>
              <p className="text-slate-600">
                Cliente: <span className="font-semibold">{contract?.customer_name}</span>
              </p>
            </div>
            <div className="text-sm text-slate-500">
              <p>Expira: {new Date(contractData.expires_at).toLocaleDateString()}</p>
            </div>
          </div>

          {/* Permission Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              {permissions?.can_sign_as_customer && 'Firmando como: Cliente'}
              {permissions?.can_sign_as_officer && 'Firmando como: Oficial de Crédito'}
            </p>
          </div>
        </div>

        {/* Contract Content */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Contenido del Contrato
          </h2>
          <div className="bg-slate-50 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans">
              {contract?.content || 'No hay contenido disponible'}
            </pre>
          </div>
        </div>

        {/* Signature Pad */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Tu Firma
          </h2>
          <p className="text-sm text-slate-600 mb-4">
            Por favor dibuja tu firma en el recuadro de abajo usando tu mouse o dedo (en dispositivos táctiles).
          </p>

          <div className="border-2 border-slate-300 rounded-lg mb-4 bg-white">
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

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Agreement */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <label className="flex items-start">
            <input
              type="checkbox"
              className="mt-1 mr-3"
              required
            />
            <span className="text-sm text-slate-700">
              Al firmar este contrato, acepto los términos y condiciones especificados en el documento.
              Entiendo que esta firma tiene validez legal.
            </span>
          </label>
        </div>

        {/* Actions */}
        <div className="flex justify-end">
          <button
            onClick={handleSign}
            disabled={signing}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-300 font-semibold"
          >
            {signing ? 'Firmando...' : 'Firmar Contrato'}
          </button>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-slate-500">
          <p>Este enlace es de un solo uso y expirará después de firmar.</p>
        </div>
      </div>
    </div>
  );
}
