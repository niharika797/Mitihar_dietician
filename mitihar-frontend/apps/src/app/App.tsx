import React from 'react';
import { RouterProvider } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { router } from './routes.tsx';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,        // 1 minute — prevents hammering the API
      retry: 1,                    // retry failed requests once before erroring
      refetchOnWindowFocus: false, // doctors switch tabs constantly; no surprise refetches
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: '14px',
            borderRadius: '8px',
            border: '1px solid #E5E7EB',
          },
          classNames: {
            success: 'text-[#15803d]',
          },
        }}
      />
    </QueryClientProvider>
  );
}
