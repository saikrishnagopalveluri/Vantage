import type { ReactNode } from "react";

/** Each field of work gets a muted hue and a small glyph, so a story's field reads at a glance. */
const GLYPHS: Record<string, ReactNode> = {
  marketing: <path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1zM15 9a4 4 0 0 1 0 6M18 7a7 7 0 0 1 0 10" />,
  finance: <path d="M4 19h16M6 15l4-4 3 3 5-6M18 8h-3M18 8v3" />,
  software: <path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13 6l-2 12" />,
  "data-ai": (
    <>
      <circle cx="6" cy="6" r="2" />
      <circle cx="18" cy="6" r="2" />
      <circle cx="12" cy="18" r="2" />
      <path d="M8 6h8M7 8l4 8M17 8l-4 8" />
    </>
  ),
  "it-security": <path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6zM9 12l2 2 4-4" />,
  operations: (
    <>
      <path d="M3 7h11v9H3zM14 10h4l3 3v3h-7" />
      <circle cx="7" cy="18" r="1.6" />
      <circle cx="17" cy="18" r="1.6" />
    </>
  ),
  hr: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3 19c0-3 2.7-5 6-5s6 2 6 5M17 11a2.5 2.5 0 1 0 0-5M18 14c2 .4 3 2 3 4" />
    </>
  ),
  sales: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r=".6" />
    </>
  ),
  "product-design": <path d="M4 20l4-1 11-11-3-3L5 16zM14 6l3 3" />,
  consulting: <path d="M4 8h16v11H4zM9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M4 13h16" />,
  b2b: <path d="M4 5h9v9H4zM11 10h9v9h-9z" />,
  "digital-transformation": <path d="M4 12a8 8 0 0 1 14-5M20 12a8 8 0 0 1-14 5M18 3v4h-4M6 21v-4h4" />,
  "platform-business": <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM17 14v6M14 17h6" />,
  engineering: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
    </>
  ),
  trades: <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z" />,
  agriculture: <path d="M5 19c0-9 5-14 15-14 0 10-5 15-14 15M5 19l8-8" />,
  admin: <path d="M9 4h6v3H9zM7 6H6v14h12V6h-1M9 12h6M9 16h4" />,
  healthcare: <path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10zM12 9v5M9.5 11.5h5" />,
  science: <path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 15h8" />,
  education: <path d="M2 9l10-5 10 5-10 5zM6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5" />,
  legal: <path d="M12 4v16M6 20h12M5 7h14M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z" />,
  "public-services": <path d="M3 10l9-6 9 6M5 10v8M9 10v8M15 10v8M19 10v8M3 20h18" />,
  "creative-media": <path d="M3 7h13v10H3zM16 10l5-3v10l-5-3" />,
  hospitality: <path d="M5 8h11v6a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5zM16 10h2a2 2 0 0 1 0 4h-2M8 3v2M12 3v2" />,
};

const NAME_TO_SLUG: Record<string, string> = {
  "Marketing": "marketing",
  "Finance & Banking": "finance",
  "Sales & Business Development": "sales",
  "Human Resources": "hr",
  "Consulting & Strategy": "consulting",
  "B2B Business": "b2b",
  "Software Engineering": "software",
  "Data & AI": "data-ai",
  "IT, Cloud & Security": "it-security",
  "Product & Design": "product-design",
  "Digital Transformation": "digital-transformation",
  "Platform Businesses": "platform-business",
  "Operations & Supply Chain": "operations",
  "Engineering & Manufacturing": "engineering",
  "Construction & Skilled Trades": "trades",
  "Agriculture & Environment": "agriculture",
  "Office & Administration": "admin",
  "Healthcare & Life Sciences": "healthcare",
  "Science & Research": "science",
  "Education & Training": "education",
  "Legal & Compliance": "legal",
  "Public Services & Safety": "public-services",
  "Creative, Media & Arts": "creative-media",
  "Hospitality, Food & Travel": "hospitality",
};

export function slugFor(name: string | null | undefined): string {
  return NAME_TO_SLUG[name ?? ""] ?? "consulting";
}

export function DomainIcon({ slug, size = 20 }: { slug: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden
    >
      {GLYPHS[slug] ?? GLYPHS.consulting}
    </svg>
  );
}

/** One neutral chip for every field. The glyph and the name tell fields apart, not a colour. */
export const domainStyle = (_slug: string) => ({ background: "var(--sunken)", color: "var(--ink)" });

export function DomainBadge({ name, slug, compact = false }: { name: string; slug?: string; compact?: boolean }) {
  const key = slug ?? slugFor(name);
  return (
    <span
      style={domainStyle(key)}
      className="inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-0.5 text-xs font-semibold"
    >
      <DomainIcon slug={key} size={13} />
      {!compact && name}
    </span>
  );
}
