'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/contexts/AuthContext';
import { ConfigProvider } from '@/lib/contexts/ConfigContext';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider>
        <AuthProvider>{children}</AuthProvider>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
