/** Rules and helpers for Match the Field: tap a company, then tap the industry it belongs to, as many
 *  times as you can in 60 seconds. No lives — a wrong pick costs nothing but a moment, and doesn't
 *  interrupt the clock. Kept free of React so it can be tested on its own, the same way quiz.ts and
 *  speed-round.ts are. */

import type { ShareCard } from "./share";

export const ROUND_SECONDS = 60;
export const BOARD_SIZE = 5; // pairs visible at once
export const MIN_QUEUE = 4; // if the starting pool has fewer distinct industries than this, ask for a fresh batch

export interface MatchPair {
  id: string; // the company id; also doubles as the pair id
  left: string; // the company name
  right: string; // its industry name
}

export interface MatchState {
  board: MatchPair[]; // the pairs currently on screen, up to BOARD_SIZE
  leftOrder: string[]; // pair ids, left column order
  rightOrder: string[]; // pair ids, right column order (shuffled separately, so it's a real puzzle)
  queue: MatchPair[]; // pairs not yet shown; drawn from as the board is solved
  selectedLeft: string | null;
  correct: number; // pairs solved so far this round
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

/** Every company with an industry, one pair each, shuffled. Industries can repeat across the queue —
 *  only the board itself (what's on screen at once) needs one company per industry, so each visible
 *  match has exactly one right answer. */
export function buildQueue(companies: { id: string; name: string; industry: { name: string } | null }[]): MatchPair[] {
  return shuffled(companies.filter((c) => c.industry).map((c) => ({ id: c.id, left: c.name, right: c.industry!.name })));
}

/** Draws from the queue until the board holds `size` pairs with distinct industries (or the queue runs
 *  dry). A pair whose industry is already on the board is skipped, not discarded — it goes to the back
 *  of the queue, since it will very likely fit once that industry clears off the board. */
export function fillBoard(board: MatchPair[], queue: MatchPair[], size: number): { board: MatchPair[]; queue: MatchPair[] } {
  const nextBoard = [...board];
  const rest: MatchPair[] = [];
  let i = 0;
  while (nextBoard.length < size && i < queue.length) {
    const candidate = queue[i];
    i++;
    if (nextBoard.some((p) => p.right === candidate.right)) rest.push(candidate);
    else nextBoard.push(candidate);
  }
  return { board: nextBoard, queue: [...rest, ...queue.slice(i)] };
}

export function newMatchState(companies: { id: string; name: string; industry: { name: string } | null }[]): MatchState {
  const { board, queue } = fillBoard([], buildQueue(companies), BOARD_SIZE);
  const ids = board.map((p) => p.id);
  return { board, leftOrder: shuffled(ids), rightOrder: shuffled(ids), queue, selectedLeft: null, correct: 0, mistakes: 0 };
}

/** Tapping a company selects it, or clears the selection if it's tapped again. */
export function selectLeft(state: MatchState, id: string): MatchState {
  return { ...state, selectedLeft: state.selectedLeft === id ? null : id };
}

/** Tapping an industry with a company selected checks the pair. A right answer clears that pair off
 *  the board and slides in a replacement from the queue; a wrong one just clears the selection. Either
 *  way the clock keeps running — there's nothing to lose but a moment. */
export function tryMatch(state: MatchState, rightId: string): { state: MatchState; correct: boolean } {
  if (!state.selectedLeft) return { state, correct: false };
  const correct = state.selectedLeft === rightId;
  if (!correct) return { state: { ...state, selectedLeft: null, mistakes: state.mistakes + 1 }, correct: false };

  const board = state.board.filter((p) => p.id !== rightId);
  const { board: refilled, queue } = fillBoard(board, state.queue, BOARD_SIZE);
  const added = refilled.filter((p) => !board.includes(p)).map((p) => p.id);
  return {
    state: {
      ...state,
      board: refilled,
      leftOrder: [...state.leftOrder.filter((id) => id !== rightId), ...added],
      rightOrder: [...state.rightOrder.filter((id) => id !== rightId), ...shuffled(added)],
      queue,
      selectedLeft: null,
      correct: state.correct + 1,
    },
    correct: true,
  };
}

export const accuracy = (state: MatchState): number => {
  const attempts = state.correct + state.mistakes;
  return attempts ? Math.round((100 * state.correct) / attempts) : 0;
};

// ---- best score ------------------------------------------------------------------------------------------------------

const BEST_KEY = "vantage.matchfield.best";

export interface MatchBest {
  correct: number;
}

export function readMatchBest(): MatchBest | null {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as Partial<MatchBest>;
    return typeof v.correct === "number" ? { correct: v.correct } : null;
  } catch {
    return null;
  }
}

/** Saves the round if it beats the stored best (more correct matches wins). Returns whether it did. */
export function saveMatchIfBest(state: MatchState): boolean {
  const best = readMatchBest();
  if (best && best.correct >= state.correct) return false;
  try {
    window.localStorage.setItem(BEST_KEY, JSON.stringify({ correct: state.correct }));
  } catch {}
  return state.correct > 0;
}

// ---- share card ------------------------------------------------------------------------------------------------------

export function matchShareCard(state: MatchState): ShareCard {
  return {
    game: "MATCH THE FIELD",
    headlineLabel: "matched",
    headline: String(state.correct),
    accentLabel: "accuracy",
    accent: `${accuracy(state)}%`,
    stats: [{ value: `${ROUND_SECONDS}s`, label: "on the clock" }],
    footer: "Think you can beat it?",
  };
}
