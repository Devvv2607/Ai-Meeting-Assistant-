'use client';

import { useEffect, useRef, useState } from 'react';
import { logout } from '@/services/auth';

export interface ProfileUser {
  name: string;
  role: string;
}

function initialsFrom(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 0) return 'M';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

interface MenuItem {
  icon: string;
  label: string;
  onSelect: () => void;
  destructive?: boolean;
}

/**
 * Sidebar user card + dropdown that opens above it (Profile / Settings /
 * Log Out). Closes on outside click and Escape; fade + scale animation.
 */
export default function ProfileMenu({ user }: { user: ProfileUser }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const items: MenuItem[] = [
    { icon: '👤', label: 'Profile', onSelect: () => setOpen(false) },
    { icon: '⚙️', label: 'Settings', onSelect: () => setOpen(false) },
    { icon: '🚪', label: 'Log Out', onSelect: logout, destructive: true },
  ];

  return (
    <div ref={rootRef} className="relative mt-auto border-t border-line pt-4">
      {/* Dropdown — anchored above the card */}
      <div
        role="menu"
        aria-hidden={!open}
        className={`absolute bottom-full left-0 right-0 z-40 mb-2 origin-bottom rounded-xl border border-line bg-surface p-1.5 shadow-card transition-all duration-150 ease-out ${
          open
            ? 'pointer-events-auto scale-100 opacity-100'
            : 'pointer-events-none scale-95 opacity-0'
        }`}
      >
        {items.map((item, i) => (
          <div key={item.label}>
            {item.destructive && i > 0 && (
              <div className="mx-2 my-1.5 h-px bg-line" />
            )}
            <button
              type="button"
              role="menuitem"
              tabIndex={open ? 0 : -1}
              onClick={item.onSelect}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[14px] font-medium transition-colors ${
                item.destructive
                  ? 'text-rec-ink hover:bg-rec-bg'
                  : 'text-ink2 hover:bg-surface2 hover:text-ink'
              }`}
            >
              <span className="w-[18px] text-center text-[15px]">{item.icon}</span>
              {item.label}
            </button>
          </div>
        ))}
      </div>

      {/* User card (trigger) */}
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`flex w-full items-center gap-2.5 rounded-[10px] px-1.5 py-1.5 text-left transition-colors ${
          open ? 'bg-surface2' : 'hover:bg-surface2'
        }`}
      >
        <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-accent text-[13px] font-bold text-lime">
          {initialsFrom(user.name)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13.5px] font-semibold text-ink">{user.name}</div>
          <div className="truncate text-[12px] text-ink3">{user.role}</div>
        </div>
        <span
          aria-hidden
          className={`pr-1 text-[11px] text-muted transition-transform duration-150 ${
            open ? 'rotate-180' : ''
          }`}
        >
          ▲
        </span>
      </button>
    </div>
  );
}
