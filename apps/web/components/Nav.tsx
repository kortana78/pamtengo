import Link from "next/link";

const links = [
  { href: "/", label: "Overview" },
  { href: "/leads", label: "Leads" },
  { href: "/runs", label: "Agent runs" },
  { href: "/outreach", label: "Outreach review" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-bold text-brand-700">
          Pamtengo
          <span className="ml-2 rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
            sales intelligence · demo
          </span>
        </Link>
        <nav className="flex gap-1" aria-label="Primary">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="rounded-lg px-3 py-2 text-sm hover:bg-slate-100">
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
