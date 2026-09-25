/**
 * Sharing helpers shared by every mini-game's "over" screen: a portrait score card drawn on a canvas,
 * in the app's own colours, so it can be posted or saved as an image — never a name or a profile, only
 * the score. Modelled on quiz.ts/share-card.ts's already-shipped Pop Quiz sharing, generalised so Speed
 * Round, Match the Field and Word Drop can reuse the same card and the same WhatsApp/LinkedIn/X intents
 * instead of each drawing their own. Kept free of React, the same way the games' own rule modules are.
 */

export { intents } from "./quiz";

export interface ShareCard {
  game: string; // shown top-right, e.g. "SPEED ROUND"
  headlineLabel: string; // small label above the headline, e.g. "SCORE" or "MATCHED"
  headline: string; // the big central number or word
  accentLabel?: string; // an optional second small block under the headline, e.g. "ACCURACY"
  accent?: string; // its value, drawn in the accent colour
  stats: { value: string; label: string }[]; // 1 to 3 stat tiles
  footer: string; // e.g. "Think you can beat it?"
}

const W = 1080;
const H = 1350;
// Always the light palette, so a shared card looks the same whatever theme the player uses.
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

export async function drawShareCard(card: ShareCard, origin: string): Promise<Blob> {
  const serif = family("--font-fraunces", 'Georgia, "Times New Roman", serif');
  const mono = family("--font-plex", 'ui-monospace, Menlo, Consolas, monospace');
  const sans = family("--font-source", "system-ui, -apple-system, Segoe UI, sans-serif");
  try {
    await Promise.all([document.fonts.load(`700 120px ${serif}`), document.fonts.load(`500 30px ${mono}`), document.fonts.load(`400 30px ${sans}`)]);
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

  // Header
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
  ctx.fillText(card.game, W - 130, 176);
  ctx.textAlign = "left";
  ctx.strokeStyle = COLOR.line;
  ctx.beginPath();
  ctx.moveTo(130, 220);
  ctx.lineTo(W - 130, 220);
  ctx.stroke();

  // Headline
  ctx.textAlign = "center";
  ctx.fillStyle = COLOR.muted;
  ctx.font = `500 28px ${mono}`;
  spaced(6);
  ctx.fillText(card.headlineLabel.toUpperCase(), W / 2, 330);
  spaced(0);
  let size = 300;
  ctx.font = `700 ${size}px ${serif}`;
  while (ctx.measureText(card.headline).width > W - 300 && size > 100) {
    size -= 10;
    ctx.font = `700 ${size}px ${serif}`;
  }
  ctx.fillStyle = COLOR.ink;
  ctx.fillText(card.headline, W / 2, 330 + 40 + size * 0.78);

  // Accent (optional second block, e.g. a rank title or an accuracy figure)
  let statsY = 800;
  if (card.accent && card.accentLabel) {
    const accentY = 330 + 40 + size * 0.78 + 130;
    ctx.fillStyle = COLOR.muted;
    ctx.font = `500 28px ${mono}`;
    spaced(6);
    ctx.fillText(card.accentLabel.toUpperCase(), W / 2, accentY);
    spaced(0);
    ctx.fillStyle = COLOR.accent;
    ctx.font = `700 96px ${serif}`;
    ctx.fillText(card.accent, W / 2, accentY + 105);
    statsY = accentY + 200;
  }

  // Stats
  if (card.stats.length > 0) {
    statsY = Math.max(statsY, 1000);
    const colW = (W - 260) / card.stats.length;
    card.stats.forEach(({ value, label }, i) => {
      const cx = 130 + colW * i + colW / 2;
      rounded(ctx, 130 + colW * i + 8, statsY, colW - 16, 170, 24);
      ctx.fillStyle = COLOR.paper;
      ctx.fill();
      ctx.fillStyle = COLOR.ink;
      ctx.font = `700 76px ${serif}`;
      ctx.fillText(value, cx, statsY + 92);
      ctx.fillStyle = COLOR.muted;
      ctx.font = `400 28px ${sans}`;
      ctx.fillText(label, cx, statsY + 140);
    });
  }

  // Footer
  ctx.fillStyle = COLOR.ink;
  ctx.font = `700 40px ${serif}`;
  ctx.fillText(card.footer, W / 2, 1226);
  ctx.fillStyle = COLOR.muted;
  ctx.font = `400 28px ${sans}`;
  ctx.fillText(origin.replace(/^https?:\/\//, ""), W / 2, 1266);
  ctx.font = `400 24px ${sans}`;
  ctx.fillText("Powered by DOT Club, IBS Hyderabad", W / 2, 1326);

  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Couldn't make the image."))), "image/png"));
}
