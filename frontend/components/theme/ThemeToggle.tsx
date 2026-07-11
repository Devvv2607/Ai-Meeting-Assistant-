'use client';

import { useTheme } from './ThemeProvider';

/**
 * Fixed top-right pill toggle (sun / moon) matching the Margin prototype.
 */
export default function ThemeToggle({ fixed = true }: { fixed?: boolean }) {
  const { theme, toggle } = useTheme();

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      className={`${
        fixed ? 'fixed top-5 right-5 z-50' : ''
      } flex items-center gap-1 rounded-pill border border-line bg-surface px-1 py-1 shadow-toggle transition-colors`}
    >
      <span
        className={`flex h-7 w-7 items-center justify-center rounded-pill text-[13px] transition-colors ${
          theme === 'light' ? 'bg-nav-active text-accent-ink' : 'text-muted'
        }`}
      >
        ☀
      </span>
      <span
        className={`flex h-7 w-7 items-center justify-center rounded-pill text-[13px] transition-colors ${
          theme === 'dark' ? 'bg-nav-active text-accent-ink' : 'text-muted'
        }`}
      >
        ☾
      </span>
    </button>
  );
}
