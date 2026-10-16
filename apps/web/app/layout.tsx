import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pamtengo — AI sales intelligence",
  description: "Manage leads, qualify with a bounded AI agent, and review evidence-backed outreach.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 pb-8 text-xs text-slate-500">
          Pamtengo portfolio demo · All companies and contacts are fictional demo data · Mock email only — no real
          messages are ever sent.
        </footer>
      </body>
    </html>
  );
}
