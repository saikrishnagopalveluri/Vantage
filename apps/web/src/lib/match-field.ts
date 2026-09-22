/** Rules and helpers for Match the Field: tap a company, then tap the industry it belongs to. No lives, no
 *  clock — just real companies and industries from the taxonomy, matched at your own pace. Kept free of
 *  React so it can be tested on its own, the same way quiz.ts and speed-round.ts are. */

export const PAIRS_PER_ROUND = 5;
export const MIN_PAIRS = 4; // if fewer than this many distinct industries turn up, ask for a fresh batch

export interface MatchPair {
  id: string; // the company id; also doubles as the pair id
  left: string; // the company name
  right: string; // its industry name
}

export interface MatchState {
  pairs: MatchPair[];
  leftOrder: string[]; // pair ids, left column order
  rightOrder: string[]; // pair ids, right column order (shuffled separately, so it's a real puzzle)
  matched: Set<string>;
  selectedLeft: string | null;
  mistakes: number;
}

function shuffled<T>(items: T[]): T[] {
  const a = [...items];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Picks up to PAIRS_PER_ROUND companies with distinct industries, so every match has exactly one right answer. */
export function pickPairs(companies: { id: string; name: string; industry: { name: string } | null }[]): MatchPair[] {
  const seenIndustries = new Set<string>();
  const pairs: MatchPair[] = [];
  for (const c of shuffled(companies)) {
    if (!c.industry || seenIndustries.has(c.industry.name)) continue;
    seenIndustries.add(c.industry.name);
    pairs.push({ id: c.id, left: c.name, right: c.industry.name });
    if (pairs.length >= PAIRS_PER_ROUND) break;
  }
  return pairs;
}

export function newMatchState(pairs: MatchPair[]): MatchState {
  const ids = pairs.map((p) => p.id);
  return { pairs, leftOrder: shuffled(ids), rightOrder: shuffled(ids), matched: new Set(), selectedLeft: null, mistakes: 0 };
}

/** Tapping a company selects it, or clears the selection if it's tapped again. Matched companies can't be selected. */
export function selectLeft(state: MatchState, id: string): MatchState {
  if (state.matched.has(id)) return state;
  return { ...state, selectedLeft: state.selectedLeft === id ? null : id };
}

/** Tapping an industry with a company selected checks the pair. A right answer locks both in; a wrong one
 *  just clears the selection, so it costs nothing but a moment. */
export function tryMatch(state: MatchState, rightId: string): { state: MatchState; correct: boolean } {
  if (!state.selectedLeft || state.matched.has(rightId)) return { state, correct: false };
  const correct = state.selectedLeft === rightId;
  if (correct) {
    return { state: { ...state, matched: new Set(state.matched).add(rightId), selectedLeft: null }, correct: true };
  }
  return { state: { ...state, selectedLeft: null, mistakes: state.mistakes + 1 }, correct: false };
}

export const isSolved = (state: MatchState): boolean => state.pairs.length > 0 && state.matched.size === state.pairs.length;

// ---- best time -------------------------------------------------------------------------------------------------------

const BEST_KEY = "vantage.matchfield.best";

export interface MatchBest {
  seconds: number;
  mistakes: number;
}

export function readMatchBest(): MatchBest | null {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as Partial<MatchBest>;
    return typeof v.seconds === "number" ? { seconds: v.seconds, mistakes: v.mistakes ?? 0 } : null;
  } catch {
    return null;
  }
}

/** Saves the round if it finished faster than the stored best. Returns whether it did. */
export function saveMatchIfBest(seconds: number, mistakes: number): boolean {
  const best = readMatchBest();
  if (best && best.seconds <= seconds) return false;
  try {
    window.localStorage.setItem(BEST_KEY, JSON.stringify({ seconds, mistakes }));
  } catch {}
  return true;
}
