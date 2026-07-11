'use client';

import { useEffect, useRef, useState } from 'react';
import { api } from '@/services/api';
import AppShell from '@/components/layout/AppShell';
import ChatPanel, { Citation } from '@/components/chat/ChatPanel';

interface MeetingItem {
  id: number;
  title: string;
  status: string;
  created_at: string;
}

function sourcesToCites(sources: any[], meetingTitle?: string): Citation[] {
  if (!Array.isArray(sources)) return [];
  return sources
    .map((s) => {
      const t = s.time || s.speaker || s.filename || '';
      const label = meetingTitle && t ? `${meetingTitle} · ${t}` : String(t || meetingTitle || 'source');
      return { label };
    })
    .slice(0, 4);
}

export default function AskMarginPage() {
  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const targetRef = useRef<MeetingItem | null>(null);
  // The in-flight meetings load, so resolve() can await it instead of racing it.
  const loadRef = useRef<Promise<void> | null>(null);

  useEffect(() => {
    loadRef.current = api
      .getMeetings(0, 20)
      .then((res) => {
        const list: MeetingItem[] = res.data || [];
        setMeetings(list);
        // Prefer the most recent completed meeting (it has a transcript to answer from).
        targetRef.current =
          list.find((m) => (m.status || '').toLowerCase() === 'completed') || list[0] || null;
      })
      .catch(() => setMeetings([]))
      .finally(() => setLoaded(true));
  }, []);

  const resolve = async (question: string) => {
    // Wait for the initial meetings load so we never falsely report "no meetings".
    if (loadRef.current) {
      try {
        await loadRef.current;
      } catch {
        /* ignore */
      }
    }
    const target = targetRef.current;
    if (!target) {
      return {
        answer:
          "You don't have any meetings yet. Record a live meeting or upload one, then come back and ask across them.",
      };
    }
    const res = await api.askQuestion(target.id, question);
    return {
      answer: res.data.answer as string,
      cites: sourcesToCites(res.data.sources, target.title),
    };
  };

  return (
    <AppShell>
      <div className="mx-auto flex h-screen max-w-3xl flex-col px-10 py-10">
        <div className="mb-5">
          <div className="mb-2 inline-flex items-center gap-2 rounded-md bg-accent-soft px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-accent-ink">
            <span>✦</span> Context: {meetings.length} meeting{meetings.length === 1 ? '' : 's'}
          </div>
          <h1 className="font-display text-[clamp(26px,3.5vw,38px)] font-medium tracking-[-0.01em] text-ink">
            Ask across your meetings.
          </h1>
          {loaded && targetRef.current && (
            <p className="mt-2 text-[13px] text-ink3">
              Answering from your most recent meeting,{' '}
              <span className="text-ink2">“{targetRef.current.title}”</span>. Cross-meeting search is
              coming soon.
            </p>
          )}
        </div>

        <div className="min-h-0 flex-1">
          <ChatPanel
            resolve={resolve}
            variant="page"
            placeholder="Ask anything about your meetings…"
            suggestions={[
              'What deadlines do I have coming up?',
              'Summarize the key decisions',
              'What action items are assigned to me?',
              'What was the most important moment?',
            ]}
          />
        </div>
      </div>
    </AppShell>
  );
}
