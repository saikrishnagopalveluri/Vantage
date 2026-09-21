/**
 * The picture that goes with a shared result: a portrait card in the app's own colours, drawn on a canvas so it
 * can be posted or saved as an image. It shows the score and title only, never a name or a profile.
 */
import { RANKS, type Result } from "./quiz";

const W = 1080;
const H = 1350;
// Always the light palette, so a shared card looks the same whatever theme the player uses.
const COLOR = { paper: "#f6f2ea", surface: "#fffdf8", ink: "#1d1a16", muted: "#625a4f", line: "#e4dccd", accent: "#a94d08", accentSoft: "#fbead0" };

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

export async function drawShareCard(result: Result, origin: string): Promise<Blob> {
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
  ctx.fillText("POP QUIZ", W - 130, 176);
  ctx.textAlign = "left";
  ctx.strokeStyle = COLOR.line;
  ctx.beginPath();
  ctx.moveTo(130, 220);
  ctx.lineTo(W - 130, 220);
  ctx.stroke();

  // Score
  ctx.textAlign = "center";
  ctx.fillStyle = COLOR.muted;
  ctx.font = `500 28px ${mono}`;
  spaced(6);
  ctx.fillText("MY SCORE", W / 2, 330);
  spaced(0);
  const points = result.score.toLocaleString("en-IN");
  let size = 300;
  ctx.font = `700 ${size}px ${serif}`;
  while (ctx.measureText(points).width > W - 300 && size > 100) {
    size -= 10;
    ctx.font = `700 ${size}px ${serif}`;
  }
  ctx.fillStyle = COLOR.ink;
  ctx.fillText(points, W / 2, 330 + 40 + size * 0.78);

  // Rank
  const rankY = 330 + 40 + size * 0.78 + 130;
  ctx.fillStyle = COLOR.muted;
  ctx.font = `500 28px ${mono}`;
  spaced(6);
  ctx.fillText("MY TITLE", W / 2, rankY);
  spaced(0);
  ctx.fillStyle = COLOR.accent;
  ctx.font = `700 96px ${serif}`;
  ctx.fillText(RANKS[result.rank].title, W / 2, rankY + 105);

  // Stats
  const statsY = 1000;
  const stats: [string, string][] = [[String(result.correct), "right"], [String(result.bestStreak), "best streak"], [String(result.level), "level reached"]];
  const colW = (W - 260) / 3;
  stats.forEach(([value, label], i) => {
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

  // Footer
  ctx.fillStyle = COLOR.ink;
  ctx.font = `700 40px ${serif}`;
  ctx.fillText("Think you can beat it?", W / 2, 1226);
  ctx.fillStyle = COLOR.muted;
  ctx.font = `400 28px ${sans}`;
  ctx.fillText(origin.replace(/^https?:\/\//, ""), W / 2, 1266);
  ctx.font = `400 24px ${sans}`;
  ctx.fillText("Powered by DOT Club, IBS Hyderabad", W / 2, 1326);

  return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Couldn't make the image."))), "image/png"));
}
