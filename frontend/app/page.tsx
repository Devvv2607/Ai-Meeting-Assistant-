'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import ThemeToggle from '@/components/theme/ThemeToggle';

export default function LandingPage() {
  const router = useRouter();

  // If already logged in, skip the marketing page.
  useEffect(() => {
    if (typeof window !== 'undefined' && localStorage.getItem('access_token')) {
      router.replace('/dashboard');
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-bg">
      <ThemeToggle />

      {/* Header */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-8 py-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-[27px] w-[27px] items-center justify-center rounded-[7px] bg-accent">
            <span className="h-[9px] w-[9px] rounded-[2px] bg-lime" />
          </span>
          <span className="font-display text-[22px] font-semibold text-ink">Margin</span>
        </div>
        <button
          onClick={() => router.push('/login')}
          className="rounded-md border border-line-input px-5 py-2.5 text-[14.5px] font-semibold text-ink2 transition-colors hover:border-line-hover"
        >
          Sign in
        </button>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-8 pb-10 pt-12 lg:pt-20">
        <h1 className="font-display text-[clamp(40px,7vw,84px)] font-medium leading-[1.04] tracking-[-0.01em] text-ink">
          Be present.
          <br />
          We&apos;ll take the <em className="italic text-accent-ink">notes</em>.
        </h1>
        <p className="mt-7 max-w-xl text-[18px] leading-relaxed text-ink2">
          Margin quietly captures every meeting, surfaces the moments that matter, and answers your
          questions long after the room clears.
        </p>

        <div className="mt-9 flex flex-wrap items-center gap-3.5">
          <button
            onClick={() => router.push('/login')}
            className="rounded-md bg-accent px-7 py-3.5 text-[15px] font-semibold text-on-accent transition-transform hover:-translate-y-0.5 hover:bg-accent-hover"
          >
            Get started — it&apos;s free
          </button>
          <button
            onClick={() => router.push('/login')}
            className="rounded-md border border-line-input px-7 py-3.5 text-[15px] font-semibold text-ink2 transition-colors hover:border-line-hover"
          >
            Watch the demo
          </button>
        </div>

        <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-[12.5px] uppercase tracking-wide text-muted2">
          <span className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-lime" /> Live notes
          </span>
          <span className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-lime" /> Upload recordings
          </span>
          <span className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-lime" /> Ask across meetings
          </span>
        </div>
      </section>

      {/* Showcase */}
      <section className="mx-auto grid max-w-6xl gap-6 px-8 pb-24 lg:grid-cols-2">
        {/* Recent meetings preview */}
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-card">
          <div className="mb-4 font-mono text-[11px] uppercase tracking-wider text-muted2">
            Recent meetings
          </div>
          <div className="space-y-3">
            {[
              { mon: 'JUN', day: '25', title: 'Product sync — Q3 roadmap', tag: 'Weekly · Acme', dur: '48 min' },
              { mon: 'JUN', day: '24', title: 'Manager 1:1 with Dana', tag: 'Team', dur: '32 min' },
              { mon: 'JUN', day: '23', title: 'Customer discovery — Northwind', tag: 'Sales', dur: '38 min' },
            ].map((m) => (
              <div
                key={m.title}
                className="flex items-center gap-4 rounded-xl border border-line2 bg-surface3 px-4 py-3"
              >
                <div className="flex h-[46px] w-[46px] flex-col items-center justify-center rounded-lg border border-line bg-surface2">
                  <span className="font-mono text-[9px] text-muted2">{m.mon}</span>
                  <span className="font-display text-[20px] font-semibold leading-none text-accent-ink">
                    {m.day}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-display text-[16px] font-semibold text-ink">
                    {m.title}
                  </div>
                  <span className="mt-1 inline-block rounded-md bg-accent-soft px-2 py-0.5 text-[11.5px] text-accent-ink">
                    {m.tag}
                  </span>
                </div>
                <span className="font-mono text-[12px] text-muted3">{m.dur}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Ask Margin preview */}
        <div className="rounded-2xl border border-line bg-panel2 p-6 shadow-card">
          <div className="mb-4 flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-muted2">
            <span className="text-accent-ink">✦</span> Ask Margin
          </div>
          <div className="space-y-3">
            <div className="ml-auto max-w-[82%] rounded-[16px_16px_4px_16px] bg-accent px-4 py-2.5 text-[14.5px] text-on-accent">
              What deadlines do I have coming up?
            </div>
            <div className="max-w-[88%] rounded-[16px_16px_16px_4px] border border-line bg-surface3 px-4 py-3 text-[14.5px] leading-relaxed text-ink-soft">
              You have three: the Q3 launch is locked for Aug 14, onboarding copy is due Friday, and
              Dana wants the deck before next week.
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className="rounded-sm border border-accent-soft-border bg-accent-soft px-2 py-0.5 font-mono text-[11px] text-accent-ink">
                  ▸ Product sync · 19:05
                </span>
                <span className="rounded-sm border border-accent-soft-border bg-accent-soft px-2 py-0.5 font-mono text-[11px] text-accent-ink">
                  ▸ 1:1 · 04:12
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
