'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/services/api';
import AppShell from '@/components/layout/AppShell';
import ChatPanel, { ChatMessage, Citation } from '@/components/chat/ChatPanel';
import { fmtClock, fmtDuration, dateBadge } from '@/lib/format';

interface Segment {
  id: number;
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
}

interface SummaryData {
  summary: string;
  key_points: string[];
  action_items: string[];
  sentiment: string;
}

function sourcesToCites(sources: any[]): Citation[] {
  if (!Array.isArray(sources)) return [];
  return sources
    .map((s) => {
      const label = s.time || s.filename || s.speaker || 'source';
      return { label: String(label) };
    })
    .slice(0, 4);
}

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = Number(params?.id);

  const [meeting, setMeeting] = useState<any>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [checked, setChecked] = useState<Record<number, boolean>>({});

  // Transcript translation. The stored transcript is always English; the user
  // can translate the displayed view into any supported language on demand.
  const [languages, setLanguages] = useState<Record<string, string>>({});
  const [transLang, setTransLang] = useState('en');
  const [translatedSegs, setTranslatedSegs] = useState<Segment[] | null>(null);
  const [translating, setTranslating] = useState(false);

  useEffect(() => {
    if (!meetingId) return;

    const load = async () => {
      try {
        const [mRes, tRes] = await Promise.all([
          api.getMeeting(meetingId),
          api.getTranscript(meetingId),
        ]);
        setMeeting(mRes.data);
        setSegments(tRes.data?.segments || []);
      } catch {
        /* meeting may not exist */
      }

      // Summary may 400 if no transcript yet — tolerate it.
      try {
        const sRes = await api.getSummary(meetingId);
        setSummary(sRes.data);
      } catch {
        setSummary(null);
      }

      // Supported translation languages (for the transcript translate control).
      try {
        const lRes = await api.getSupportedLanguages();
        setLanguages(lRes.data?.languages || {});
      } catch {
        /* translation optional */
      }

      // Prefill chat history.
      try {
        const hRes = await api.getChatHistory(meetingId);
        const msgs: ChatMessage[] = (hRes.data?.messages || []).map((m: any) => ({
          role: m.role === 'user' ? 'user' : 'assistant',
          text: m.content,
          cites: sourcesToCites(m.sources),
        }));
        setHistory(msgs);
      } catch {
        /* ignore */
      }

      setLoading(false);
    };

    load();
  }, [meetingId]);

  const resolve = async (question: string) => {
    const res = await api.askQuestion(meetingId, question);
    return { answer: res.data.answer as string, cites: sourcesToCites(res.data.sources) };
  };

  const translate = async (lang: string) => {
    setTransLang(lang);
    if (lang === 'en') {
      setTranslatedSegs(null); // show the original English transcript
      return;
    }
    setTranslating(true);
    try {
      const res = await api.translateTranscript(meetingId, lang);
      const segs: Segment[] = (res.data?.segments || []).map((s: any, i: number) => ({
        id: segments[i]?.id ?? i,
        speaker: s.speaker,
        text: s.text,
        start_time: s.start_time,
        end_time: s.end_time,
      }));
      setTranslatedSegs(segs);
    } catch {
      setTranslatedSegs(null);
      setTransLang('en');
    } finally {
      setTranslating(false);
    }
  };

  const shownSegments = translatedSegs ?? segments;

  if (loading) {
    return (
      <AppShell>
        <div className="px-10 py-12">
          <div className="h-8 w-64 animate-pulse rounded bg-surface2" />
          <div className="mt-6 h-40 animate-pulse rounded-xl bg-surface2" />
        </div>
      </AppShell>
    );
  }

  if (!meeting) {
    return (
      <AppShell>
        <div className="px-10 py-12">
          <button onClick={() => router.push('/dashboard')} className="text-[14px] text-accent-ink hover:underline">
            ← Back to home
          </button>
          <p className="mt-6 text-[16px] text-ink2">Meeting not found.</p>
        </div>
      </AppShell>
    );
  }

  const badge = dateBadge(meeting.created_at);
  const status = (meeting.status || '').toLowerCase();

  return (
    <AppShell>
      <div className="grid gap-0 lg:grid-cols-[1fr_396px]">
        {/* Main content */}
        <div className="mgScroll px-10 py-10">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-[13.5px] text-ink2 transition-colors hover:text-ink"
          >
            ← Back to home
          </button>

          <div className="mt-5 flex items-center gap-2.5">
            <span className="font-mono text-[11.5px] uppercase tracking-wider text-muted2">
              {badge.mon} {badge.day}
            </span>
            {status === 'completed' && (
              <span className="flex items-center gap-1.5 rounded-md bg-ok-bg px-2.5 py-1 text-[11.5px] text-ok-ink">
                <span className="h-1.5 w-1.5 rounded-full bg-ok-dot" /> Summarized
              </span>
            )}
            {status === 'processing' && (
              <span className="rounded-md bg-accent-soft px-2.5 py-1 text-[11.5px] text-accent-ink">
                Processing…
              </span>
            )}
          </div>

          <h1 className="mt-3 max-w-[760px] font-display text-[clamp(28px,4vw,40px)] font-medium leading-tight tracking-[-0.01em] text-ink">
            {meeting.title}
          </h1>

          <div className="mt-3 flex items-center gap-4 font-mono text-[12.5px] text-muted3">
            <span>{fmtDuration(meeting.duration)}</span>
            {summary?.sentiment && <span className="capitalize">· {summary.sentiment}</span>}
          </div>

          {/* Key moments */}
          {summary?.key_points && summary.key_points.length > 0 && (
            <section className="mt-9 max-w-[760px]">
              <h2 className="mb-3 font-display text-[20px] font-semibold text-ink">Key points</h2>
              <ul className="space-y-3 border-l-2 border-line pl-5">
                {summary.key_points.map((kp, i) => (
                  <li key={i} className="relative">
                    <span className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full bg-lime" />
                    <p className="text-[15px] leading-relaxed text-ink-soft">{kp}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Minutes of the meeting */}
          <section className="mt-9 max-w-[760px]">
            <h2 className="mb-3 font-display text-[20px] font-semibold text-ink">
              Minutes of the meeting
            </h2>
            {summary?.summary ? (
              <p className="text-[15.5px] leading-[1.7] text-ink-soft">{summary.summary}</p>
            ) : (
              <p className="rounded-lg border border-line bg-surface px-4 py-3 text-[14px] text-ink3">
                {status === 'completed'
                  ? 'No minutes available for this meeting.'
                  : 'Minutes will appear once transcription finishes.'}
              </p>
            )}
          </section>

          {/* Action items */}
          {summary?.action_items && summary.action_items.length > 0 && (
            <section className="mt-9 max-w-[760px]">
              <h2 className="mb-3 font-display text-[20px] font-semibold text-ink">Action items</h2>
              <div className="space-y-2">
                {summary.action_items.map((a, i) => (
                  <label
                    key={i}
                    className="flex cursor-pointer items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3"
                  >
                    <button
                      type="button"
                      onClick={() => setChecked((c) => ({ ...c, [i]: !c[i] }))}
                      className={`mt-0.5 flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center rounded-[5px] border text-[11px] ${
                        checked[i]
                          ? 'border-accent bg-accent text-on-accent'
                          : 'border-line-input bg-surface3 text-transparent'
                      }`}
                    >
                      ✓
                    </button>
                    <span
                      className={`text-[14.5px] leading-relaxed ${
                        checked[i] ? 'text-ink3 line-through' : 'text-ink-soft'
                      }`}
                    >
                      {a}
                    </span>
                  </label>
                ))}
              </div>
            </section>
          )}

          {/* Transcript */}
          <section className="mt-9 max-w-[760px]">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-[20px] font-semibold text-ink">Full transcript</h2>
              {segments.length > 0 && Object.keys(languages).length > 0 && (
                <div className="flex items-center gap-2">
                  {translating && (
                    <span className="h-3.5 w-3.5 rounded-full border-2 border-line-hover border-t-accent animate-spin-mg" />
                  )}
                  <label className="font-mono text-[11px] uppercase tracking-wider text-muted2">
                    Translate
                  </label>
                  <select
                    value={transLang}
                    disabled={translating}
                    onChange={(e) => translate(e.target.value)}
                    className="rounded-md border border-line-input bg-surface px-2.5 py-1.5 text-[13px] text-ink outline-none focus:border-line-hover disabled:opacity-50"
                  >
                    <option value="en">English (original)</option>
                    {Object.entries(languages)
                      .filter(([code]) => code !== 'en')
                      .map(([code, name]) => (
                        <option key={code} value={code}>
                          {name}
                        </option>
                      ))}
                  </select>
                </div>
              )}
            </div>
            {transLang !== 'en' && !translating && (
              <p className="mb-3 text-[12.5px] text-ink3">
                Showing a machine translation of the English transcript. Speaker
                labels and timings are unchanged.
              </p>
            )}
            {shownSegments.length === 0 ? (
              <p className="rounded-lg border border-line bg-surface px-4 py-3 text-[14px] text-ink3">
                No transcript available yet.
              </p>
            ) : (
              <div className="space-y-4">
                {shownSegments.map((seg) => (
                  <div key={seg.id} className="border-b border-line2 pb-3">
                    <div className="mb-1 flex items-center gap-2.5">
                      <span className="text-[13.5px] font-semibold text-accent-ink">
                        {seg.speaker || 'Speaker'}
                      </span>
                      <span className="font-mono text-[11.5px] text-muted3">
                        {fmtClock(seg.start_time)}
                      </span>
                    </div>
                    <p className="text-[14.5px] leading-relaxed text-ink-soft">{seg.text}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Q&A sidebar */}
        <aside className="sticky top-0 hidden h-screen flex-col border-l border-line bg-panel2 p-5 lg:flex">
          <div className="mb-3">
            <div className="flex items-center gap-2 font-display text-[17px] font-semibold text-ink">
              <span className="text-accent-ink">✦</span> Ask this meeting
            </div>
            <p className="mt-1 text-[13px] text-ink3">
              Answers are grounded in this meeting&apos;s transcript.
            </p>
          </div>
          <div className="min-h-0 flex-1">
            <ChatPanel
              resolve={resolve}
              initialMessages={history}
              placeholder="Ask about this meeting…"
              suggestions={
                history.length === 0
                  ? ['Summarize the key decisions', 'List my action items', 'What deadlines were set?']
                  : []
              }
            />
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
