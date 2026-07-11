/** @type {import('tailwindcss').Config} */
module.exports = {
  // Theming is driven by CSS variables that flip on [data-theme]; no dark: variants needed.
  darkMode: 'class',
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        surface2: "var(--surface2)",
        surface3: "var(--surface3)",
        panel2: "var(--panel2)",

        ink: "var(--ink)",
        "ink-soft": "var(--ink-soft)",
        ink2: "var(--ink2)",
        ink2b: "var(--ink2b)",
        ink3: "var(--ink3)",

        muted: "var(--muted)",
        muted2: "var(--muted2)",
        muted3: "var(--muted3)",

        line: "var(--line)",
        "line-input": "var(--line-input)",
        line2: "var(--line2)",
        "line-hover": "var(--line-hover)",
        "nav-active": "var(--nav-active)",

        accent: "var(--accent)",
        "accent-ink": "var(--accent-ink)",
        "accent-hover": "var(--accent-hover)",
        lime: "var(--lime)",
        "accent-soft": "var(--accent-soft)",
        "accent-soft-border": "var(--accent-soft-border)",
        mark: "var(--mark)",
        dot: "var(--dot)",
        bullet: "var(--bullet)",

        "rec-bg": "var(--rec-bg)",
        "rec-border": "var(--rec-border)",
        "rec-ink": "var(--rec-ink)",
        "rec-ink2": "var(--rec-ink2)",

        "ok-bg": "var(--ok-bg)",
        "ok-ink": "var(--ok-ink)",
        "ok-dot": "var(--ok-dot)",
        "key-ink": "var(--key-ink)",

        "on-accent": "var(--on-accent)",
      },
      fontFamily: {
        sans: ["'Hanken Grotesk'", "system-ui", "sans-serif"],
        display: ["'Newsreader'", "Georgia", "serif"],
        mono: ["'Space Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "5px",
        DEFAULT: "10px",
        md: "11px",
        lg: "12px",
        xl: "15px",
        "2xl": "18px",
        pill: "999px",
      },
      boxShadow: {
        toggle: "0 6px 18px -10px var(--shadow)",
        card: "0 16px 36px -22px var(--shadow-soft)",
        cardHover: "0 16px 36px -18px var(--shadow)",
        elevated: "0 24px 60px -24px var(--shadow)",
        hero: "0 40px 90px -40px var(--shadow)",
        input: "0 8px 24px -16px var(--shadow)",
      },
      keyframes: {
        mgFadeUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        mgDot: {
          "0%,80%,100%": { transform: "translateY(0)", opacity: ".5" },
          "40%": { transform: "translateY(-5px)", opacity: "1" },
        },
      },
      animation: {
        fadeUp: "mgFadeUp .55s ease-out both",
        dot: "mgDot 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
