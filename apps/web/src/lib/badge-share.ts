/**
 * The achievement badges' own share card: a small celebratory medallion design, distinct from the
 * games' score card (lib/share.ts) since an achievement reads differently from a score — no
 * opponent to beat, just something earned. Kept free of React for the same Node-testability reason
 * lib/word-drop.ts's *ShareCard builders are.
 */

import type { Badge, BadgeKind } from "./types";

export interface BadgeCard {
  kind: BadgeKind;
  glyph: string;
  label: string;
  description: string;
  statValue: string;
  statLabel: string;
}

const GLYPH: Record<BadgeKind, string> = { streak: "🔥", articles: "📖", time: "⚡" };

function formatCurrent(kind: BadgeKind, seconds: number): string {
  if (kind !== "time") return String(seconds);
  const hours = Math.floor(seconds / 3600);
  return hours >= 1 ? `${hours}h` : `${Math.floor(seconds / 60)}m`;
}

const STAT_LABEL: Record<BadgeKind, string> = { streak: "day streak", articles: "articles read", time: "on Vantage" };

export function badgeShareCard(badge: Badge): BadgeCard {
  return {
    kind: badge.kind,
    glyph: GLYPH[badge.kind],
    label: badge.label,
    description: badge.description,
    statValue: formatCurrent(badge.kind, badge.current),
    statLabel: STAT_LABEL[badge.kind],
  };
}

const W = 1080;
const H = 1350;
const COLOR = { paper: "#f6f2ea", surface: "#fffdf8", ink: "#1d1a16", muted: "#625a4f", line: "#e4dccd", accent: "#a94d08" };

function family(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value ? `${value}, ${fallback}` : fallback;
}

function rounded(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export async function drawBadgeCard(card: BadgeCard, origin: string): Promise<Blob> {
  const serif = family("--font-fraunces", 'Georgia, "Times New Roman", serif');
  const mono = family("--font-plex", 'ui-monospace, Menlo, Consolas, monospace');
  const sans = family("--font-source", "system-ui, -apple-system, Segoe UI, sans-serif");
  try {
    await Promise.all([document.fonts.load(`700 90px ${serif}`), document.fonts.load(`500 26px ${mono}`), document.fonts.load(`400 26px ${sans}`)]);
  } catch {}

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("This browser can't draw the card.");
  const spaced = (px: number) => {
    if ("letterSpacing" in ctx) (ctx as CanvasRenderingContext2D & { letterSpacing: string }).letterSpacing = `${px}px`;
  };

  ctx.fillStyle = COLOR.paper;
  ctx.fillRect(0, 0, W, H);
  rounded(ctx, 60, 60, W - 120, H - 120, 40);
  ctx.fillStyle = COLOR.surface;
  ctx.fill();
  ctx.strokeStyle = COLOR.line;
  ctx.lineWidth = 2;
  ctx.stroke();

  // Header: wordmark left, "ACHIEVEMENT" tag right
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  ctx.fillStyle = COLOR.ink;
  ctx.font = `700 54px ${serif}`;
  spaced(0);
  ctx.fillText("Vantage", 130, 178);
  ctx.fillStyle = COLOR.accent;
  ctx.font = `500 26px ${mono}`;
  spaced(5);
  ctx.textAlign = "right";
  ctx.fillText("ACHIEVEMENT", W - 130, 176);
  ctx.textAlign = "left";
  ctx.strokeStyle = COLOR.line;
  ctx.beginPath();
  ctx.moveTo(130, 220);
  ctx.lineTo(W - 130, 220);
  ctx.stroke();

  // Medallion: a filled accent circle with the badge's glyph
  const medalY = 400;
  const medalR = 130;
  ctx.beginPath();
  ctx.arc(W / 2, medalY, medalR, 0, Math.PI * 2);
  ctx.fillStyle = COLOR.accent;
  ctx.fill();
  ctx.textAlign = "center";
  ctx.font = "130px sans-serif";
  spaced(0);
  ctx.fillText(card.glyph, W / 2, medalY + 46);

  // Label + description
  ctx.fillStyle = COLOR.muted;
  ctx.font = `500 28px ${mono}`;
  spaced(6);
  ctx.fillText("BADGE EARNED", W / 2, 620);
  spaced(0);
  let size = 92;
  ctx.font = `700 ${size}px ${serif}`;
  while (ctx.measureText(card.label).width > W - 260 && size > 48) {
    size -= 4;
    ctx.font = `700 ${size}px ${serif}`;
  }
  ctx.fillStyle = COLOR.ink;
  ctx.fillText(card.label, W / 2, 700 + size * 0.5);
  ctx.fillStyle = COLOR.muted;
  ctx.font = `400 32px ${sans}`;
  ctx.fillText(card.description, W / 2, 700 + size + 60);

  // Stat capsule
  const capW = 560;
  const capY = 900;
  rounded(ctx, W / 2 - capW / 2, capY, capW, 170, 24);
  ctx.fillStyle = COLOR.paper;
  ctx.fill();
  ctx.fillStyle = COLOR.ink;
  ctx.font = `700 76px ${serif}`;
  ctx.fillText(card.statValue, W / 2, capY + 92);
  ctx.fillStyle = COLOR.muted;
  ctx.font = `400 28px ${sans}`;
  ctx.fillText(card.statLabel, W / 2, capY + 140);

  // Footer
  ctx.fillStyle = COLOR.ink;
  ctx.font = `700 40px ${serif}`;
  ctx.fillText("Unlocked on Vantage", W / 2, 1226);
  ctx.fillStyle = COLOR.muted;
  ctx.font = `400 28px ${sans}`;
  ctx.fillText(origin.replace(/^https?:\/\//, ""), W / 2, 1266);
  ctx.font = `400 24px ${sans}`;
  ctx.fillText("Powered by DOT Club, IBS Hyderabad", W / 2, 1326);

  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Couldn't make the image."))), "image/png"));
}
