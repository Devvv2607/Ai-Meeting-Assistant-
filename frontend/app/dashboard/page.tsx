'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/services/api';
import AppShell from '@/components/layout/AppShell';
import { dateBadge, fmtDuration, greeting, longDate, firstName } from '@/lib/format';

interface MeetingItem {
  id: number;
  title: string;
  status: string;
  duration?: number | null;
  created_at: string;
}

const STATUS_STYLE: Record<string, string> = {
  completed: 'bg-ok-bg text-ok-ink',
  processing: 'bg-accent-soft text-accent-ink',
  pending: 'bg-surface2 text-ink3',
  failed: 'bg-rec-bg text-rec-ink',
};

export default function DashboardPage() {
  const router = useRouter();
  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('there');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('mg-user');
      if (raw) {
        const u = JSON.parse(raw);
        setName(firstName(u.full_name || u.name || u.email));
      }
    } catch {
      /* ignore */
    }

    api
      .getMeetings(0, 20)
      .then((res) => setMeetings(res.data || []))
      .catch(() => setMeetings([]))
      .finally(() => setLoading(false));
  }, []);

  const actionCards = [
    {
      key: 'live',
      title: 'Start a live meeting',
      blurb: 'Capture notes as it happens — no bot in the call.',
      icon: <span className="h-3 w-3 rounded-full bg-lime animate-pulse-mg" />,
      primary: true,
      onClick: () => router.push('/live-meeting'),
    },
    {
      key: 'upload',
      title: 'Upload a recording',
      blurb: 'Drop in audio or video and get a full summary.',
      icon: <span className="text-[20px] text-accent-ink">↑</span>,
      primary: false,
      onClick: () => router.push('/upload'),
    },
    {
      key: 'ask',
      title: 'Ask your meetings',
      blurb: "Chat across everything you've ever recorded.",
      icon: <span className="text-[20px] text-accent-ink">✦</span>,
      primary: false,
      onClick: () => router.push('/ask'),
    },
  ];

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl px-10 py-12">
        {/* Greeting */}
        <div className="font-mono text-[11px] uppercase tracking-wider text-muted2">{longDate()}</div>
        <h1 className="mt-1 font-display text-[clamp(28px,4vw,40px)] font-medium tracking-[-0.01em] text-ink">
          {greeting()}, {name}.
        </h1>

        {/* Action cards */}
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {actionCards.map((c) => (
            <button
              key={c.key}
              onClick={c.onClick}
              className={`flex min-h-[172px] flex-col justify-between rounded-2xl p-6 text-left transition-transform hover:-translate-y-1 hover:shadow-cardHover ${
                c.primary
                  ? 'bg-accent text-on-accent'
                  : 'border border-line bg-surface text-ink'
              }`}
            >
              <span
                className={`flex h-10 w-10 items-center justify-center rounded-md ${
                  c.primary ? 'bg-[rgba(255,255,255,0.12)]' : 'bg-accent-soft'
                }`}
              >
                {c.icon}
              </span>
              <div>
                <div className="font-display text-[19px] font-semibold leading-snug">{c.title}</div>
                <p
                  className={`mt-1.5 text-[13.5px] leading-relaxed ${
                    c.primary ? 'text-[rgba(243,240,230,0.82)]' : 'text-ink2'
                  }`}
                >
                  {c.blurb}
                </p>
              </div>
            </button>
          ))}
        </div>

        {/* Recent meetings */}
        <div className="mt-12">
          <h2 className="mb-4 font-display text-[20px] font-semibold text-ink">Recent meetings</h2>

          {loading ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-[78px] animate-pulse rounded-xl border border-line bg-surface2" />
              ))}
            </div>
          ) : meetings.length === 0 ? (
            <div className="rounded-xl border border-dashed border-line-input bg-surface px-6 py-10 text-center">
              <p className="text-[15px] text-ink2">No meetings yet.</p>
              <p className="mt-1 text-[13.5px] text-ink3">
                Start a live meeting or upload a recording to see it here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {meetings.map((m) => {
                const badge = dateBadge(m.created_at);
                const status = (m.status || '').toLowerCase();
                return (
                  <button
                    key={m.id}
                    onClick={() => router.push(`/meeting/${m.id}`)}
                    className="flex w-full items-center gap-5 rounded-xl border border-line bg-surface px-5 py-4 text-left transition-all hover:translate-x-0.5 hover:border-line-hover"
                  >
                    <div className="flex h-[46px] w-[46px] flex-shrink-0 flex-col items-center justify-center rounded-lg border border-line bg-surface2">
                      <span className="font-mono text-[9px] text-muted2">{badge.mon}</span>
                      <span className="font-display text-[20px] font-semibold leading-none text-accent-ink">
                        {badge.day}
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-display text-[18px] font-semibold text-ink">
                        {m.title}
                      </div>
                      <span
                        className={`mt-1 inline-block rounded-md px-2 py-0.5 text-[11.5px] capitalize ${
                          STATUS_STYLE[status] || 'bg-surface2 text-ink3'
                        }`}
                      >
                        {status || 'unknown'}
                      </span>
                    </div>
                    <span className="font-mono text-[12px] text-muted3">{fmtDuration(m.duration)}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
