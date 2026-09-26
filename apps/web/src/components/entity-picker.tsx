"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAsync, useDebounced } from "@/lib/hooks";
import { ensureUserId } from "@/lib/session";
import type { CapabilityRef, CompanyOut, CompanySuggestResult, RoleRef, RoleSuggestResult } from "@/lib/types";
import { CloseIcon } from "./icons";
import { Button, Skeleton } from "./ui";

export interface PickItem {
  id: string;
  label: string;
  hint?: string;
}

export const fromRole = (r: RoleRef): PickItem => ({
  id: r.id,
  label: r.title,
  hint: r.parent ? `a kind of ${r.parent.name}` : r.domain?.name,
});
export const fromCompany = (c: CompanyOut | { id: string; name: string }): PickItem => ({
  id: c.id,
  label: c.name,
  hint: "industry" in c ? c.industry?.name : undefined,
});
export const fromCapability = (c: CapabilityRef): PickItem => ({ id: c.id, label: c.name, hint: c.kind });

export type PickerKind = "roles" | "companies" | "capabilities";

const PAGE = 40;

async function fetchOne(
  kind: PickerKind,
  q: string,
  domainId: string | null,
  signal: AbortSignal,
  limit: number,
  mba: boolean,
): Promise<PickItem[]> {
  if (kind === "roles") return (await api.roles(q, domainId, signal, limit, mba)).map(fromRole);
  if (kind === "companies") return (await api.companies(q, domainId, signal, limit, mba)).map(fromCompany);
  return (await api.capabilities(q, domainId, undefined, signal, limit, mba)).map(fromCapability);
}

/** One request per chosen field, merged, so a reader following two fields sees both. */
async function search(
  kind: PickerKind,
  q: string,
  domainIds: string[],
  signal: AbortSignal,
  limit: number,
  mba = false,
): Promise<PickItem[]> {
  const scopes = domainIds.length ? domainIds : [null];
  const lists = await Promise.all(scopes.map((d) => fetchOne(kind, q, d, signal, limit, mba)));
  const seen = new Set<string>();
  const merged = lists.flat().filter((item) => !seen.has(item.id) && seen.add(item.id));
  // One field: the server already ranked the best matches first. Several: interleave the lists.
  return scopes.length === 1 ? merged : interleave(lists).filter((item, i, all) => all.findIndex((o) => o.id === item.id) === i);
}

function interleave(lists: PickItem[][]): PickItem[] {
  const out: PickItem[] = [];
  for (let i = 0; i < Math.max(...lists.map((l) => l.length)); i++) for (const list of lists) if (list[i]) out.push(list[i]);
  return out;
}

const MIN_ADD_LEN = 2;

function AddEntityPanel({
  kind,
  initialQuery,
  domainId,
  onAdded,
  onCancel,
}: {
  kind: "roles" | "companies";
  initialQuery: string;
  domainId: string | null;
  onAdded: (item: PickItem) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(initialQuery);
  const [website, setWebsite] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const debouncedTitle = useDebounced(title.trim());
  const debouncedWebsite = useDebounced(website.trim());

  const { data, loading } = useAsync<RoleSuggestResult | CompanySuggestResult | null>(
    (signal) => {
      if (debouncedTitle.length < 1) return Promise.resolve(null);
      return kind === "roles"
        ? api.suggestRole(debouncedTitle, signal)
        : api.suggestCompany(debouncedTitle, debouncedWebsite || null, signal);
    },
    `suggest:${kind}:${debouncedTitle}:${debouncedWebsite}`,
  );

  const matches = (data?.matches ?? []) as (RoleRef | CompanyOut)[];
  const webResults = data?.web_results ?? [];
  const siteMeta = kind === "companies" ? (data as CompanySuggestResult | null)?.site_meta : null;

  const pickExisting = (item: RoleRef | CompanyOut) => {
    onAdded(kind === "roles" ? fromRole(item as RoleRef) : fromCompany(item as CompanyOut));
  };

  const submit = async () => {
    const trimmed = title.trim();
    if (trimmed.length < MIN_ADD_LEN) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const created =
        kind === "roles"
          ? fromRole(await api.addRole({ title: trimmed, domain_id: domainId }))
          : fromCompany(await api.addCompany({ name: trimmed, website: website.trim() || null }));
      onAdded(created);
    } catch (error) {
      setSubmitError(error instanceof ApiError ? error.message : "Couldn't add that. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="raised mt-2 space-y-3 rounded-xl p-3.5">
      <div>
        <label className="mb-1.5 block text-sm font-semibold" htmlFor={`add-${kind}-title`}>
          {kind === "roles" ? "Role title" : "Company name"}
        </label>
        <input
          id={`add-${kind}-title`}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="min-h-11 w-full rounded-xl border border-line bg-surface px-3.5 text-base outline-none placeholder:text-muted focus:border-accent"
          autoFocus
        />
      </div>

      {kind === "companies" && (
        <div>
          <label className="mb-1.5 block text-sm font-semibold" htmlFor="add-companies-website">
            Website <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="add-companies-website"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="acme.com"
            className="min-h-11 w-full rounded-xl border border-line bg-surface px-3.5 text-base outline-none placeholder:text-muted focus:border-accent"
          />
        </div>
      )}

      {loading && (
        <div className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      )}

      {!loading && matches.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs text-muted">Did you mean one of these already in Vantage?</p>
          <ul className="flex flex-wrap gap-1.5">
            {matches.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  onClick={() => pickExisting(m)}
                  className="btn-raised inline-flex min-h-9 items-center rounded-md px-3 text-sm font-semibold"
                >
                  {"title" in m ? m.title : m.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!loading && (siteMeta || webResults.length > 0) && (
        <div className="space-y-1.5 text-sm">
          {siteMeta && (
            <p>
              <span className="font-semibold">{siteMeta.title}</span>
              {siteMeta.snippet && <span className="text-muted"> — {siteMeta.snippet}</span>}
            </p>
          )}
          {webResults.map((r) => (
            <a key={r.url} href={r.url} target="_blank" rel="noreferrer" className="block truncate text-accent hover:underline">
              {r.title}
            </a>
          ))}
        </div>
      )}

      {submitError && <p className="text-sm font-semibold text-accent">{submitError}</p>}

      <div className="flex gap-2">
        <Button
          type="button"
          variant="primary"
          onClick={submit}
          disabled={submitting || title.trim().length < MIN_ADD_LEN}
        >
          {submitting ? "Adding…" : "Add it"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function EntityPicker({
  kind,
  label,
  selected,
  onChange,
  single = false,
  placeholder,
  domainIds = [],
  suggested = false,
}: {
  kind: PickerKind;
  label: string;
  selected: PickItem[];
  onChange: (items: PickItem[]) => void;
  single?: boolean;
  placeholder?: string;
  /** Limit the list to these fields of work. */
  domainIds?: string[];
  /** Offer quick picks that management students choose most. */
  suggested?: boolean;
}) {
  const [query, setQuery] = useState("");
  const q = useDebounced(query.trim());
  const scope = domainIds.join(",");
  const base = `${kind}:${q}:${scope}`;
  const [more, setMore] = useState({ base, pages: 1 });
  const pages = more.base === base ? more.pages : 1;
  const limit = PAGE * pages;
  const { data, loading, error } = useAsync((signal) => search(kind, q, domainIds, signal, limit), `${base}:${limit}`);

  const quick = useAsync(
    (signal) => (suggested && !single ? search(kind, "", domainIds, signal, 14, true) : Promise.resolve([])),
    `quick:${kind}:${scope}:${suggested && !single}`,
  );

  const chosen = new Set(selected.map((s) => s.id));
  const options = (data ?? []).filter((o) => !chosen.has(o.id));
  const quickPicks = (quick.data ?? []).filter((o) => !chosen.has(o.id)).slice(0, 10);
  const pick = (item: PickItem) => {
    onChange(single ? [item] : [...selected, item]);
    setQuery("");
  };

  const [adding, setAdding] = useState(false);
  const canAdd = (kind === "roles" || kind === "companies") && !loading && q.length >= MIN_ADD_LEN;

  return (
    <div>
      <label className="mb-2 block text-[15px] font-semibold" htmlFor={`pick-${kind}-${label}`}>
        {label}
      </label>

      {selected.length > 0 && (
        <ul className="mb-3 flex flex-wrap gap-2" aria-label={`Selected: ${label}`}>
          {selected.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onChange(selected.filter((s) => s.id !== item.id))}
                className="inline-flex min-h-9 items-center gap-1.5 rounded-full bg-accent-soft py-1 pl-3.5 pr-2.5 text-sm font-semibold text-accent"
                aria-label={`Remove ${item.label}`}
              >
                {item.label}
                <CloseIcon width={14} height={14} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {quickPicks.length > 0 && !q && (
        <div className="mb-3">
          <p className="mb-1.5 font-mono text-xs text-muted">Popular with management students</p>
          <ul className="flex flex-wrap gap-1.5" aria-label={`Popular ${label.toLowerCase()} for management students`}>
            {quickPicks.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => pick(item)}
                  className="btn-raised inline-flex min-h-9 items-center rounded-md px-3 text-sm font-semibold"
                >
                  + {item.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <input
        id={`pick-${kind}-${label}`}
        type="search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setAdding(false);
        }}
        placeholder={placeholder ?? "Search"}
        autoComplete="off"
        className="min-h-11 w-full rounded-xl border border-line bg-surface px-3.5 text-base outline-none placeholder:text-muted focus:border-accent"
      />

      <div className="raised mt-2 max-h-60 overflow-y-auto rounded-xl" aria-busy={loading}>
        {error ? (
          <p className="p-3 text-sm text-muted">{error.message}</p>
        ) : loading && !data ? (
          <div className="space-y-2 p-3">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : options.length === 0 ? (
          <p className="p-3 text-sm text-muted">{q ? "No match. Try a shorter word." : "You've added everything here."}</p>
        ) : (
          <ul>
            {options.map((item) => (
              <li key={item.id} className="border-b border-line last:border-b-0">
                <button
                  type="button"
                  onClick={() => pick(item)}
                  className="flex min-h-11 w-full items-center justify-between gap-3 px-3.5 text-left text-[15px] hover:bg-accent-soft"
                >
                  <span>{item.label}</span>
                  {item.hint && <span className="text-xs text-muted">{item.hint}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
        {(data?.length ?? 0) >= limit && !error && (
          <button
            type="button"
            onClick={() => setMore({ base, pages: pages + 1 })}
            className="min-h-11 w-full border-t border-line text-sm font-semibold text-accent hover:bg-accent-soft"
          >
            Show more
          </button>
        )}
      </div>

      {canAdd && !adding && (
        <button
          type="button"
          onClick={() => {
            ensureUserId();
            setAdding(true);
          }}
          className="mt-2 text-sm font-semibold text-accent hover:underline"
        >
          Can&apos;t find &quot;{q}&quot;? Add it
        </button>
      )}

      {adding && (kind === "roles" || kind === "companies") && (
        <AddEntityPanel
          kind={kind}
          initialQuery={q}
          domainId={domainIds.length === 1 ? domainIds[0] : null}
          onAdded={(item) => {
            pick(item);
            setAdding(false);
          }}
          onCancel={() => setAdding(false)}
        />
      )}
    </div>
  );
}
