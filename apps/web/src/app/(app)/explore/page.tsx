"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowIcon, SearchIcon } from "@/components/icons";
import { Button, Card, EmptyState, ErrorNotice, PageHeader, Segmented, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { DomainBadge, DomainIcon, domainStyle } from "@/lib/domains";
import { useAsync, useDebounced } from "@/lib/hooks";

type Tab = "roles" | "companies";

const PAGE = 40;
const ROW = "flex min-h-14 items-center justify-between gap-3 px-4 py-2.5 hover:bg-accent-soft";

export default function ExplorePage() {
  const [tab, setTab] = useState<Tab>("roles");
  const [domainId, setDomainId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [pages, setPages] = useState({ key: "", n: 1 });
  const q = useDebounced(query.trim(), 220);

  const scope = `${q}:${domainId}`;
  const n = pages.key === scope ? pages.n : 1;
  const limit = PAGE * n;

  const domains = useAsync((signal) => api.domains(signal), "domains");
  const roles = useAsync((signal) => api.roles(q, domainId, signal, limit), `roles:${scope}:${limit}`);
  const companies = useAsync((signal) => api.companies(q, domainId, signal, limit), `companies:${scope}:${limit}`);
  const list = tab === "roles" ? roles : companies;
  const active = domains.data?.find((d) => d.id === domainId);
  const mayHaveMore = (list.data?.length ?? 0) >= limit;

  return (
    <>
      <PageHeader
        eyebrow="Explore"
        title="See what each job asks for"
        subtitle="Pick a field, open a role, and check the skills it needs and who is hiring."
      />

      <section aria-label="Fields" className="mb-6">
        <ul className="flex flex-wrap gap-2">
          {(domains.data ?? Array.from({ length: 12 }, () => null)).map((d, i) =>
            d ? (
              <li key={d.id} style={{ "--n": Math.min(i, 8) } as React.CSSProperties} className="rise">
                <button
                  onClick={() => setDomainId(domainId === d.id ? null : d.id)}
                  aria-pressed={domainId === d.id}
                  className={cx(
                    "inline-flex min-h-11 items-center gap-2 rounded-md border py-1.5 pl-2 pr-3.5 text-sm font-semibold transition-[transform,background-color,border-color] duration-200 active:scale-[0.97]",
                    domainId === d.id ? "border-transparent" : "btn-raised",
                  )}
                  style={domainId === d.id ? { background: "var(--ink)", color: "var(--paper)" } : undefined}
                >
                  <span style={domainStyle(d.slug)} className="flex size-7 items-center justify-center rounded-full">
                    <DomainIcon slug={d.slug} size={15} />
                  </span>
                  {d.name}
                  <span className="font-mono text-xs opacity-70">{d.role_count.toLocaleString()}</span>
                </button>
              </li>
            ) : (
              <li key={i}>
                <Skeleton className="h-11 w-36 rounded-full" />
              </li>
            ),
          )}
        </ul>
      </section>

      <div className="sticky top-12 z-20 -mx-4 space-y-2.5 bg-paper px-4 pb-3 pt-2 md:top-0 md:mx-0 md:px-0">
        <div className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 focus-within:border-accent">
          <SearchIcon width={18} height={18} className="text-muted" />
          <label htmlFor="explore-search" className="sr-only">
            Search {tab}
          </label>
          <input
            id="explore-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tab === "roles" ? "Search job titles, like “actuary” or “SRE”" : "Search companies"}
            autoComplete="off"
            className="min-h-11 w-full bg-transparent text-base outline-none placeholder:text-muted"
          />
        </div>
        <Segmented
          label="What to browse"
          value={tab}
          onChange={setTab}
          options={[
            { id: "roles", label: "Roles" },
            { id: "companies", label: "Companies" },
          ]}
        />
        {active && (
          <p className="text-sm text-muted">
            Showing {tab} in <strong className="text-ink">{active.name}</strong>.{" "}
            <button onClick={() => setDomainId(null)} className="font-semibold text-accent underline underline-offset-4">
              Show everything
            </button>
          </p>
        )}
      </div>

      <div className="mt-2" aria-busy={list.loading}>
        {list.error && !list.data ? (
          <ErrorNotice message={list.error.message} onRetry={list.reload} />
        ) : !list.data ? (
          <Card className="space-y-3">
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-5 w-1/2" />
            <Skeleton className="h-5 w-3/5" />
          </Card>
        ) : list.data.length === 0 ? (
          <EmptyState title="No match">Try a shorter word, or clear the field filter.</EmptyState>
        ) : tab === "roles" ? (
          <ul className="raised divide-y divide-line overflow-hidden rounded-2xl">
            {roles.data?.map((r) => (
              <li key={r.id}>
                <Link href={`/explore/roles/${r.id}`} className={ROW}>
                  <span>
                    <span className="block font-semibold">{r.title}</span>
                    {r.parent && <span className="block text-xs text-muted">A kind of {r.parent.name}</span>}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {r.domain && <DomainBadge name={r.domain.name} />}
                    <ArrowIcon width={16} height={16} className="text-muted" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <ul className="raised divide-y divide-line overflow-hidden rounded-2xl">
            {companies.data?.map((c) => (
              <li key={c.id}>
                <Link href={`/explore/companies/${c.id}`} className={ROW}>
                  <span className="font-semibold">{c.name}</span>
                  <span className="flex items-center gap-2 text-sm text-muted">
                    {c.industry?.name}
                    <ArrowIcon width={16} height={16} />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        {mayHaveMore && !list.error && (
          <div className="mt-4 flex justify-center">
            <Button onClick={() => setPages({ key: scope, n: n + 1 })} disabled={list.loading}>
              {list.loading ? "Loading" : "Show more"}
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
