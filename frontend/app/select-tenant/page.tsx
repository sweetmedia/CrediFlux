'use client';

import { Building2, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Image from 'next/image';

export default function SelectTenantPage() {
  const tenants = [
    {
      name: 'Demo Company',
      subdomain: 'democompany',
      description: 'Cuenta de demostración',
      url: 'http://democompany.localhost:3000',
    },
    {
      name: 'Caproinsa SRL',
      subdomain: 'caproinsa',
      description: 'Desarrollo y pruebas',
      url: 'http://caproinsa.localhost:3000',
    },
    {
      name: 'AMS Fin',
      subdomain: 'amsfin',
      description: 'Cliente de prueba',
      url: 'http://amsfin.localhost:3000',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-6">
            <Image
              src="/logo.svg"
              alt="CrediFlux"
              width={200}
              height={50}
              className="h-12 w-auto"
              priority
            />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            CrediFlux SaaS Platform
          </h1>
          <p className="text-lg text-gray-600">
            Selecciona tu organización para continuar
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tenants.map((tenant) => (
            <a
              key={tenant.subdomain}
              href={tenant.url}
              className="block transition-all hover:scale-105"
            >
              <Card className="h-full cursor-pointer hover:shadow-lg border-2 hover:border-indigo-500">
                <CardHeader>
                  <div className="flex items-center justify-between mb-2">
                    <Building2 className="h-8 w-8 text-indigo-600" />
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                  <CardTitle className="text-xl">{tenant.name}</CardTitle>
                  <CardDescription>{tenant.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-gray-500 font-mono bg-gray-50 rounded px-3 py-2">
                    {tenant.subdomain}.localhost:3000
                  </div>
                </CardContent>
              </Card>
            </a>
          ))}
        </div>

        <div className="mt-12 text-center">
          <Card className="bg-yellow-50 border-yellow-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-center gap-2">
                <Building2 className="h-5 w-5" />
                Administración del Sistema
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">
                Para acceso administrativo del sistema SaaS (superusers y staff):
              </p>
              <a
                href="http://localhost:8000/admin/"
                className="inline-flex items-center justify-center px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
              >
                Ir al Admin del Sistema
                <ChevronRight className="ml-2 h-4 w-4" />
              </a>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            ¿No encuentras tu organización?{' '}
            <a href="mailto:support@crediflux.com" className="text-indigo-600 hover:underline">
              Contacta soporte
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
