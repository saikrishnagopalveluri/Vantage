/** Rules and helpers for the pop quiz. Kept free of React so they can be tested on their own. */

export const LIVES = 3;
export const RIGHT_PER_LEVEL = 4;
export const MAX_LEVEL = 10;
export const BATCH = 8;
export const PREFETCH_WHEN_LEFT = 3;
export const REMEMBER_SEEN = 300; // question ids sent back to the server so they are not asked again

export interface QuizQuestion {
  id: string;
  kind: string;
  prompt: string;
  context: string | null;
  options: string[];
  answer: number;
  explain: string;
  field: string | null;
  level: number;
}

export interface Rank {
  min: number;
  title: string;
}

/** Titles earned by the number of right answers in one game. */
export const RANKS: Rank[] = [
  { min: 0, title: "Intern" },
  { min: 5, title: "Analyst" },
  { min: 10, title: "Associate" },
  { min: 15, title: "Manager" },
  { min: 25, title: "Senior Manager" },
  { min: 35, title: "Director" },
  { min: 50, title: "Partner" },
  { min: 70, title: "Managing Director" },
];

export function rankIndex(correct: number): number {
  let index = 0;
  RANKS.forEach((r, i) => {
    if (correct >= r.min) index = i;
  });
  return index;
}

export const rankFor = (correct: number): Rank => RANKS[rankIndex(correct)];

/** The next title to aim for and how many more right answers it takes, or null at the top. */
export function nextRank(correct: number): { title: string; needed: number } | null {
  const next = RANKS[rankIndex(correct) + 1];
  return next ? { title: next.title, needed: next.min - correct } : null;
}

export const levelFor = (correct: number): number => Math.min(MAX_LEVEL, 1 + Math.floor(correct / RIGHT_PER_LEVEL));

/** Seconds to answer: 22 at the start, two fewer each level, never under 8. */
export const secondsFor = (level: number): number => Math.max(8, 22 - 2 * (level - 1));

/** Base points rise with the level, a quick answer earns a bonus, and a streak multiplies the total (up to double). */
export function pointsFor({ level, secondsLeft, streak }: { level: number; secondsLeft: number; streak: number }): number {
  const base = 100 + 10 * level;
  const speed = Math.round(Math.max(0, secondsLeft) * 5);
  const multiplier = 1 + Math.min(streak, 10) * 0.1;
  return Math.round((base + speed) * multiplier);
}

export interface Answer {
  question: QuizQuestion;
  picked: number | null; // null when time ran out
  right: boolean;
}

export interface Game {
  lives: number;
  score: number;
  correct: number;
  streak: number;
  bestStreak: number;
  level: number;
  answers: Answer[];
}

export const newGame = (): Game => ({ lives: LIVES, score: 0, correct: 0, streak: 0, bestStreak: 0, level: 1, answers: [] });

/** The game after one answer. A right answer scores and may raise the level; a wrong one costs a life and resets the streak. */
export function applyAnswer(game: Game, question: QuizQuestion, picked: number | null, secondsLeft: number): { game: Game; points: number; leveledUp: boolean } {
  const right = picked !== null && picked === question.answer;
  const answers = [...game.answers, { question, picked, right }];
  if (!right) return { game: { ...game, lives: game.lives - 1, streak: 0, answers }, points: 0, leveledUp: false };
  const streak = game.streak + 1;
  const points = pointsFor({ level: game.level, secondsLeft, streak: game.streak });
  const correct = game.correct + 1;
  const level = levelFor(correct);
  return {
    game: { ...game, score: game.score + points, correct, streak, bestStreak: Math.max(game.bestStreak, streak), level, answers },
    points,
    leveledUp: level > game.level,
  };
}

export const isOver = (game: Game): boolean => game.lives <= 0;

export const accuracy = (game: Game): number => (game.answers.length ? Math.round((100 * game.correct) / game.answers.length) : 0);

// ---- best score ----------------------------------------------------------------------------------------------------

const BEST_KEY = "vantage.quiz.best";
export interface Best {
  score: number;
  correct: number;
  bestStreak: number;
}

export function readBest(): Best | null {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as Partial<Best>;
    return typeof v.score === "number" ? { score: v.score, correct: v.correct ?? 0, bestStreak: v.bestStreak ?? 0 } : null;
  } catch {
    return null;
  }
}

/** Saves the game if it beats the stored best. Returns whether it did. */
export function saveIfBest(game: Game): boolean {
  const best = readBest();
  if (best && best.score >= game.score) return false;
  try {
    window.localStorage.setItem(BEST_KEY, JSON.stringify({ score: game.score, correct: game.correct, bestStreak: game.bestStreak }));
  } catch {}
  return game.score > 0;
}

// ---- sharing -------------------------------------------------------------------------------------------------------

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(Number.isFinite(n) ? n : 0)));

export interface Result {
  score: number;
  correct: number;
  bestStreak: number;
  level: number;
  rank: number; // index into RANKS
}

export const resultOf = (game: Game): Result => ({
  score: game.score,
  correct: game.correct,
  bestStreak: game.bestStreak,
  level: game.level,
  rank: rankIndex(game.correct),
});

/** Turn untrusted query values into a result that is safe to draw and print: whole numbers in range, a rank that exists. */
export function parseResult(input: Record<string, string | string[] | undefined>): Result {
  const num = (key: string) => {
    const raw = input[key];
    return Number(Array.isArray(raw) ? raw[0] : raw);
  };
  return {
    score: clamp(num("s"), 0, 999_999),
    correct: clamp(num("c"), 0, 999),
    bestStreak: clamp(num("k"), 0, 999),
    level: clamp(num("l"), 1, MAX_LEVEL),
    rank: clamp(num("t"), 0, RANKS.length - 1),
  };
}

export const resultQuery = (r: Result): string => `s=${r.score}&c=${r.correct}&k=${r.bestStreak}&l=${r.level}&t=${r.rank}`;

export const shareUrl = (origin: string, r: Result): string => `${origin}/quiz/share?${resultQuery(r)}`;

/** A post that reads like a person wrote it. It names no one and shows no profile details. */
export function shareText(r: Result): string {
  const points = r.score.toLocaleString("en-IN");
  return `I scored ${points} on the Vantage pop quiz: ${r.correct} right, a best streak of ${r.bestStreak}, and the title of ${RANKS[r.rank].title}. Think you can beat that?`;
}

export const intents = {
  linkedin: (url: string) => `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
  x: (text: string, url: string) => `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
  whatsapp: (text: string, url: string) => `https://wa.me/?text=${encodeURIComponent(`${text} ${url}`)}`,
};
