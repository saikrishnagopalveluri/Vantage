"use client";

import { useId, useState } from "react";
import { timeAgo } from "@/lib/format";
import { DomainBadge } from "@/lib/domains";
import type { FeedItem, Tier } from "@/lib/types";
import { BookmarkIcon, CheckIcon, ChevronIcon, CloseIcon, ExternalIcon, EyeIcon } from "./icons";
import { ListenControls } from "./listen-controls";
import { Button, Chip, cx } from "./ui";

const TIER_LABEL: Record<Tier, string> = {
  critical: "Read this",
  relevant: "Relevant",
  explore: "Worth a look",
};

const TIER_STYLE: Record<Tier, string> = {
  critical: "bg-accent text-accent-ink",
  relevant: "bg-accent-soft text-accent",
  explore: "border border-line text-muted",
};

export function RelevanceBadge({ score, tier }: { score: number; tier: Tier }) {
  return (
    <span
      className={cx("inline-flex shrink-0 items-baseline gap-1.5 rounded-md px-3 py-1 text-xs font-semibold", TIER_STYLE[tier])}
      title={`${Math.round(score)} out of 100 for you`}
    >
      <span className="font-mono text-sm">{Math.round(score)}</span>
      {TIER_LABEL[tier]}
    </span>
  );
}

interface Props {
  item: FeedItem;
  index?: number;
  lead?: boolean;
  onSave: (item: FeedItem) => void;
  onDismiss: (item: FeedItem) => void;
  /** The reader went through to the publisher's article. */
  onOpen: (item: FeedItem) => void;
  /** The reader expanded the summary for the first time. */
  onExpand?: (item: FeedItem) => void;
}

/** Which colour a card wears when more than one state applies: saved, then read, then opened. */
function cardState(item: FeedItem): string | undefined {
  if (item.saved) return "card-saved";
  if (item.read) return "card-read";
  if (item.opened) return "card-opened";
  return undefined;
}

/** The state in words and an icon, so the colour is never the only signal. Read replaces opened. */
function StateMarks({ item }: { item: FeedItem }) {
  if (!item.saved && !item.read && !item.opened) return null;
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs font-semibold">
      {item.saved && (
        <span className="inline-flex items-center gap-1 text-accent">
          <BookmarkIcon width={14} height={14} filled />
          Saved for later
        </span>
      )}
      {item.read ? (
        <span className="inline-flex items-center gap-1 text-good">
          <CheckIcon width={14} height={14} />
          Read
        </span>
      ) : (
        item.opened && (
          <span className="inline-flex items-center gap-1 text-opened">
            <EyeIcon width={14} height={14} />
            Opened
          </span>
        )
      )}
    </span>
  );
}

/** Two short paragraphs and a few pointers from the publisher's own feed text. Hidden until asked for. */
function Brief({ item, onOpen }: { item: FeedItem; onOpen: (item: FeedItem) => void }) {
  const brief = item.brief;
  if (!brief || (brief.paragraphs.length === 0 && brief.pointers.length === 0)) {
    return <p className="text-[15px] text-muted">The publisher didn&apos;t share more than the headline. Open the article to read it.</p>;
  }
  return (
    <div className="space-y-3.5 text-[15px] leading-relaxed">
      <ListenControls id={item.id} title={item.title} brief={brief} />
      {brief.paragraphs.map((p) => (
        <p key={p}>{p}</p>
      ))}
      {brief.pointers.length > 0 && (
        <div>
          <p className="font-mono text-xs text-accent">Quick pointers</p>
          <ul className="mt-1.5 list-disc space-y-1.5 pl-5 marker:text-accent">
            {brief.pointers.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}
      {brief.note && <p className="text-sm text-muted">{brief.note}</p>}
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        onClick={() => onOpen(item)}
        className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-accent underline underline-offset-4"
      >
        Read the full story at {item.source.name}
        <ExternalIcon width={14} height={14} />
      </a>
    </div>
  );
}

export function FeedCard({ item, index = 0, lead = false, onSave, onDismiss, onOpen, onExpand }: Props) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const tags = [...item.matched.companies, ...item.matched.roles, ...item.matched.capabilities, ...item.matched.topics].slice(0, lead ? 6 : 4);

  function toggleSummary() {
    const next = !open;
    setOpen(next);
    // Only the first expand counts, and not at all once the story is already read.
    if (next && !item.opened && !item.read) onExpand?.(item);
  }

  return (
    <article
      style={{ "--n": index } as React.CSSProperties}
      className={cx("rise raised rounded-2xl", cardState(item), lead ? "p-4 md:p-7" : "p-4 md:p-5")}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <RelevanceBadge score={item.score} tier={item.tier} />
          {item.domains.slice(0, 2).map((d) => (
            <DomainBadge key={d} name={d} />
          ))}
        </div>
        <StateMarks item={item} />
      </div>
      <p className="mt-2 text-xs text-muted">
        {item.newsletter && <span className="mr-1.5 rounded border border-line px-1.5 py-0.5 font-mono text-xs text-accent">Newsletter</span>}
        {item.source.name} · {timeAgo(item.published_at)}
      </p>

      <h2 className={cx("mt-1.5 font-display leading-[1.15]", lead ? "text-[24px] md:text-[34px]" : "text-[19px] md:text-[22px]")}>
        <a href={item.url} target="_blank" rel="noopener noreferrer" onClick={() => onOpen(item)} className="hover:text-accent">
          {item.title}
          <ExternalIcon width={15} height={15} className="ml-1.5 inline align-baseline opacity-50" />
        </a>
      </h2>

      {item.also_covered_by.length > 0 && (
        <p className="mt-2 text-xs text-muted">Also reported by {item.also_covered_by.join(", ")}</p>
      )}

      {tags.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <li key={tag}>
              <Chip>{tag}</Chip>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3.5 rounded-xl border border-line bg-sunken p-3.5">
        <p className="font-mono text-xs text-accent">Why it matters to you</p>
        <p className="mt-1 text-[15px] leading-snug">{item.why_this_matters}</p>
        <p className="mt-2.5 font-mono text-xs text-accent">What to do</p>
        <p className="mt-1 text-[15px] leading-snug">{item.action}</p>
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={toggleSummary}
          aria-expanded={open}
          aria-controls={panelId}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-lg text-[15px] font-semibold text-accent"
        >
          {open ? "Hide summary" : "Summary and pointers"}
          <ChevronIcon width={18} height={18} className={cx("transition-transform duration-300", open && "rotate-180")} />
        </button>
        <div id={panelId} role="region" aria-label="Summary" hidden={!open} className="rise mt-2 rounded-xl border border-line p-4">
          {open && <Brief item={item} onOpen={onOpen} />}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Button onClick={() => onSave(item)} aria-pressed={item.saved} variant={item.saved ? "primary" : "secondary"} className="px-3.5">
          <BookmarkIcon width={18} height={18} filled={item.saved} />
          {item.saved ? "Saved" : "Save"}
        </Button>
        <Button onClick={() => onDismiss(item)} variant="ghost" className="px-3.5">
          <CloseIcon width={18} height={18} />
          Not for me
        </Button>
      </div>
    </article>
  );
}
