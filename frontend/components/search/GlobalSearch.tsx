'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { searchAPI, SearchResult } from '@/lib/api/search';
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Search,
  Loader2,
  Users,
  FileText,
  DollarSign,
  FileSignature,
  Command,
} from 'lucide-react';

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

const TYPE_ICONS: Record<string, React.ComponentType<any>> = {
  customer: Users,
  loan: FileText,
  payment: DollarSign,
  contract: FileSignature,
};

const TYPE_LABELS: Record<string, string> = {
  customer: 'Cliente',
  loan: 'Prestamo',
  payment: 'Pago',
  contract: 'Contrato',
};

const TYPE_COLORS: Record<string, string> = {
  customer: 'bg-purple-100 text-purple-800',
  loan: 'bg-blue-100 text-blue-800',
  payment: 'bg-green-100 text-green-800',
  contract: 'bg-orange-100 text-orange-800',
};

export function GlobalSearch({ isOpen, onClose }: GlobalSearchProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Focus input when dialog opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
    } else {
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Debounced search
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }

    const timeoutId = setTimeout(async () => {
      setIsLoading(true);
      try {
        const response = await searchAPI.globalSearch(query);

        // Flatten results into a single array
        const allResults: SearchResult[] = [
          ...response.results.customers,
          ...response.results.loans,
          ...response.results.payments,
          ...response.results.contracts,
        ];

        setResults(allResults);
        setSelectedIndex(0);
      } catch (error) {
        console.error('Search error:', error);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [query]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIndex]) {
      e.preventDefault();
      router.push(results[selectedIndex].url);
      onClose();
    } else if (e.key === 'Escape') {
      onClose();
    }
  }, [results, selectedIndex, router, onClose]);

  const handleSelect = (result: SearchResult) => {
    router.push(result.url);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] p-0 gap-0 overflow-hidden">
        <DialogTitle className="sr-only">Busqueda Global</DialogTitle>
        {/* Search Input */}
        <div className="flex items-center border-b px-4">
          <Search className="h-5 w-5 text-slate-400 mr-3" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar clientes, prestamos, pagos, contratos..."
            className="flex-1 border-0 focus-visible:ring-0 text-lg py-6"
          />
          {isLoading && <Loader2 className="h-5 w-5 animate-spin text-slate-400" />}
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto">
          {query.length < 2 ? (
            <div className="p-8 text-center text-slate-500">
              <Command className="h-12 w-12 mx-auto mb-3 text-slate-300" />
              <p>Escribe al menos 2 caracteres para buscar</p>
              <p className="text-sm mt-2">
                Usa <kbd className="px-2 py-1 bg-slate-100 rounded text-xs">Esc</kbd> para cerrar
              </p>
            </div>
          ) : results.length === 0 && !isLoading ? (
            <div className="p-8 text-center text-slate-500">
              <Search className="h-12 w-12 mx-auto mb-3 text-slate-300" />
              <p>No se encontraron resultados para &quot;{query}&quot;</p>
            </div>
          ) : (
            <div className="py-2">
              {results.map((result, index) => {
                const Icon = TYPE_ICONS[result.type] || FileText;
                const isSelected = index === selectedIndex;

                return (
                  <button
                    key={`${result.type}-${result.id}`}
                    onClick={() => handleSelect(result)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 text-left transition-colors
                      ${isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'}
                    `}
                  >
                    <div className={`p-2 rounded-lg ${TYPE_COLORS[result.type] || 'bg-slate-100'}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 truncate">
                          {result.title}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {TYPE_LABELS[result.type] || result.type}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-500 truncate">
                        {result.subtitle}
                      </p>
                    </div>
                    {isSelected && (
                      <kbd className="px-2 py-1 bg-slate-100 rounded text-xs text-slate-500">
                        Enter
                      </kbd>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-4 py-2 flex items-center justify-between text-xs text-slate-500 bg-slate-50">
          <div className="flex gap-4">
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border rounded mr-1">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-white border rounded mr-1">↓</kbd>
              para navegar
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border rounded mr-1">Enter</kbd>
              para seleccionar
            </span>
          </div>
          <span>
            {results.length} resultado{results.length !== 1 && 's'}
          </span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
