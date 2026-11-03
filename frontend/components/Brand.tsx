import Link from "next/link";

export function Mark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#183d32" />
      <rect x="7" y="9" width="14" height="2.2" rx="1.1" fill="#f5f2ea" opacity="0.55" />
      <rect x="7" y="14.9" width="18" height="2.2" rx="1.1" fill="#a6b9a5" />
      <rect x="7" y="20.8" width="10" height="2.2" rx="1.1" fill="#f5f2ea" opacity="0.55" />
      <circle cx="24" cy="21.9" r="2.6" fill="#34765a" stroke="#f5f2ea" strokeWidth="1.2" />
    </svg>
  );
}

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5 focus-ring rounded-md" aria-label="insightmeet home">
      <Mark />
      <span className={`font-serif text-[1.35rem] tracking-tight ${light ? "text-ivory" : "text-forest"}`}>
        insight<em className={`not-italic ${light ? "text-sage" : "text-emerald"}`}>meet</em>
      </span>
    </Link>
  );
}
