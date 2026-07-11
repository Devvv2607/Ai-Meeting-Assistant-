'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Sidebar from './Sidebar';
import ThemeToggle from '@/components/theme/ThemeToggle';

/**
 * Authenticated app shell: sidebar + scrollable main area + theme toggle.
 * Redirects to /login when no access token is present.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) router.replace('/login');
  }, [router]);

  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <main className="mgScroll relative flex-1 overflow-y-auto">
        <ThemeToggle />
        {children}
      </main>
    </div>
  );
}
