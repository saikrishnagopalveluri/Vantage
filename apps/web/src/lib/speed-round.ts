/** Rules and helpers for Speed Round: one minute, as many right answers as you can get, no lives and no levels.
 *  Kept free of React so it can be tested on its own, the same way quiz.ts is. */

import type { QuizQuestion } from "./quiz";

export const ROUND_SECONDS = 60;
export const LEVEL = 3; // a fixed, moderate difficulty for the whole round: this game is a race, not a climb
export const BATCH = 10;
export const PREFETCH_WHEN_LEFT = 3;
export const REMEMBER_SEEN = 200;

export interface SpeedAnswer {
  question: QuizQuestion;
  picked: number;
  right: boolean;
}

export interface SpeedGame {
  correct: number;
  answers: SpeedAnswer[];
}

export const newSpeedGame = (): SpeedGame => ({ correct: 0, answers: [] });

/** The game after one pick. Every pick counts, right or wrong; there is no life to lose. */
export function applySpeedAnswer(game: SpeedGame, question: QuizQuestion, picked: number): { game: SpeedGame; right: boolean } {
  const right = picked === question.answer;
  return {
    game: { correct: game.correct + (right ? 1 : 0), answers: [...game.answers, { question, picked, right }] },
    right,
  };
}

export const accuracy = (game: SpeedGame): number => (game.answers.length ? Math.round((100 * game.correct) / game.answers.length) : 0);

// ---- best score ------------------------------------------------------------------------------------------------------

const BEST_KEY = "vantage.speedround.best";

export interface SpeedBest {
  correct: number;
  answered: number;
}

export function readSpeedBest(): SpeedBest | null {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as Partial<SpeedBest>;
    return typeof v.correct === "number" ? { correct: v.correct, answered: v.answered ?? v.correct } : null;
  } catch {
    return null;
  }
}

/** Saves the round if it beats the stored best (more right answers wins). Returns whether it did. */
export function saveSpeedIfBest(game: SpeedGame): boolean {
  const best = readSpeedBest();
  if (best && best.correct >= game.correct) return false;
  try {
    window.localStorage.setItem(BEST_KEY, JSON.stringify({ correct: game.correct, answered: game.answers.length }));
  } catch {}
  return game.correct > 0;
}
