const UNITS: [number, string][] = [
  [60, "m"],
  [24, "h"],
  [7, "d"],
];

/** "5m ago", "3h ago", "2d ago", then a short date. */
export function timeAgo(iso: string, now = Date.now()): string {
  let value = (now - new Date(iso).getTime()) / 60000;
  if (value < 1) return "just now";
  for (const [size, unit] of UNITS) {
    if (value < size) return `${Math.floor(value)}${unit} ago`;
    value /= size;
  }
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function greeting(hour = new Date().getHours()): string {
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}
