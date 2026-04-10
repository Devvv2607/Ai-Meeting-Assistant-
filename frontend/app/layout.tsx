import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Meeting Intelligence Platform",
  description: "Convert meeting recordings into structured insights",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
