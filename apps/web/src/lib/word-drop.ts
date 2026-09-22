/** Rules and helpers for Word Drop: guess a real skill or tool from the taxonomy in six tries, Wordle-style.
 *  Kept free of React so it can be tested on its own, the same way the other games' rule modules are. */

export const MAX_GUESSES = 6;
export const MIN_LEN = 4;
export const MAX_LEN = 8;

export type LetterState = "correct" | "present" | "absent";

/** Picks one real skill or tool name that's a clean single word (letters only, a fair length for a
 *  guessing grid). Multi-word or punctuated names ("Power BI", "C++") are skipped: there is no wordlist
 *  behind this game, so a guess only has to be the right length, not a real word, and that only works
 *  cleanly for single tokens. */
export function pickWord(capabilities: { name: string }[]): string | null {
  const candidates = capabilities.map((c) => c.name.trim()).filter((n) => /^[A-Za-z]+$/.test(n) && n.length >= MIN_LEN && n.length <= MAX_LEN);
  if (candidates.length === 0) return null;
  return candidates[Math.floor(Math.random() * candidates.length)].toUpperCase();
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
  guesses: string[];
  status: "playing" | "won" | "lost";
}

export const newWordState = (target: string): WordState => ({ target, guesses: [], status: "playing" });

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
