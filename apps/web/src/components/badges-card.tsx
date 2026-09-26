"use client";

import { useId, useState, type ComponentType } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import type { ShareCard } from "@/lib/share";
import type { Badge, BadgeKind } from "@/lib/types";
import { ShareBar } from "./games/share-bar";
import { BookmarkIcon, CheckIcon, FlameIcon, LightningIcon } from "./icons";
import { Button, cx } from "./ui";

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

function cardFor(badge: Badge): ShareCard {
  return {
    game: SECTION[badge.kind].title.toUpperCase(),
    headlineLabel: "Badge earned",
    headline: badge.label,
    stats: [{ value: formatCurrent(badge.kind, badge.current), label: badge.description }],
    footer: "I just earned this on Vantage",
  };
}

function BadgeTile({ badge }: { badge: Badge }) {
  const [sharing, setSharing] = useState(false);
  const origin = typeof window === "undefined" ? "" : window.location.origin;

  return (
    <li className={cx("rounded-xl border p-3.5", badge.achieved ? "border-accent bg-accent-soft" : "border-line opacity-60")}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold">{badge.label}</p>
          <p className="text-sm text-muted">{badge.description}</p>
        </div>
        {badge.achieved && <CheckIcon width={20} height={20} className="shrink-0 text-accent" />}
      </div>
      {!badge.achieved && (
        <p className="mt-2 text-xs text-muted">
          {formatCurrent(badge.kind, badge.current)} / {formatCurrent(badge.kind, badge.threshold)}
        </p>
      )}
      {badge.achieved && !sharing && (
        <Button className="mt-2.5 min-h-9 px-3 text-sm" onClick={() => setSharing(true)}>
          Share
        </Button>
      )}
      {badge.achieved && sharing && (
        <div className="mt-2.5">
          <ShareBar
            card={cardFor(badge)}
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
                <BadgeTile key={badge.id} badge={badge} />
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
