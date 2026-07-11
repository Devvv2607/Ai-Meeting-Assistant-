'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/services/api';
import ThemeToggle from '@/components/theme/ThemeToggle';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await api.login(email, password);
      const token = res.data.access_token;
      localStorage.setItem('access_token', token);
      localStorage.setItem('mg-user', JSON.stringify({ email, full_name: email.split('@')[0] }));
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
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

      <div className="mx-auto grid max-w-6xl gap-10 px-8 pb-16 pt-6 lg:grid-cols-[54%_46%]">
        {/* Left: form */}
        <div className="max-w-md">
          <h1 className="font-display text-[clamp(30px,4vw,44px)] font-medium leading-[1.1] tracking-[-0.01em] text-ink">
            Every meeting, call &amp; conversation — <em className="italic text-accent-ink">remembered</em>.
          </h1>
          <p className="mt-4 text-[16px] leading-relaxed text-ink2">
            Sign in to capture, summarize, and ask across everything you record.
          </p>

          {error && (
            <div className="mt-6 rounded-lg border border-rec-border bg-rec-bg px-4 py-3 text-[14px] text-rec-ink">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="mt-7 space-y-3">
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
              placeholder="••••••••"
              autoComplete="current-password"
              className="w-full rounded-md border border-line-input bg-surface px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-line-hover placeholder:text-muted"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-accent px-5 py-3 text-[15px] font-semibold text-on-accent transition-transform hover:-translate-y-0.5 hover:bg-accent-hover disabled:opacity-50"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="my-5 flex items-center gap-3 text-[12px] text-muted2">
            <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
          </div>

          {/* Google sign-in: not supported by backend yet — disabled gracefully */}
          <button
            type="button"
            disabled
            title="Coming soon"
            className="flex w-full cursor-not-allowed items-center justify-center gap-2.5 rounded-md border border-line-input bg-surface px-5 py-3 text-[15px] font-semibold text-muted opacity-70"
          >
            <span className="font-bold">G</span> Continue with Google
          </button>

          <p className="mt-6 text-[14px] text-ink2">
            New to Margin?{' '}
            <Link href="/register" className="font-semibold text-accent-ink hover:underline">
              Create an account
            </Link>
          </p>
        </div>

        {/* Right: showcase */}
        <div className="hidden rounded-2xl border border-line bg-surface2 p-7 lg:flex lg:flex-col lg:justify-center">
          <div className="space-y-4">
            <div className="rounded-xl border border-line bg-surface3 p-5 shadow-card">
              <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted2">
                Margin notes
              </div>
              <div className="font-display text-[18px] font-semibold text-ink">
                Launch date locked for Aug 14
              </div>
              <p className="mt-1.5 text-[14px] leading-relaxed text-ink2">
                Team aligned on scope; onboarding copy owned by Maya, due Friday.
              </p>
            </div>
            <div className="ml-auto max-w-[88%] rounded-[16px_16px_4px_16px] bg-accent px-4 py-2.5 text-[14px] text-on-accent">
              What did we decide about pricing?
            </div>
          </div>
          <p className="mt-6 text-[14px] text-ink3">
            Your notes, enhanced — the moment the meeting ends.
          </p>
        </div>
      </div>
    </div>
  );
}
