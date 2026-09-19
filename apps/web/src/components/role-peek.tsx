"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { DomainBadge } from "@/lib/domains";
import { useAsync, useDebounced } from "@/lib/hooks";
import { ArrowIcon, SearchIcon } from "./icons";
import { Chip, Skeleton } from "./ui";

const EXAMPLES = ["Brand Manager", "Management Consultant", "Investment Banking Associate", "Product Manager"];

/** Type a job, see what employers ask for. Uses the public taxonomy, so it works before sign-up. */
export function RolePeek() {
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<{ id: string; title: string } | null>(null);
  const q = useDebounced(query.trim(), 200);

  const results = useAsync(
    (signal) => (q.length >= 2 ? api.roles(q, null, signal, 6) : Promise.resolve([])),
    `peek:${q}`,
  );
  const detail = useAsync(
    (signal) => (picked ? api.roleDetail(picked.id, signal) : Promise.resolve(null)),
    `peek-role:${picked?.id ?? ""}`,
  );

  const role = detail.data;
  const skills = role?.capabilities.filter((c) => c.kind === "skill").slice(0, 7) ?? [];
  const tools = role?.capabilities.filter((c) => c.kind === "tool").slice(0, 6) ?? [];

  return (
    <div className="raised rounded-2xl p-5 md:p-6">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent">Try it, no account needed</p>
      <h3 className="mt-1.5 font-display text-2xl leading-snug">What does a job ask for?</h3>
      <p className="mt-1 text-[15px] text-muted">Type any job title. Skills and tools come from O*NET, a US Department of Labor database.</p>

      <div className="mt-4 flex items-center gap-2 rounded-xl border border-line bg-surface px-3 focus-within:border-accent">
        <SearchIcon width={18} height={18} className="text-muted" />
        <label htmlFor="peek-search" className="sr-only">
          Job title
        </label>
        <input
          id="peek-search"
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPicked(null);
          }}
          placeholder="Try “brand manager” or “consultant”"
          autoComplete="off"
          className="min-h-11 w-full bg-transparent text-base outline-none placeholder:text-muted"
        />
      </div>

      {!picked && q.length < 2 && (
        <ul className="mt-3 flex flex-wrap gap-2" aria-label="Examples">
          {EXAMPLES.map((e) => (
            <li key={e}>
              <button
                type="button"
                onClick={() => setQuery(e)}
                className="btn-raised min-h-9 rounded-full px-3.5 text-sm font-semibold"
              >
                {e}
              </button>
            </li>
          ))}
        </ul>
      )}

      {!picked && q.length >= 2 && (
        <div className="mt-3" aria-busy={results.loading}>
          {results.data && results.data.length > 0 ? (
            <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
              {results.data.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    onClick={() => setPicked({ id: r.id, title: r.title })}
                    className="flex min-h-11 w-full items-center justify-between gap-3 px-3.5 text-left text-[15px] font-semibold hover:bg-accent-soft"
                  >
                    {r.title}
                    {r.domain && <DomainBadge name={r.domain.name} />}
                  </button>
                </li>
              ))}
            </ul>
          ) : results.loading ? (
            <Skeleton className="h-11 w-full" />
          ) : (
            <p className="text-sm text-muted">No job titles match. Try a shorter word.</p>
          )}
        </div>
      )}

      {picked && (
        <div className="rise mt-4" aria-live="polite">
          {!role ? (
            <Skeleton className="h-28 w-full" />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <h4 className="font-display text-xl">{role.title}</h4>
                {role.domain && <DomainBadge name={role.domain.name} />}
              </div>
              {role.description && <p className="mt-1.5 line-clamp-3 text-[15px] leading-relaxed text-muted">{role.description}</p>}
              {skills.length > 0 && (
                <div className="mt-3">
                  <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Skills</p>
                  <ul className="mt-1.5 flex flex-wrap gap-1.5">
                    {skills.map((s) => (
                      <li key={s.id}>
                        <Chip tone="accent">{s.name}</Chip>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {tools.length > 0 && (
                <div className="mt-3">
                  <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">Tools</p>
                  <ul className="mt-1.5 flex flex-wrap gap-1.5">
                    {tools.map((s) => (
                      <li key={s.id}>
                        <Chip>{s.name}</Chip>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="mt-3 text-sm text-muted">
                {role.companies_total > 0
                  ? `${role.companies_total.toLocaleString()} companies in our lists hire for this kind of work.`
                  : "We don't have companies listed for this one yet."}
              </p>
              <Link
                href="/login?mode=signup"
                className="mt-3 inline-flex min-h-11 items-center gap-1.5 font-semibold text-accent underline underline-offset-4"
              >
                Follow it and see your own gaps <ArrowIcon width={15} height={15} />
              </Link>
            </>
          )}
        </div>
      )}
    </div>
  );
}
