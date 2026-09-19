"use client";

import { api } from "@/lib/api";
import { DomainIcon, domainStyle } from "@/lib/domains";
import { useAsync } from "@/lib/hooks";
import { MAX_FIELDS, type Domain } from "@/lib/types";
import { CheckIcon, CloseIcon } from "./icons";
import { Skeleton, cx } from "./ui";

const GROUP_ORDER = ["Business & Finance", "Technology", "Health, Science & Public", "Operations & Industry", "Creative & Services"];

function groupOf(domains: Domain[]): [string, Domain[]][] {
  const groups = new Map<string, Domain[]>();
  for (const d of domains) groups.set(d.group, [...(groups.get(d.group) ?? []), d]);
  const rank = (g: string) => (GROUP_ORDER.includes(g) ? GROUP_ORDER.indexOf(g) : GROUP_ORDER.length);
  return [...groups].sort(([a], [b]) => rank(a) - rank(b));
}

/** Fields of work, grouped, as tappable cards. A reader can follow up to four. */
export function DomainGrid({
  selected,
  onToggle,
  stickyClass = "top-0",
}: {
  selected: string[];
  onToggle: (id: string) => void;
  /** Where the counter sticks while scrolling; lower it when a fixed bar sits above. */
  stickyClass?: string;
}) {
  const { data, error } = useAsync((signal) => api.domains(signal), "domains");
  if (error) return <p className="text-[15px] text-muted">{error.message}</p>;

  const full = selected.length >= MAX_FIELDS;
  const chosen = (data ?? []).filter((d) => selected.includes(d.id));

  return (
    <div role="group" aria-label="Fields of work">
      <div className={cx("sticky z-10 -mx-4 mb-4 border-b border-line bg-paper/95 px-4 py-2.5 backdrop-blur md:mx-0 md:rounded-xl md:border md:px-3.5", stickyClass)}>
        <p className="text-sm text-muted" aria-live="polite">
          <span className="font-mono font-semibold text-ink">
            {selected.length} of {MAX_FIELDS}
          </span>{" "}
          {full ? "chosen. Remove one to pick another." : "chosen. You can pick up to four."}
        </p>
        {/* Always reserve the row, so picking a field never pushes the list down under the reader's thumb. */}
        <ul className="mt-2 flex min-h-9 flex-wrap items-center gap-1.5" aria-label="Chosen fields">
          {chosen.length === 0 && <li className="text-xs text-muted">Your picks will show up here.</li>}
          {chosen.map((d) => (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => onToggle(d.id)}
                  aria-label={`Remove ${d.name}`}
                  style={domainStyle(d.slug)}
                  className="inline-flex min-h-9 items-center gap-1.5 rounded-full py-1 pl-2.5 pr-2 text-xs font-semibold"
                >
                  <DomainIcon slug={d.slug} size={13} />
                  {d.name}
                  <CloseIcon width={13} height={13} />
                </button>
              </li>
            ))}
        </ul>
      </div>
      {!data ? (
        <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          {Array.from({ length: 9 }, (_, i) => (
            <li key={i}>
              <Skeleton className="h-16 w-full rounded-2xl" />
            </li>
          ))}
        </ul>
      ) : (
        <div className="space-y-6">
          {groupOf(data).map(([group, domains]) => (
            <section key={group} aria-label={group}>
              <h3 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">{group}</h3>
              <ul className="grid grid-cols-1 gap-2.5 min-[420px]:grid-cols-2">
                {domains.map((d) => {
                  const on = selected.includes(d.id);
                  const blocked = full && !on;
                  return (
                    <li key={d.id}>
                      <button
                        type="button"
                        onClick={() => !blocked && onToggle(d.id)}
                        aria-pressed={on}
                        aria-disabled={blocked}
                        className={cx(
                          "relative flex min-h-16 w-full items-center gap-3 rounded-2xl border p-3 text-left transition-[transform,background-color,border-color,opacity] duration-200",
                          on ? "border-transparent shadow-inner" : "raised",
                          blocked ? "cursor-not-allowed opacity-45" : "active:scale-[0.98]",
                          !on && !blocked && "hover:border-muted",
                        )}
                        style={on ? domainStyle(d.slug) : undefined}
                      >
                        <span style={domainStyle(d.slug)} className="flex size-10 shrink-0 items-center justify-center rounded-xl">
                          <DomainIcon slug={d.slug} size={20} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block text-[15px] font-semibold leading-tight">{d.name}</span>
                          <span className="mt-0.5 block text-xs opacity-90">{d.role_count.toLocaleString()} job titles</span>
                        </span>
                        {on && <CheckIcon width={18} height={18} className="shrink-0" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
