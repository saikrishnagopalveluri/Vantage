import { cx } from "./ui";

export const PARTNER = { name: "DOT Club", place: "IBS Hyderabad" } as const;

/**
 * The partner credit: the DOT Club logo on a white tile (so it reads the same in light and dark themes) and the line
 * "Powered by DOT Club, IBS Hyderabad". The logo is decorative next to the text, but has a name for anyone who can't see it.
 */
export function PartnerBadge({ size = "md", className }: { size?: "sm" | "md" | "lg"; className?: string }) {
  const px = size === "sm" ? 40 : size === "lg" ? 88 : 56;
  return (
    <div className={cx("flex items-center gap-3", className)}>
      <span className="flex shrink-0 items-center justify-center rounded-xl border border-line bg-white p-1">
        <picture>
          <source srcSet="/partners/dot-club-sm.webp" type="image/webp" />
          {/* A plain image on purpose: it is a small fixed asset, already sized and compressed. */}
          <img src="/partners/dot-club-sm.png" alt="DOT Club logo" width={px} height={Math.round(px * 1.096)} loading="lazy" decoding="async" />
        </picture>
      </span>
      <p className={cx("leading-snug text-muted", size === "sm" ? "text-[13px]" : "text-sm")}>
        Powered by <span className="font-semibold text-ink">{PARTNER.name}</span>, {PARTNER.place}
      </p>
    </div>
  );
}
