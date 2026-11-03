"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Brand } from "./Brand";
import { getLastMeeting } from "@/lib/storage";

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [last, setLast] = useState<string | null>(null);

  useEffect(() => {
    setLast(getLastMeeting());
    setOpen(false);
  }, [pathname]);

  const links = [
    { href: "/workspace", label: "Workspace" },
    { href: last ? `/ask?meeting=${last}` : "/ask", label: "Ask", match: "/ask" },
    { href: "/history", label: "History" },
  ];

  return (
    <header className="sticky top-0 z-40 border-b hairline bg-ivory/90 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
        <Brand />
        <nav className="hidden items-center gap-8 md:flex" aria-label="Primary">
          {links.map((l) => {
            const active = pathname.startsWith(l.match ?? l.href.split("?")[0]);
            return (
              <Link
                key={l.label}
                href={l.href}
                className={`text-sm transition-colors ${active ? "text-forest font-semibold" : "text-muted hover:text-forest"}`}
              >
                {l.label}
              </Link>
            );
          })}
          <Link href="/workspace" className="btn btn-primary !py-2">
            Analyze a transcript
          </Link>
        </nav>
        <button
          className="md:hidden rounded-md p-2 text-forest"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>
      {open && (
        <nav className="border-t hairline bg-ivory px-5 pb-4 md:hidden" aria-label="Mobile">
          {links.map((l) => (
            <Link key={l.label} href={l.href} className="block border-b hairline py-3 text-forest">
              {l.label}
            </Link>
          ))}
          <Link href="/workspace" className="btn btn-primary mt-4 w-full">
            Analyze a transcript
          </Link>
        </nav>
      )}
    </header>
  );
}
