import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactElement, ReactNode } from 'react'

/**
 * Minimal wrapper that provides BrowserRouter for components using
 * useNavigate / useLocation / Link etc.
 */
function AllProviders({ children }: { children: ReactNode }) {
  return <BrowserRouter>{children}</BrowserRouter>
}

export function renderWithRouter(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options })
}

/**
 * Render with MemoryRouter + QueryClientProvider.
 * Creates a fresh QueryClient per call to prevent cache leakage between tests.
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: {
    initialEntries?: string[]
    renderOptions?: Omit<RenderOptions, 'wrapper'>
  },
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={options?.initialEntries ?? ['/']}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...options?.renderOptions }),
    queryClient,
  }
}
