import { useEffect } from 'react';
import { useThemeStore } from './store/useThemeStore';
import App from './App';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import './index.css';

const queryClient = new QueryClient();

function Root() {
  const { theme } = useThemeStore();

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')!).render(<Root />);
