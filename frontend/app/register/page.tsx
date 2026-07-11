'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/services/api';
import ThemeToggle from '@/components/theme/ThemeToggle';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.register(email, password, fullName || undefined);
      // Auto sign-in after registration
      const res = await api.login(email, password);
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem(
        'mg-user',
        JSON.stringify({ email, full_name: fullName || email.split('@')[0] })
      );
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not create your account.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg">
      <ThemeToggle />

      <div className="mx-auto flex max-w-6xl items-center gap-2.5 px-8 py-6">
        <span className="flex h-[27px] w-[27px] items-center justify-center rounded-[7px] bg-accent">
          <span className="h-[9px] w-[9px] rounded-[2px] bg-lime" />
        </span>
        <span className="font-display text-[22px] font-semibold text-ink">Margin</span>
      </div>

      <div className="mx-auto max-w-md px-8 pb-16 pt-6">
        <h1 className="font-display text-[34px] font-medium leading-tight tracking-[-0.01em] text-ink">
          Create your account
        </h1>
        <p className="mt-3 text-[15px] text-ink2">Start capturing meetings in minutes.</p>

        {error && (
          <div className="mt-6 rounded-lg border border-rec-border bg-rec-bg px-4 py-3 text-[14px] text-rec-ink">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="mt-7 space-y-3">
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Full name"
            autoComplete="name"
            className="w-full rounded-md border border-line-input bg-surface px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-line-hover placeholder:text-muted"
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@work.com"
            autoComplete="email"
            className="w-full rounded-md border border-line-input bg-surface px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-line-hover placeholder:text-muted"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a password"
            autoComplete="new-password"
            className="w-full rounded-md border border-line-input bg-surface px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-line-hover placeholder:text-muted"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-accent px-5 py-3 text-[15px] font-semibold text-on-accent transition-transform hover:-translate-y-0.5 hover:bg-accent-hover disabled:opacity-50"
          >
            {loading ? 'Creating…' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-[14px] text-ink2">
          Already have an account?{' '}
          <Link href="/login" className="font-semibold text-accent-ink hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
