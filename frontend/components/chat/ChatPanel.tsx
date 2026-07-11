'use client';

import { useEffect, useRef, useState } from 'react';

export interface Citation {
  label: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  cites?: Citation[];
}

interface ChatPanelProps {
  /** Resolver that calls the backend and returns the assistant answer. */
  resolve: (question: string) => Promise<{ answer: string; cites?: Citation[] }>;
  suggestions?: string[];
  placeholder?: string;
  initialMessages?: ChatMessage[];
  /** Render compact (meeting sidebar) vs roomy (full Ask page). */
  variant?: 'sidebar' | 'page';
}

export default function ChatPanel({
  resolve,
  suggestions = [],
  placeholder = 'Ask a question…',
  initialMessages = [],
  variant = 'sidebar',
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || thinking) return;
    setMessages((m) => [...m, { role: 'user', text: q }]);
    setInput('');
    setThinking(true);
    try {
      const { answer, cites } = await resolve(q);
      setMessages((m) => [...m, { role: 'assistant', text: answer, cites }]);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Sorry — I could not answer that just now.';
      setMessages((m) => [...m, { role: 'assistant', text: detail }]);
    } finally {
      setThinking(false);
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="mgScroll flex-1 overflow-y-auto pr-1">
        {empty && suggestions.length > 0 && (
          <div className="space-y-2">
            <div className="mb-1 font-mono text-[11px] uppercase tracking-wider text-muted2">
              Try asking…
            </div>
            <div className={variant === 'page' ? 'grid gap-2 sm:grid-cols-2' : 'space-y-2'}>
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="w-full rounded-lg border border-line bg-surface3 px-3.5 py-2.5 text-left text-[13.5px] text-ink2 transition-colors hover:border-line-hover hover:text-ink"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={
                  msg.role === 'user'
                    ? 'max-w-[82%] rounded-[16px_16px_4px_16px] bg-accent px-4 py-2.5 text-[14.5px] leading-relaxed text-on-accent'
                    : 'max-w-[88%] rounded-[16px_16px_16px_4px] border border-line bg-surface3 px-4 py-3 text-[14.5px] leading-relaxed text-ink-soft'
                }
              >
                <span className="whitespace-pre-wrap">{msg.text}</span>
                {msg.cites && msg.cites.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {msg.cites.map((c, ci) => (
                      <span
                        key={ci}
                        className="rounded-sm border border-accent-soft-border bg-accent-soft px-2 py-0.5 font-mono text-[11px] text-accent-ink"
                      >
                        ▸ {c.label}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {thinking && (
            <div className="flex justify-start">
              <div className="flex items-center gap-1.5 rounded-[16px_16px_16px_4px] border border-line bg-surface3 px-4 py-3.5">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-[7px] w-[7px] rounded-full bg-dot animate-dot"
                    style={{ animationDelay: `${i * 0.16}s` }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {/* Input */}
      <div className="mt-3 flex items-center gap-2 rounded-pill border border-line-input bg-surface3 px-2 py-1.5 shadow-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') send(input);
          }}
          placeholder={placeholder}
          className="flex-1 bg-transparent px-3 py-1.5 text-[14.5px] text-ink outline-none placeholder:text-muted"
        />
        <button
          onClick={() => send(input)}
          disabled={!input.trim() || thinking}
          aria-label="Send"
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-accent text-on-accent transition-colors hover:bg-accent-hover disabled:opacity-40"
        >
          ↑
        </button>
      </div>
    </div>
  );
}
