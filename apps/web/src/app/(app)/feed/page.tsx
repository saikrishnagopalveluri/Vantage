"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { FeedCard } from "@/components/feed-card";
import { ArrowIcon } from "@/components/icons";
import { useProfile } from "@/components/profile-context";
import { useToast } from "@/components/toast";
import { Button, Card, EmptyState, ErrorNotice, LinkButton, Segmented, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { DomainIcon, domainStyle, slugFor } from "@/lib/domains";
import { greeting, timeAgo } from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import type { Feed, FeedItem, Lens, NamedRef } from "@/lib/types";

const LENSES: { id: Lens; label: string }[] = [
  { id: "for_you", label: "For you" },
  { id: "companies", label: "Companies" },
  { id: "skills", label: "Skills" },
  { id: "newsletters", label: "Newsletters" },
];

const EMPTY_COPY: Record<Lens, { title: string; body: string }> = {
  for_you: {
    title: "Nothing new for you yet",
    body: "We check our sources through the day. Follow another field or a few more companies and this fills up faster.",
  },
  companies: {
    title: "Your companies are quiet",
    body: "When a company you follow or work for is in the news, the story lands here.",
  },
  skills: {
    title: "No skill news right now",
    body: "Stories about skills and tools you haven't picked up yet will show up here.",
  },
  newsletters: {
    title: "No newsletter posts match you yet",
    body: "We read Substack and other independent newsletters on technology, strategy, finance and product, and keep the posts that fit your fields, roles and companies. New ones arrive through the day.",
  },
};

const STALE_AFTER_MS = 10 * 60_000;

interface State {
  at: number;
  key: string;
  items: FeedItem[];
  summary: Feed["summary"] | null;
  hasMore: boolean;
  error: string | null;
}

function summaryLine(s: Feed["summary"] | null): string {
  if (!s || s.total === 0) return "We'll line up what matters as soon as something new comes in.";
  const first = s.critical + s.relevant;
  const noun = s.total === 1 ? "story matches" : "stories match";
  if (first === 0) return `${s.total} ${noun} what you follow. None are urgent.`;
  return `${s.total} ${noun} what you follow. ${first} ${first === 1 ? "is" : "are"} worth reading first.`;
}

function Rail({ userId, focus }: { userId: string; focus: NamedRef[] }) {
  const { profile } = useProfile();
  const { data } = useAsync((signal) => api.skillGaps(userId, signal), `rail:${userId}:${profile.capabilities.length}`);
  const gaps = (data?.target_roles ?? [])
    .flatMap((r) => r.capabilities.filter((c) => !c.user_has_it).map((c) => ({ ...c, role: r.role_title })))
    .sort((a, b) => b.gap_ratio - a.gap_ratio)
    .slice(0, 4);

  return (
    <aside className="hidden lg:block">
      <div className="sticky top-8 space-y-4">
        <Card>
          <h2 className="font-display text-lg">What you follow</h2>
          {focus.length ? (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {focus.map((d) => (
                <li key={d.id} style={domainStyle(slugFor(d.name))} className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold">
                  <DomainIcon slug={slugFor(d.name)} size={13} />
                  {d.name}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted">Pick a field on your profile to tune the feed.</p>
          )}
          <Link href="/profile" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-accent">
            Change <ArrowIcon width={14} height={14} />
          </Link>
        </Card>

        <Card>
          <h2 className="font-display text-lg">Skills to build next</h2>
          {gaps.length ? (
            <ul className="mt-3 space-y-3">
              {gaps.map((g) => (
                <li key={`${g.role}-${g.capability_id}`}>
                  <div className="flex items-baseline justify-between gap-2 text-sm">
                    <span className="font-semibold">{g.name}</span>
                    <span className="font-mono text-xs text-muted">
                      {g.required_by_count}/{g.required_by_total}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-sunken" aria-hidden>
                    <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(g.gap_ratio * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-muted">Add a target role and we&apos;ll show what the companies you want ask for.</p>
          )}
          <Link href="/career" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-accent">
            See all gaps <ArrowIcon width={14} height={14} />
          </Link>
        </Card>
      </div>
    </aside>
  );
}

export default function FeedPage() {
  const { profile } = useProfile();
  const toast = useToast();
  const userId = profile.user_id;

  const [lens, setLens] = useState<Lens>("for_you");
  const [domainId, setDomainId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<State>({ at: 0, key: "", items: [], summary: null, hasMore: false, error: null });
  const [now, setNow] = useState(() => Date.now());
  const [loadingMore, setLoadingMore] = useState(false);

  const key = `${lens}|${domainId ?? ""}#${tick}`;
  const loading = state.key !== key;

  // The fields a reader follows, plus the field of any role they want or hold.
  const focus: NamedRef[] = [...profile.domains];
  for (const role of [...profile.target_roles, ...(profile.current_role ? [profile.current_role] : [])]) {
    if (role.domain && !focus.some((d) => d.id === role.domain!.id)) focus.push(role.domain);
  }

  useEffect(() => {
    const controller = new AbortController();
    api.feed(userId, lens, 0, domainId, controller.signal).then(
      (feed) => {
        if (controller.signal.aborted) return;
        setState({ at: Date.now(), key, items: feed.items, summary: feed.summary, hasMore: feed.has_more, error: null });
      },
      (error: Error) => {
        if (!controller.signal.aborted) setState((s) => ({ ...s, key, error: error.message }));
      },
    );
    return () => controller.abort();
  }, [userId, lens, domainId, key]);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  // Feeds are pulled every hour, so quietly refresh when the reader comes back to a stale screen.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      setNow(Date.now());
      if (state.at && Date.now() - state.at > STALE_AFTER_MS) reload();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [state.at, reload]);

  const patch = (id: string, changes: Partial<FeedItem>) =>
    setState((s) => ({ ...s, items: s.items.map((i) => (i.id === id ? { ...i, ...changes } : i)) }));

  async function toggleSave(item: FeedItem) {
    patch(item.id, { saved: !item.saved });
    try {
      await api.interact(userId, item.id, item.saved ? "unsave" : "save");
    } catch (e) {
      patch(item.id, { saved: item.saved });
      toast(e instanceof Error ? e.message : "Couldn't save that one.");
    }
  }

  async function dismiss(item: FeedItem) {
    setState((s) => ({ ...s, items: s.items.filter((i) => i.id !== item.id) }));
    try {
      await api.interact(userId, item.id, "dismiss");
      toast("Got it. You'll see less like this.", {
        actionLabel: "Undo",
        onAction: () => api.interact(userId, item.id, "undismiss").then(reload, reload),
      });
    } catch (e) {
      reload();
      toast(e instanceof Error ? e.message : "Couldn't hide that one.");
    }
  }

  const loadMore = useCallback(async () => {
    setLoadingMore(true);
    try {
      const page = await api.feed(userId, lens, state.items.length, domainId);
      setState((s) => {
        const seen = new Set(s.items.map((i) => i.id));
        return { ...s, items: [...s.items, ...page.items.filter((i) => !seen.has(i.id))], hasMore: page.has_more };
      });
    } catch (e) {
      toast(e instanceof Error ? e.message : "Couldn't load more.");
    } finally {
      setLoadingMore(false);
    }
  }, [userId, lens, domainId, state.items.length, toast]);

  // Load the next page when the reader gets near the end.
  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = sentinel.current;
    if (!node || !state.hasMore || loadingMore || loading) return;
    const observer = new IntersectionObserver((entries) => entries[0].isIntersecting && void loadMore(), { rootMargin: "600px" });
    observer.observe(node);
    return () => observer.disconnect();
  }, [state.hasMore, loadingMore, loading, loadMore]);

  const noTargets = profile.target_roles.length === 0 && profile.target_companies.length === 0 && profile.domains.length === 0 && !profile.current_company;
  const [lead, ...rest] = state.items;

  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_19rem] lg:gap-10">
      <div className="min-w-0">
        <header className="mb-5 mt-1">
          <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
            {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
          </p>
          <h1 className="font-display text-[30px] leading-[1.1] md:text-[38px]">{greeting()}</h1>
          <p className="mt-2 max-w-xl text-[15px] text-muted">{summaryLine(state.summary)}</p>
          {state.at > 0 && (
            <p className="mt-1.5 flex items-center gap-1 text-xs text-muted">
              Updated {timeAgo(new Date(state.at).toISOString(), now)}
              <button onClick={reload} disabled={loading} className="-my-3.5 inline-flex min-h-11 items-center px-2 font-semibold text-accent disabled:opacity-50">
                {loading ? "Refreshing" : "Refresh"}
              </button>
            </p>
          )}
        </header>

        <div className="sticky top-12 z-20 -mx-4 space-y-2.5 bg-paper/95 px-4 pb-3 pt-2 backdrop-blur md:top-0 md:mx-0 md:px-0">
          <Segmented label="Feed lens" options={LENSES} value={lens} onChange={setLens} />
          {focus.length > 1 && (
            <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:px-0" role="group" aria-label="Filter by field">
              <button
                onClick={() => setDomainId(null)}
                aria-pressed={domainId === null}
                className={cx(
                  "min-h-9 shrink-0 rounded-full border px-3.5 text-sm font-semibold transition-colors",
                  domainId === null ? "border-ink bg-ink text-paper" : "border-line text-muted hover:text-ink",
                )}
              >
                All fields
              </button>
              {focus.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setDomainId(domainId === d.id ? null : d.id)}
                  aria-pressed={domainId === d.id}
                  style={domainId === d.id ? domainStyle(slugFor(d.name)) : undefined}
                  className={cx(
                    "inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-full border px-3.5 text-sm font-semibold transition-colors",
                    domainId === d.id ? "border-transparent" : "border-line text-muted hover:text-ink",
                  )}
                >
                  <DomainIcon slug={slugFor(d.name)} size={14} />
                  {d.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div role="tabpanel" className="mt-3 space-y-4">
          {loading && state.items.length === 0 ? (
            [0, 1, 2].map((n) => (
              <div key={n} className="raised rounded-2xl p-5" aria-busy>
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="mt-3 h-6 w-full" />
                <Skeleton className="mt-2 h-6 w-2/3" />
                <Skeleton className="mt-4 h-20 w-full" />
              </div>
            ))
          ) : state.error && state.items.length === 0 ? (
            <ErrorNotice message={state.error} onRetry={reload} />
          ) : state.items.length === 0 ? (
            noTargets ? (
              <EmptyState title="Tell us what you follow" action={<LinkButton href="/profile" variant="primary">Choose your fields</LinkButton>}>
                Pick a field, a role or a few companies, and your feed fills with stories that touch them.
              </EmptyState>
            ) : (
              <EmptyState title={EMPTY_COPY[lens].title}>{EMPTY_COPY[lens].body}</EmptyState>
            )
          ) : (
            <>
              {lead && <FeedCard key={lead.id} item={lead} lead onSave={toggleSave} onDismiss={dismiss} onOpen={(i) => void api.interact(userId, i.id, "read").catch(() => {})} />}
              {rest.map((item, i) => (
                <FeedCard
                  key={item.id}
                  item={item}
                  index={i + 1}
                  onSave={toggleSave}
                  onDismiss={dismiss}
                  onOpen={(it) => void api.interact(userId, it.id, "read").catch(() => {})}
                />
              ))}
              <div ref={sentinel} className="flex justify-center pt-2">
                {state.hasMore && (
                  <Button onClick={loadMore} disabled={loadingMore}>
                    {loadingMore ? "Loading…" : "Show more"}
                  </Button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      <Rail userId={userId} focus={focus} />
    </div>
  );
}
