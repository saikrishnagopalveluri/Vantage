// Generates the PWA icon set from one vector mark. Run: npm run icons
import { mkdirSync, writeFileSync } from "node:fs";
import sharp from "sharp";

const INK = "#1d1a16";
const AMBER = "#f59e0b";

// A "V" with a point above it: a vantage point.
const mark = (size, scale) => {
  const s = size * scale;
  const o = (size - s) / 2;
  const p = (x, y) => `${(o + (x / 512) * s).toFixed(1)} ${(o + (y / 512) * s).toFixed(1)}`;
  return `
    <path d="M ${p(132, 176)} L ${p(256, 388)} L ${p(380, 176)}" fill="none" stroke="${AMBER}"
      stroke-width="${((46 / 512) * s).toFixed(1)}" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${(o + (256 / 512) * s).toFixed(1)}" cy="${(o + (108 / 512) * s).toFixed(1)}"
      r="${((28 / 512) * s).toFixed(1)}" fill="${AMBER}"/>`;
};

const svg = (size, { radius = 0, scale = 0.86 } = {}) => `
  <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <rect width="${size}" height="${size}" rx="${radius}" fill="${INK}"/>${mark(size, scale)}
  </svg>`;

mkdirSync("public/icons", { recursive: true });

const targets = [
  ["public/icons/icon-192.png", 192, { radius: 44 }],
  ["public/icons/icon-512.png", 512, { radius: 118 }],
  // Maskable keeps the mark inside the central safe zone; the OS applies its own shape.
  ["public/icons/maskable-512.png", 512, { scale: 0.6 }],
  // iOS rounds the corners itself, so this one is full-bleed.
  ["public/icons/apple-touch-icon.png", 180, { scale: 0.7 }],
];
for (const [file, size, opts] of targets) {
  await sharp(Buffer.from(svg(size, opts))).png().toFile(file);
  console.log("wrote", file);
}

writeFileSync("public/icon.svg", svg(512, { radius: 118 }).trim());
console.log("wrote public/icon.svg");
