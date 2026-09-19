"use client";

import { useState } from "react";
import { BookmarkIcon, ExternalIcon } from "@/components/icons";
import { useProfile } from "@/components/profile-context";
import { useToast } from "@/components/toast";
import { Button, EmptyState, ErrorNotice, LinkButton, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useAsync } from "@/lib/hooks";

export default function SavedPage() {
  const { profile } = useProfile();
  const toast = useToast();
  const { data, error, reload } = useAsync((signal) => api.saved(profile.user_id, signal), `saved:${profile.user_id}`);
  const [removed, setRemoved] = useState<Set<string>>(new Set());

  async function unsave(id: string) {
    setRemoved((r) => new Set(r).add(id));
    try {
      await api.interact(profile.user_id, id, "unsave");
    } catch (e) {
      setRemoved((r) => {
        const next = new Set(r);
        next.delete(id);
        return next;
      });
      toast(e instanceof Error ? e.message : "Couldn't remove that.");
    }
  }

  const items = (data ?? []).filter((i) => !removed.has(i.id));

  return (
    <>
      <PageHeader eyebrow="Saved" title="Your reading list" subtitle="Stories you set aside for later." />
      {error && !data ? (
        <ErrorNotice message={error.message} onRetry={reload} />
      ) : !data ? (
        <div className="space-y-3" aria-busy>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nothing saved yet" action={<LinkButton href="/feed" variant="primary">Go to your feed</LinkButton>}>
          Tap Save on a story and it will wait here.
        </EmptyState>
      ) : (
        <ul className="max-w-3xl space-y-3">
          {items.map((item, i) => (
            <li key={item.id} style={{ "--n": i } as React.CSSProperties} className="rise raised rounded-2xl p-4">
              <p className="text-xs text-muted">
                {item.source.name} · {timeAgo(item.published_at)} · saved {timeAgo(item.saved_at)}
              </p>
              <h2 className="mt-1.5 font-display text-lg leading-snug">
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:text-accent">
                  {item.title}
                  <ExternalIcon width={14} height={14} className="ml-1.5 inline opacity-50" />
                </a>
              </h2>
              <Button variant="ghost" className="-ml-3 mt-1 min-h-10 text-sm" onClick={() => unsave(item.id)}>
                <BookmarkIcon width={16} height={16} filled />
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
