'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import ProfileMenu, { ProfileUser } from './ProfileMenu';

interface NavItem {
  key: string;
  label: string;
  icon: string;
  href: string;
}

const NAV: NavItem[] = [
  { key: 'home', label: 'Home', icon: '⌂', href: '/dashboard' },
  { key: 'ask', label: 'Ask Margin', icon: '✦', href: '/ask' },
  { key: 'library', label: 'Library', icon: '▤', href: '/dashboard' },
];

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<ProfileUser>({
    name: 'Your account',
    role: 'Member',
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem('mg-user');
      if (raw) {
        const u = JSON.parse(raw);
        setUser({
          name: u.full_name || u.name || u.email || 'Your account',
          role: u.role || 'Member',
        });
      }
    } catch {
      /* ignore */
    }
  }, []);

  const isActive = (item: NavItem) =>
    item.key === 'home' ? pathname?.startsWith('/dashboard') : pathname?.startsWith(item.href);

  return (
    <aside className="sticky top-0 flex h-screen w-[248px] flex-shrink-0 flex-col border-r border-line bg-panel2 px-4 py-5">
      {/* Logo */}
      <button
        onClick={() => router.push('/dashboard')}
        className="mb-6 flex items-center gap-2.5 px-1.5 text-left"
      >
        <span className="flex h-[27px] w-[27px] items-center justify-center rounded-[7px] bg-accent">
          <span className="h-[9px] w-[9px] rounded-[2px] bg-lime" />
        </span>
        <span className="font-display text-[22px] font-semibold text-ink">Margin</span>
      </button>

      {/* Start a meeting */}
      <button
        onClick={() => router.push('/live-meeting')}
        className="mb-5 flex w-full items-center gap-2.5 rounded-md bg-accent px-3.5 py-3 text-[14.5px] font-semibold text-on-accent transition-transform hover:-translate-y-0.5 hover:bg-accent-hover"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-rec-ink" />
        Start a meeting
      </button>

      {/* Nav */}
      <nav className="flex flex-col gap-[3px]">
        {NAV.map((item) => {
          const active = isActive(item);
          return (
            <button
              key={item.key}
              onClick={() => router.push(item.href)}
              className={`flex items-center gap-2.5 rounded-[10px] px-[11px] py-2.5 text-[14.5px] transition-colors ${
                active
                  ? 'bg-nav-active font-semibold text-accent-ink'
                  : 'font-medium text-ink2 hover:bg-surface2'
              }`}
            >
              <span className="w-[18px] text-center">{item.icon}</span>
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* User card + dropdown */}
      <ProfileMenu user={user} />
    </aside>
  );
}
