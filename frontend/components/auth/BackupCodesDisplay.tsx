'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Copy, Check, Download } from 'lucide-react';

interface BackupCodesDisplayProps {
  codes: string[];
}

export function BackupCodesDisplay({ codes }: BackupCodesDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const text = codes.join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const text = `CrediFlux - Codigos de Respaldo 2FA\n${'='.repeat(40)}\n\nGuarda estos codigos en un lugar seguro.\nCada codigo solo puede usarse una vez.\n\n${codes.join('\n')}\n\nGenerado: ${new Date().toLocaleString()}`;

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'crediflux-backup-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 p-4 bg-slate-50 rounded-lg border">
        {codes.map((code, index) => (
          <code
            key={index}
            className="text-center py-2 px-3 bg-white rounded border font-mono text-sm"
          >
            {code}
          </code>
        ))}
      </div>

      <div className="flex gap-2 justify-center">
        <Button variant="outline" size="sm" onClick={handleCopy}>
          {copied ? (
            <>
              <Check className="h-4 w-4 mr-2" />
              Copiado
            </>
          ) : (
            <>
              <Copy className="h-4 w-4 mr-2" />
              Copiar
            </>
          )}
        </Button>
        <Button variant="outline" size="sm" onClick={handleDownload}>
          <Download className="h-4 w-4 mr-2" />
          Descargar
        </Button>
      </div>
    </div>
  );
}
