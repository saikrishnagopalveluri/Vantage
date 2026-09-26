"use client";

import { useId, useState, type ComponentType, type CSSProperties } from "react";
import { api } from "@/lib/api";
import { badgeShareCard, drawBadgeCard } from "@/lib/badge-share";
import { useAsync } from "@/lib/hooks";
import type { Badge, BadgeKind } from "@/lib/types";
import { ShareBar } from "./games/share-bar";
import { BookmarkIcon, CheckIcon, FlameIcon, LightningIcon } from "./icons";
import { Button, Chip, cx } from "./ui";

const SECTION: Record<BadgeKind, { title: string; icon: ComponentType<{ width: number; height: number }> }> = {
  streak: { title: "Showing up", icon: FlameIcon },
  articles: { title: "Reading", icon: BookmarkIcon },
  time: { title: "Time on Vantage", icon: LightningIcon },
};

function formatCurrent(kind: BadgeKind, seconds: number): string {
  if (kind !== "time") return String(seconds);
  const hours = seconds / 3600;
  return hours >= 1 ? `${Math.floor(hours)}h` : `${Math.floor(seconds / 60)}m`;
}

function BadgeTile({ badge, index }: { badge: Badge; index: number }) {
  const [sharing, setSharing] = useState(false);
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const Icon = SECTION[badge.kind].icon;
  const pct = Math.min(100, Math.round((badge.current / badge.threshold) * 100));

  return (
    <li
      className={cx(
        "rise flex flex-col rounded-xl border p-3.5",
        badge.achieved ? "border-accent bg-accent-soft" : "border-line bg-surface",
      )}
      style={{ "--n": index } as CSSProperties}
    >
      <div className="flex items-start gap-3">
        <div
          className={cx(
            "flex size-10 shrink-0 items-center justify-center rounded-full",
            badge.achieved ? "bg-accent text-accent-ink" : "bg-paper text-muted",
          )}
          aria-hidden
        >
          <Icon width={18} height={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold">{badge.label}</p>
            {badge.achieved && (
              <Chip tone="accent">
                <CheckIcon width={12} height={12} /> Earned
              </Chip>
            )}
          </div>
          <p className="text-sm text-muted">{badge.description}</p>
        </div>
      </div>

      {!badge.achieved && (
        <div className="mt-3">
          <div className="h-1.5 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-1.5 text-xs text-muted">
            {formatCurrent(badge.kind, badge.current)} / {formatCurrent(badge.kind, badge.threshold)}
          </p>
        </div>
      )}

      {badge.achieved && !sharing && (
        <Button className="mt-3 min-h-9 self-start px-3 text-sm" onClick={() => setSharing(true)}>
          Share this badge
        </Button>
      )}
      {badge.achieved && sharing && (
        <div className="mt-3">
          <ShareBar
            card={badgeShareCard(badge)}
            draw={drawBadgeCard}
            heading="Post your badge"
            subheading="Your post shows only this badge. Not your name, email or profile."
            fileName={`vantage-${badge.id}.png`}
            shareTitle={`${badge.label} — Vantage`}
            shareText={`I just earned the "${badge.label}" badge on Vantage: ${badge.description}.`}
            url={origin}
          />
        </div>
      )}
    </li>
  );
}

export function BadgesCard({ userId }: { userId: string }) {
  const titleId = useId();
  const { data } = useAsync((signal) => api.badges(userId, signal), `badges:${userId}`);
  if (!data) return null;

  const byKind = (kind: BadgeKind) => data.badges.filter((b) => b.kind === kind);
  const earned = data.badges.filter((b) => b.achieved).length;
  let i = 0;

  return (
    <section aria-labelledby={titleId} className="raised rounded-2xl p-4 md:p-5">
      <div className="flex items-baseline justify-between">
        <h2 id={titleId} className="font-display text-xl">
          Achievements
        </h2>
        <p className="text-sm text-muted">
          {earned} of {data.badges.length}
        </p>
      </div>
      {(Object.keys(SECTION) as BadgeKind[]).map((kind) => {
        const Icon = SECTION[kind].icon;
        return (
          <div key={kind} className="mt-4">
            <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-muted">
              <Icon width={16} height={16} />
              {SECTION[kind].title}
            </p>
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {byKind(kind).map((badge) => (
                <BadgeTile key={badge.id} badge={badge} index={i++} />
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
