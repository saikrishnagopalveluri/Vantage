"use client";

import Link from "next/link";
import { useState } from "react";
import { CheckIcon } from "@/components/icons";
import { JDPanel } from "@/components/jd-panel";
import { useProfile } from "@/components/profile-context";
import { useToast } from "@/components/toast";
import { Button, Card, Chip, EmptyState, ErrorNotice, LinkButton, PageHeader, Segmented, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { CapabilityGap, RoleGaps } from "@/lib/types";

const SOURCE_LABEL: Record<CapabilityGap["source"], string> = {
  jd: "From your job description",
  company: "From company data",
  taxonomy: "Typical for the role",
};

function readiness(role: RoleGaps): number {
  const total = role.capabilities.reduce((sum, c) => sum + c.required_by_count, 0);
  if (!total) return 0;
  const covered = role.capabilities.filter((c) => c.user_has_it).reduce((sum, c) => sum + c.required_by_count, 0);
  return Math.round((covered / total) * 100);
}

function Ring({ value }: { value: number }) {
  const r = 40;
  const c = 2 * Math.PI * r;
  return (
    <svg width="104" height="104" viewBox="0 0 104 104" role="img" aria-label={`${value} percent covered`}>
      <circle cx="52" cy="52" r={r} fill="none" stroke="var(--sunken)" strokeWidth="9" />
      <circle
        cx="52"
        cy="52"
        r={r}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="9"
        strokeLinecap="round"
        strokeDasharray={`${(c * value) / 100} ${c}`}
        transform="rotate(-90 52 52)"
        style={{ transition: "stroke-dasharray 700ms var(--ease-out)" }}
      />
      <text x="52" y="58" textAnchor="middle" fontFamily="var(--font-fraunces), serif" fontSize="26" fill="var(--ink)">
        {value}%
      </text>
    </svg>
  );
}

function Coverage({ role }: { role: RoleGaps }) {
  const plural = (n: number) => (n === 1 ? "company" : "companies");
  if (role.companies_considered === 0) {
    return <p className="mt-1 text-sm text-muted">None of your target companies has requirements on file for this role yet, so there&apos;s nothing to compare.</p>;
  }
  return (
    <p className="mt-1 text-sm text-muted">
      Based on {role.companies_considered} {plural(role.companies_considered)} you follow that hire for this role
      {role.companies_with_no_data > 0 && `. ${role.companies_with_no_data} more ${role.companies_with_no_data === 1 ? "has" : "have"} no data yet`}.
    </p>
  );
}

export default function CareerPage() {
  const { profile, setProfile } = useProfile();
  const toast = useToast();
  const [gapsOnly, setGapsOnly] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [roleId, setRoleId] = useState<string | null>(null);
  const [tab, setTab] = useState<"roles" | "jds">("roles");

  const { data, error, loading, reload } = useAsync(
    (signal) => api.skillGaps(profile.user_id, signal),
    `gaps:${profile.user_id}:${profile.capabilities.map((c) => c.id).join(",")}:${profile.target_roles.map((r) => r.id).join(",")}:${profile.target_companies.length}`,
  );

  async function toggle(gap: CapabilityGap) {
    setPending(gap.capability_id);
    const owned = profile.capabilities.map((c) => c.id);
    try {
      setProfile(
        await api.putTargets(profile.user_id, {
          domain_ids: profile.domains.map((d) => d.id),
          target_role_ids: profile.target_roles.map((r) => r.id),
          target_company_ids: profile.target_companies.map((c) => c.id),
          capability_ids: gap.user_has_it ? owned.filter((id) => id !== gap.capability_id) : [...owned, gap.capability_id],
        }),
      );
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't update that.");
    } finally {
      setPending(null);
    }
  }

  const roles = data?.target_roles ?? [];
  const current = roles.find((r) => r.role_id === roleId) ?? roles[0];
  const rows = current?.capabilities.filter((c) => !(gapsOnly && c.user_has_it)) ?? [];
  const missing = current?.capabilities.filter((c) => !c.user_has_it) ?? [];
  const next = [...missing].sort((a, b) => b.required_by_count - a.required_by_count)[0];

  return (
    <>
      <PageHeader
        eyebrow="Skill gaps"
        title="What's between you and the job"
        subtitle="Compare what employers ask for with what you can already do."
      />

      <div className="mb-5 max-w-md">
        <Segmented
          label="Where the requirements come from"
          value={tab}
          onChange={setTab}
          options={[
            { id: "roles", label: "By role" },
            { id: "jds", label: "Job descriptions" },
          ]}
        />
      </div>

      {tab === "jds" ? (
        <JDPanel />
      ) : profile.target_roles.length === 0 ? (
        <EmptyState title="Pick a role to compare against" action={<LinkButton href="/explore" variant="primary">Browse roles</LinkButton>}>
          Gaps are worked out per role, across the companies you follow. Open any role and tap Follow.
        </EmptyState>
      ) : error && !data ? (
        <ErrorNotice message={error.message} onRetry={reload} />
      ) : !data || !current ? (
        <Skeleton className="h-72 w-full" />
      ) : (
        <div className={cx("max-w-3xl space-y-5", loading && "opacity-70 transition-opacity")}>
          {roles.length > 1 && (
            <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:px-0" role="group" aria-label="Choose a role">
              {roles.map((r) => (
                <button
                  key={r.role_id}
                  onClick={() => setRoleId(r.role_id)}
                  aria-pressed={r.role_id === current.role_id}
                  className={cx(
                    "min-h-9 shrink-0 rounded-full border px-3.5 text-sm font-semibold transition-colors",
                    r.role_id === current.role_id ? "border-ink bg-ink text-paper" : "border-line text-muted hover:text-ink",
                  )}
                >
                  {r.role_title}
                </button>
              ))}
            </div>
          )}

          <Card className="flex flex-wrap items-center gap-5">
            <Ring value={readiness(current)} />
            <div className="min-w-0 flex-1">
              <h2 className="font-display text-2xl leading-tight">
                <Link href={`/explore/roles/${current.role_id}`} className="hover:text-accent">
                  {current.role_title}
                </Link>
              </h2>
              <p className="mt-1 text-[15px]">
                You cover about {readiness(current)}% of what these companies ask for.
              </p>
              <Coverage role={current} />
            </div>
          </Card>

          {next && (
            <Card className="border-accent/40 bg-accent-soft">
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent">Learn this next</p>
              <p className="mt-1 font-display text-2xl">{next.name}</p>
              <p className="mt-1 text-[15px]">
                {next.required_by_count} of {next.required_by_total} companies ask for it, and it isn&apos;t on your profile yet.
              </p>
              <Button variant="secondary" className="mt-3" disabled={pending === next.capability_id} onClick={() => toggle(next)}>
                I already know this
              </Button>
            </Card>
          )}

          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-display text-xl">Everything they ask for</h2>
              <label className="flex min-h-11 cursor-pointer items-center gap-2.5 text-sm font-semibold">
                <input type="checkbox" checked={gapsOnly} onChange={(e) => setGapsOnly(e.target.checked)} className="size-5 accent-[var(--accent)]" />
                Only what I&apos;m missing
              </label>
            </div>

            {rows.length === 0 ? (
              <p className="mt-3 text-[15px] text-muted">
                {current.capabilities.length ? "You have everything on the list. Nice work." : "There's nothing to compare for this role yet."}
              </p>
            ) : (
              <ul className="mt-2 divide-y divide-line">
                {rows.map((gap) => (
                  <li key={gap.capability_id} className="py-3.5">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="flex flex-wrap items-center gap-2 font-semibold">
                          {gap.name}
                          <Chip>{gap.kind}</Chip>
                        </p>
                        <p className="mt-0.5 text-xs text-muted">{SOURCE_LABEL[gap.source]}</p>
                      </div>
                      <p className="shrink-0 font-mono text-sm" aria-label={`Required by ${gap.required_by_count} of ${gap.required_by_total} companies`}>
                        {gap.required_by_count}/{gap.required_by_total}
                      </p>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-sunken" aria-hidden>
                      <div
                        className={cx("h-full rounded-full transition-[width] duration-700", gap.user_has_it ? "bg-good" : "bg-accent")}
                        style={{ width: `${Math.round(gap.gap_ratio * 100)}%` }}
                      />
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-3">
                      {gap.user_has_it ? (
                        <span className="flex items-center gap-1 text-sm font-semibold text-good">
                          <CheckIcon width={16} height={16} /> You have this
                        </span>
                      ) : (
                        <span className="text-sm font-semibold text-accent">Missing</span>
                      )}
                      <Button variant="ghost" className="min-h-9 px-2 text-sm" disabled={pending === gap.capability_id} onClick={() => toggle(gap)}>
                        {gap.user_has_it ? "Actually, I don't" : "I have this"}
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
