"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowIcon, CheckIcon, PlusIcon } from "@/components/icons";
import { useProfile } from "@/components/profile-context";
import { useToast } from "@/components/toast";
import { Button, Card, Chip, ErrorNotice, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { DomainBadge } from "@/lib/domains";
import { useAsync } from "@/lib/hooks";
import { MAX_FIELDS, type CapabilityRef } from "@/lib/types";

function SkillList({ title, items, owned }: { title: string; items: CapabilityRef[]; owned: Set<string> }) {
  if (!items.length) return null;
  return (
    <div>
      <h3 className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">{title}</h3>
      <ul className="flex flex-wrap gap-2">
        {items.map((c) => {
          const has = owned.has(c.id);
          return (
            <li
              key={c.id}
              className={
                has
                  ? "inline-flex items-center gap-1.5 rounded-full bg-good-soft px-3 py-1.5 text-sm font-semibold text-good"
                  : "inline-flex items-center rounded-full border border-line bg-surface px-3 py-1.5 text-sm font-medium"
              }
            >
              {has && <CheckIcon width={14} height={14} />}
              {c.name}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function RolePage() {
  const { id } = useParams<{ id: string }>();
  const { profile, setProfile } = useProfile();
  const toast = useToast();
  const { data: role, error, reload } = useAsync((signal) => api.roleDetail(id, signal), `role:${id}`);
  const [busy, setBusy] = useState(false);

  const following = profile.target_roles.some((r) => r.id === id);
  const owned = new Set(profile.capabilities.map((c) => c.id));

  async function toggleFollow() {
    if (!role) return;
    setBusy(true);
    try {
      const roles = following ? profile.target_roles.filter((r) => r.id !== id) : [...profile.target_roles, { id, title: role.title }];
      const domains = new Set(profile.domains.map((d) => d.id));
      if (!following && role.domain && domains.size < MAX_FIELDS) domains.add(role.domain.id);
      setProfile(
        await api.putTargets(profile.user_id, {
          domain_ids: [...domains],
          target_role_ids: roles.map((r) => r.id),
          target_company_ids: profile.target_companies.map((c) => c.id),
          capability_ids: profile.capabilities.map((c) => c.id),
        }),
      );
      toast(following ? `Stopped following ${role.title}.` : `Following ${role.title}. Your feed and skill gaps now include it.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't update that.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !role) return <ErrorNotice message={error.message} onRetry={reload} />;
  if (!role)
    return (
      <div className="space-y-4" aria-busy>
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );

  const tools = role.capabilities.filter((c) => c.kind === "tool");
  const skills = role.capabilities.filter((c) => c.kind === "skill");
  const have = role.capabilities.filter((c) => owned.has(c.id)).length;
  const shownCompanies = role.companies.slice(0, 18);
  const hiddenCompanies = Math.max(0, role.companies_total - shownCompanies.length);

  return (
    <div className="max-w-3xl">
      <Link href="/explore" className="mb-4 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink">
        <ArrowIcon width={14} height={14} className="rotate-180" /> Explore
      </Link>

      <header className="mb-6">
        {role.domain && <DomainBadge name={role.domain.name} />}
        <h1 className="mt-3 font-display text-[32px] leading-[1.08] md:text-[42px]">{role.title}</h1>
        {role.canonical && (
          <p className="mt-2 text-[15px] text-muted">
            A job title for{" "}
            <Link href={`/explore/roles/${role.canonical.id}`} className="font-semibold text-accent underline underline-offset-4">
              {role.canonical.name}
            </Link>
            . The skills below are the ones that role asks for.
          </p>
        )}
        {role.description && <p className="mt-3 max-w-2xl text-[15px] leading-relaxed">{role.description}</p>}
        {role.aliases.length > 0 && <p className="mt-2 text-[15px] text-muted">Also called {role.aliases.join(", ")}.</p>}
        <Button variant={following ? "secondary" : "primary"} className="mt-4" disabled={busy} onClick={toggleFollow}>
          {following ? (
            <>
              <CheckIcon width={18} height={18} /> Following
            </>
          ) : (
            <>
              <PlusIcon width={18} height={18} /> Follow this role
            </>
          )}
        </Button>
      </header>

      <div className="space-y-5">
        <Card className="space-y-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-display text-xl">What employers ask for</h2>
            <p className="text-sm text-muted">
              You have {have} of {role.capabilities.length}
            </p>
          </div>
          <SkillList title="Skills" items={skills} owned={owned} />
          <SkillList title="Tools" items={tools} owned={owned} />
          <p className="text-xs text-muted">
            These lists come from our placeholder role data, not from a specific job posting. They&apos;re a starting point.
          </p>
        </Card>

        <Card>
          <h2 className="font-display text-xl">Who hires for it</h2>
          {role.companies.length ? (
            <>
              <ul className="mt-3 flex flex-wrap gap-2">
                {shownCompanies.map((c) => (
                  <li key={c.id}>
                    <Link href={`/explore/companies/${c.id}`} className="btn-raised inline-flex min-h-9 items-center rounded-full px-3.5 text-sm font-semibold">
                      {c.name}
                    </Link>
                  </li>
                ))}
              </ul>
              {hiddenCompanies > 0 && <p className="mt-3 text-sm text-muted">and {hiddenCompanies.toLocaleString()} more</p>}
            </>
          ) : (
            <p className="mt-2 text-[15px] text-muted">We don&apos;t have companies listed for this role yet.</p>
          )}
        </Card>

        {role.variants.length > 0 && (
          <Card>
            <h2 className="font-display text-xl">Other titles for this job</h2>
            <p className="mt-1 text-sm text-muted">Employers use these names for the same work.</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {role.variants.map((v) => (
                <li key={v}>
                  <Chip>{v}</Chip>
                </li>
              ))}
            </ul>
          </Card>
        )}

        {role.related_roles.length > 0 && (
          <Card>
            <h2 className="font-display text-xl">Roles with a similar skill set</h2>
            <p className="mt-1 text-sm text-muted">Good next moves if this role isn&apos;t quite right.</p>
            <ul className="mt-3 divide-y divide-line">
              {role.related_roles.map((r) => (
                <li key={r.role.id}>
                  <Link href={`/explore/roles/${r.role.id}`} className="flex items-start justify-between gap-3 py-3 hover:text-accent">
                    <span>
                      <span className="block font-semibold">{r.role.title}</span>
                      <span className="mt-1 flex flex-wrap gap-1">
                        {r.shared_capabilities.slice(0, 4).map((s) => (
                          <Chip key={s}>{s}</Chip>
                        ))}
                      </span>
                    </span>
                    <span className="shrink-0 font-mono text-xs text-muted">{Math.round(r.similarity * 100)}% overlap</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}
