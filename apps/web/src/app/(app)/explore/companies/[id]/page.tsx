"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowIcon, CheckIcon, ExternalIcon, PlusIcon } from "@/components/icons";
import { useProfile } from "@/components/profile-context";
import { useToast } from "@/components/toast";
import { Button, Card, Chip, ErrorNotice, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { DomainBadge } from "@/lib/domains";
import { timeAgo } from "@/lib/format";
import { useAsync } from "@/lib/hooks";

export default function CompanyPage() {
  const { id } = useParams<{ id: string }>();
  const { profile, setProfile } = useProfile();
  const toast = useToast();
  const { data: company, error, reload } = useAsync((signal) => api.companyDetail(id, signal), `company:${id}`);
  const [busy, setBusy] = useState(false);

  const tracking = profile.target_companies.some((c) => c.id === id);
  const works = profile.current_company?.id === id;

  async function toggleTrack() {
    if (!company) return;
    setBusy(true);
    try {
      const companies = tracking
        ? profile.target_companies.filter((c) => c.id !== id)
        : [...profile.target_companies, { id, name: company.name }];
      setProfile(
        await api.putTargets(profile.user_id, {
          domain_ids: profile.domains.map((d) => d.id),
          target_role_ids: profile.target_roles.map((r) => r.id),
          target_company_ids: companies.map((c) => c.id),
          capability_ids: profile.capabilities.map((c) => c.id),
        }),
      );
      toast(tracking ? `Stopped tracking ${company.name}.` : `Tracking ${company.name}. Its news now ranks higher for you.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't update that.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !company) return <ErrorNotice message={error.message} onRetry={reload} />;
  if (!company)
    return (
      <div className="space-y-4" aria-busy>
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );

  return (
    <div className="max-w-3xl">
      <Link href="/explore" className="mb-4 inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink">
        <ArrowIcon width={14} height={14} className="rotate-180" /> Explore
      </Link>

      <header className="mb-6">
        {company.industry && <Chip>{company.industry.name}</Chip>}
        <h1 className="mt-3 font-display text-[32px] leading-[1.08] md:text-[42px]">{company.name}</h1>
        {works ? (
          <p className="mt-3 text-[15px] text-muted">You work here, so its news already leads your feed.</p>
        ) : (
          <Button variant={tracking ? "secondary" : "primary"} className="mt-4" disabled={busy} onClick={toggleTrack}>
            {tracking ? (
              <>
                <CheckIcon width={18} height={18} /> Tracking
              </>
            ) : (
              <>
                <PlusIcon width={18} height={18} /> Track this company
              </>
            )}
          </Button>
        )}
      </header>

      <div className="space-y-5">
        <Card>
          <h2 className="font-display text-xl">Recent stories</h2>
          {company.articles.length ? (
            <ul className="mt-3 divide-y divide-line">
              {company.articles.map((a) => (
                <li key={a.id}>
                  <a href={a.url} target="_blank" rel="noopener noreferrer" className="flex items-start justify-between gap-3 py-3 hover:text-accent">
                    <span>
                      <span className="block font-semibold leading-snug">{a.title}</span>
                      <span className="mt-0.5 block text-xs text-muted">
                        {a.source.name} · {timeAgo(a.published_at)}
                      </span>
                    </span>
                    <ExternalIcon width={15} height={15} className="mt-1 shrink-0 opacity-50" />
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-[15px] text-muted">Nothing recent. We&apos;ll list stories here as they appear.</p>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-xl">Roles it hires for</h2>
          <p className="mt-1 text-sm text-muted">Based on placeholder hiring data for this industry.</p>
          <div className="mt-4 space-y-5">
            {company.roles_by_domain.map((group) => (
              <div key={group.domain?.id ?? "none"}>
                {group.domain && <DomainBadge name={group.domain.name} />}
                <ul className="mt-2.5 flex flex-wrap gap-2">
                  {group.roles.map((r) => (
                    <li key={r.id}>
                      <Link href={`/explore/roles/${r.id}`} className="btn-raised inline-flex min-h-9 items-center rounded-full px-3.5 text-sm font-medium">
                        {r.title}
                      </Link>
                    </li>
                  ))}
                </ul>
                {group.total > group.roles.length && (
                  <p className="mt-2 text-sm text-muted">
                    and {(group.total - group.roles.length).toLocaleString()} more. <span className="text-xs">Search Explore for a specific title.</span>
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
