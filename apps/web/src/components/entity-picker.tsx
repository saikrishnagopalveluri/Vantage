"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAsync, useDebounced } from "@/lib/hooks";
import type { CapabilityRef, CompanyOut, RoleRef } from "@/lib/types";
import { CloseIcon } from "./icons";
import { Skeleton } from "./ui";

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
        onChange={(e) => setQuery(e.target.value)}
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
    </div>
  );
}
