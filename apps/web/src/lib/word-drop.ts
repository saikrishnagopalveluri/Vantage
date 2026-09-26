/** Rules and helpers for Word Drop: guess a real skill or tool from the taxonomy in six tries, Wordle-style.
 *  Kept free of React so it can be tested on its own, the same way the other games' rule modules are. */

import type { ShareCard } from "./share";

export const MAX_GUESSES = 6;
export const MIN_LEN = 4;
export const MAX_LEN = 8;
export const MAX_HINTS = 2;
export const REMEMBER_SEEN = 15; // how many recent words to avoid repeating, before they're fair game again

export type LetterState = "correct" | "present" | "absent";
export type CapabilityKind = "skill" | "tool";

export interface WordTarget {
  word: string;
  kind: CapabilityKind;
}

/** Picks one real skill or tool name that's a clean single word (letters only, a fair length for a
 *  guessing grid). Multi-word or punctuated names ("Power BI", "C++") are skipped: there is no wordlist
 *  behind this game, so a guess only has to be the right length, not a real word, and that only works
 *  cleanly for single tokens. `exclude` (recently-seen words) is honoured only if enough candidates
 *  remain without it — a small taxonomy slice should never make the round fail to start. */
export function pickTarget(capabilities: { name: string; kind: CapabilityKind }[], exclude: string[] = []): WordTarget | null {
  const eligible = capabilities.filter((c) => /^[A-Za-z]+$/.test(c.name.trim()) && c.name.trim().length >= MIN_LEN && c.name.trim().length <= MAX_LEN);
  if (eligible.length === 0) return null;
  const excluded = new Set(exclude.map((w) => w.toUpperCase()));
  const fresh = eligible.filter((c) => !excluded.has(c.name.trim().toUpperCase()));
  const candidates = fresh.length > 0 ? fresh : eligible;
  const picked = candidates[Math.floor(Math.random() * candidates.length)];
  return { word: picked.name.trim().toUpperCase(), kind: picked.kind };
}

/** Per-letter feedback against the target: correct (right letter, right spot), present (right letter,
 *  wrong spot) or absent. A two-pass check, so a repeated letter is never marked present more times than
 *  it actually appears. */
export function scoreGuess(guess: string, target: string): LetterState[] {
  const g = guess.toUpperCase().split("");
  const t = target.toUpperCase().split("");
  const result: LetterState[] = g.map(() => "absent");
  const remaining: Record<string, number> = {};
  g.forEach((ch, i) => {
    if (ch === t[i]) result[i] = "correct";
    else remaining[t[i]] = (remaining[t[i]] ?? 0) + 1;
  });
  g.forEach((ch, i) => {
    if (result[i] === "correct") return;
    if (remaining[ch] > 0) {
      result[i] = "present";
      remaining[ch]--;
    }
  });
  return result;
}

export interface WordState {
  target: string;
  kind: CapabilityKind;
  guesses: string[];
  status: "playing" | "won" | "lost";
  hintsUsed: number;
}

export const newWordState = (target: WordTarget): WordState => ({
  target: target.word,
  kind: target.kind,
  guesses: [],
  status: "playing",
  hintsUsed: 0,
});

/** A hint costs nothing but curiosity: the first reveals whether it's a skill or a tool, the second
 *  reveals the first letter. Capped at MAX_HINTS, and does nothing once the round is over. */
export function takeHint(state: WordState): WordState {
  if (state.status !== "playing" || state.hintsUsed >= MAX_HINTS) return state;
  return { ...state, hintsUsed: state.hintsUsed + 1 };
}

/** What each hint level says, in order. Only `hintsUsed` of these should be shown at once. */
export function hintText(state: WordState): string[] {
  const hints = [`It's a ${state.kind}.`, `Starts with "${state.target[0]}".`];
  return hints.slice(0, state.hintsUsed);
}

/** A guess must already be the right length before it reaches here; the caller checks that against the
 *  target's length and shows its own message for a short or long one. */
export function submitGuess(state: WordState, guess: string): WordState {
  if (state.status !== "playing") return state;
  const g = guess.trim().toUpperCase();
  if (g.length !== state.target.length) return state;
  const guesses = [...state.guesses, g];
  const won = g === state.target;
  const lost = !won && guesses.length >= MAX_GUESSES;
  return { ...state, guesses, status: won ? "won" : lost ? "lost" : "playing" };
}

// ---- best score ------------------------------------------------------------------------------------------------------

const BEST_KEY = "vantage.worddrop.best";

export function readWordBest(): number | null {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) && n > 0 ? n : null;
  } catch {
    return null;
  }
}

/** Only a win counts, and only fewer guesses than the stored best replaces it. Returns whether it did. */
export function saveWordIfBest(state: WordState): boolean {
  if (state.status !== "won") return false;
  const guesses = state.guesses.length;
  const best = readWordBest();
  if (best !== null && best <= guesses) return false;
  try {
    window.localStorage.setItem(BEST_KEY, String(guesses));
  } catch {}
  return true;
}

// ---- recently seen -----------------------------------------------------------------------------------------------------

const SEEN_KEY = "vantage.worddrop.seen";

export function readSeenWords(): string[] {
  try {
    const raw = window.localStorage.getItem(SEEN_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((w): w is string => typeof w === "string") : [];
  } catch {
    return [];
  }
}

/** Keeps only the most recent REMEMBER_SEEN words, newest first, so an older word becomes fair game again. */
export function rememberWord(word: string): void {
  try {
    const seen = [word.toUpperCase(), ...readSeenWords().filter((w) => w !== word.toUpperCase())].slice(0, REMEMBER_SEEN);
    window.localStorage.setItem(SEEN_KEY, JSON.stringify(seen));
  } catch {}
}

// ---- share card ------------------------------------------------------------------------------------------------------

export function wordShareCard(state: WordState): ShareCard {
  return {
    game: "WORD DROP",
    headlineLabel: "solved in",
    headline: `${state.guesses.length} ${state.guesses.length === 1 ? "guess" : "guesses"}`,
    stats: [{ value: state.kind === "tool" ? "Tool" : "Skill", label: "category" }],
    footer: "Think you can beat it?",
  };
}
