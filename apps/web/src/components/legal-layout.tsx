"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { LegalInfo } from "@/lib/types";
import { Logo } from "./icons";
import { Skeleton } from "./ui";

export function formatVersion(version: string): string {
  const date = new Date(`${version}T00:00:00Z`);
  return Number.isNaN(date.getTime())
    ? version
    : date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

export function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-20 border-t border-line pt-8">
      <h2 id={`${id}-h`} className="font-display text-2xl leading-snug">
        {title}
      </h2>
      <div className="mt-3 space-y-3 text-[16px] leading-relaxed">{children}</div>
    </section>
  );
}

export const P = ({ children }: { children: ReactNode }) => <p>{children}</p>;

export function List({ items }: { items: ReactNode[] }) {
  return (
    <ul className="list-disc space-y-2 pl-5 marker:text-accent">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

/** Who to write to. Shows what the person running this copy of Vantage has set, and says so when they have not. */
export function Contact({ info }: { info: LegalInfo }) {
  const rows: [string, string | null][] = [
    ["Run by", info.operator_name],
    ["Email", info.contact_email],
    ["Grievance officer", info.grievance_officer],
    ["Grievance email", info.grievance_email],
    ["Postal address", info.postal_address],
  ];
  return (
    <dl className="raised grid gap-x-6 gap-y-2 rounded-2xl p-4 sm:grid-cols-[10rem_1fr]">
      {rows.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-sm text-muted">{label}</dt>
          <dd className={value ? "font-semibold" : "text-muted"}>{value ?? "Not set yet"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function LegalLayout({
  title,
  version,
  toc,
  children,
}: {
  title: string;
  version: (info: LegalInfo) => string;
  toc: [string, string][];
  children: (info: LegalInfo) => ReactNode;
}) {
  const { data: info, error } = useAsync((signal) => api.legal(signal), "legal");
  const draft = info && !info.operator_name;

  return (
    <div className="min-h-dvh">
      <header className="pt-safe border-b border-line">
        <div className="px-safe mx-auto flex h-14 w-full max-w-3xl items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5" aria-label="Vantage home">
            <Logo size={28} />
            <span className="font-display text-xl">Vantage</span>
          </Link>
          <nav aria-label="Legal" className="ml-auto flex gap-1 text-[15px] font-semibold">
            <Link href="/terms" className="inline-flex min-h-11 items-center rounded-lg px-3 text-muted hover:text-ink">
              Terms
            </Link>
            <Link href="/privacy" className="inline-flex min-h-11 items-center rounded-lg px-3 text-muted hover:text-ink">
              Privacy
            </Link>
          </nav>
        </div>
      </header>

      <main className="px-safe mx-auto w-full max-w-3xl py-8 md:py-12">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
          {info ? `Version ${version(info)}, updated ${formatVersion(version(info))}` : " "}
        </p>
        <h1 className="mt-2 font-display text-[34px] leading-[1.08] md:text-[46px]">{title}</h1>

        {draft && (
          <p role="note" className="mt-5 rounded-xl bg-accent-soft p-4 text-[15px] leading-relaxed text-accent">
            This is a working draft written for this app, not legal advice. The person running this copy of Vantage has not filled in their
            details yet, so parts below say &quot;Not set yet&quot;. Have a lawyer review it before real people use it.
          </p>
        )}

        {error && !info ? (
          <p role="alert" className="mt-6 text-[15px]">
            Couldn&apos;t load this page. Check your connection and reload.
          </p>
        ) : !info ? (
          <div className="mt-8 space-y-3" aria-busy>
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <>
            <nav aria-label="On this page" className="mt-6">
              <ol className="columns-1 gap-8 text-[15px] sm:columns-2">
                {toc.map(([id, label], i) => (
                  <li key={id} className="break-inside-avoid py-1">
                    <a href={`#${id}`} className="text-accent underline underline-offset-4">
                      {i + 1}. {label}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
            <div className="mt-8 space-y-8">{children(info)}</div>
          </>
        )}
      </main>

      <footer className="border-t border-line">
        <div className="px-safe mx-auto max-w-3xl py-6 text-sm text-muted">
          <Link href="/" className="font-semibold text-accent underline underline-offset-4">
            Back to Vantage
          </Link>
        </div>
      </footer>
    </div>
  );
}
