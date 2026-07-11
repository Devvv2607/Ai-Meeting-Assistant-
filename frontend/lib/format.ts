const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

/** Seconds -> M:SS (or H:MM:SS when over an hour). */
export function fmtClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}

/** Human duration label, e.g. "48 min" / "1h 12m". */
export function fmtDuration(totalSeconds?: number | null): string {
  if (!totalSeconds || totalSeconds <= 0) return '—';
  const mins = Math.round(totalSeconds / 60);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

/** ISO date -> { mon: 'JUN', day: '25' } for the date badge. */
export function dateBadge(iso?: string): { mon: string; day: string } {
  const d = iso ? new Date(iso) : new Date();
  return { mon: MONTHS[d.getMonth()] || 'JAN', day: String(d.getDate()) };
}

/** Long date line, e.g. "THURSDAY, JUNE 25". */
export function longDate(date = new Date()): string {
  return date
    .toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
    .toUpperCase();
}

/** Time-of-day greeting. */
export function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

/** First name from a name/email for the greeting. */
export function firstName(nameOrEmail?: string): string {
  if (!nameOrEmail) return 'there';
  const base = nameOrEmail.includes('@') ? nameOrEmail.split('@')[0] : nameOrEmail;
  const first = base.split(/[\s._-]+/)[0] || base;
  return first.charAt(0).toUpperCase() + first.slice(1);
}
