"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useAsync, useDebounced } from "@/lib/hooks";
import { DomainBadge } from "@/lib/domains";
import { ExternalIcon, SearchIcon } from "./icons";
import { Sheet } from "./sheet";

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5">
      <h3 className="mb-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">{title}</h3>
      <ul className="divide-y divide-line rounded-xl border border-line bg-surface">{children}</ul>
    </section>
  );
}

const ROW = "flex min-h-11 items-center justify-between gap-3 px-3.5 py-2 text-[15px] hover:bg-accent-soft";

function Results({ q, onPick }: { q: string; onPick: () => void }) {
  const { data, error, loading } = useAsync((signal) => api.search(q, signal), `search:${q}`);
  if (error) return <p className="mt-6 text-[15px] text-muted">{error.message}</p>;
  if (!data) return <p className="mt-6 text-[15px] text-muted">{loading ? "Searching…" : ""}</p>;
  const empty = !data.roles.length && !data.companies.length && !data.capabilities.length && !data.articles.length;
  if (empty) return <p className="mt-6 text-[15px] text-muted">Nothing matches &ldquo;{q}&rdquo;. Try a shorter word.</p>;
  return (
    <div>
      {data.roles.length > 0 && (
        <Group title="Roles">
          {data.roles.map((r) => (
            <li key={r.id}>
              <Link href={`/explore/roles/${r.id}`} onClick={onPick} className={ROW}>
                <span>{r.title}</span>
                {r.domain && <DomainBadge name={r.domain.name} />}
              </Link>
            </li>
          ))}
        </Group>
      )}
      {data.companies.length > 0 && (
        <Group title="Companies">
          {data.companies.map((c) => (
            <li key={c.id}>
              <Link href={`/explore/companies/${c.id}`} onClick={onPick} className={ROW}>
                <span>{c.name}</span>
                <span className="text-xs text-muted">{c.industry?.name}</span>
              </Link>
            </li>
          ))}
        </Group>
      )}
      {data.capabilities.length > 0 && (
        <Group title="Skills and tools">
          {data.capabilities.map((c) => (
            <li key={c.id} className={ROW}>
              <span>{c.name}</span>
              <span className="text-xs text-muted">{c.kind}</span>
            </li>
          ))}
        </Group>
      )}
      {data.articles.length > 0 && (
        <Group title="Stories">
          {data.articles.map((a) => (
            <li key={a.id}>
              <a href={a.url} target="_blank" rel="noopener noreferrer" className={ROW}>
                <span className="min-w-0">
                  <span className="line-clamp-2">{a.title}</span>
                  <span className="text-xs text-muted">
                    {a.source.name} · {timeAgo(a.published_at)}
                  </span>
                </span>
                <ExternalIcon width={15} height={15} className="shrink-0 opacity-60" />
              </a>
            </li>
          ))}
        </Group>
      )}
    </div>
  );
}

/** One search box for roles, companies, skills and stories. Open it with the button or "/". */
export function SearchPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const q = useDebounced(query.trim(), 200);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) setTimeout(() => input.current?.focus(), 50);
  }, [open]);

  return (
    <Sheet open={open} onClose={onClose} title="Search">
      <label htmlFor="global-search" className="sr-only">
        Search roles, companies, skills and stories
      </label>
      <div className="flex items-center gap-2 rounded-xl border border-line bg-sunken px-3 focus-within:border-accent">
        <SearchIcon width={18} height={18} className="text-muted" />
        <input
          id="global-search"
          ref={input}
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Try “actuary”, “Infosys” or “Kubernetes”"
          autoComplete="off"
          className="min-h-11 w-full bg-transparent text-base outline-none placeholder:text-muted"
        />
      </div>
      {q.length >= 2 ? <Results q={q} onPick={onClose} /> : <p className="mt-6 text-[15px] text-muted">Type at least two letters.</p>}
    </Sheet>
  );
}
