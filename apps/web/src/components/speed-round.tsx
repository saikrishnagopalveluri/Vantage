"use client";

import { useCallback, useEffect, useId, useReducer, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { QuizQuestion } from "@/lib/quiz";
import {
  BATCH,
  LEVEL,
  PREFETCH_WHEN_LEFT,
  REMEMBER_SEEN,
  ROUND_SECONDS,
  accuracy,
  applySpeedAnswer,
  newSpeedGame,
  readSpeedBest,
  saveSpeedIfBest,
  speedShareCard,
  type SpeedGame,
} from "@/lib/speed-round";
import { CheckIcon, CloseIcon } from "./icons";
import { ShareBar } from "./games/share-bar";
import { PartnerBadge } from "./partner-badge";
import { Button, Chip, cx } from "./ui";

// ---- game state -----------------------------------------------------------------------------------------------------

type Phase = "intro" | "loading" | "playing" | "over" | "error";

interface State {
  phase: Phase;
  game: SpeedGame;
  queue: QuizQuestion[];
  seen: string[];
  index: number;
  picked: number | null; // the option just chosen, shown briefly before the next question
  deadline: number; // performance.now() value when the round ends
  left: number; // seconds left, for display
  error: string | null;
  nonce: number; // bumped whenever a batch arrives, so the loader looks again
}

type Action =
  | { type: "start" }
  | { type: "loaded"; questions: QuizQuestion[]; at: number }
  | { type: "failed"; message: string }
  | { type: "tick"; at: number }
  | { type: "answer"; pick: number }
  | { type: "advance" };

const initial = (): State => ({
  phase: "intro", game: newSpeedGame(), queue: [], seen: [], index: 0, picked: null, deadline: 0, left: ROUND_SECONDS, error: null, nonce: 0,
});

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initial(), phase: "loading" };
    case "loaded": {
      const fresh = action.questions.filter((q) => !state.seen.includes(q.id));
      if (fresh.length === 0 && state.queue.length <= state.index) {
        return state.phase === "over" ? state : { ...state, phase: "error", error: "We couldn't find more questions. Try again in a moment." };
      }
      const queue = [...state.queue, ...fresh];
      const seen = [...state.seen, ...fresh.map((q) => q.id)].slice(-REMEMBER_SEEN * 2);
      if (state.phase === "loading") {
        return { ...state, queue, seen, nonce: state.nonce + 1, phase: "playing", deadline: action.at + ROUND_SECONDS * 1000, left: ROUND_SECONDS };
      }
      return { ...state, queue, seen, nonce: state.nonce + 1 };
    }
    case "failed":
      return state.phase === "over" ? state : { ...state, phase: "error", error: action.message };
    case "tick": {
      if (state.phase !== "playing") return state;
      const left = (state.deadline - action.at) / 1000;
      return left <= 0 ? { ...state, phase: "over", left: 0 } : { ...state, left };
    }
    case "answer": {
      if (state.phase !== "playing" || state.picked !== null) return state;
      const question = state.queue[state.index];
      if (!question) return state;
      const { game } = applySpeedAnswer(state.game, question, action.pick);
      return { ...state, game, picked: action.pick };
    }
    case "advance": {
      if (state.phase !== "playing" || state.picked === null) return state;
      return { ...state, index: state.index + 1, picked: null };
    }
  }
}

// ---- the game ---------------------------------------------------------------------------------------------------------

export function SpeedRound({ userId, onClose }: { userId: string; onClose: () => void }) {
  const [state, dispatch] = useReducer(reducer, undefined, initial);
  const [leaving, setLeaving] = useState(false);
  const [bestAtStart, setBestAtStart] = useState(() => readSpeedBest());
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const fetching = useRef(false);
  const titleId = useId();
  const { phase, game, queue, index, picked } = state;
  const question = queue[index];

  // A native modal dialog gives us focus trapping, Escape handling and an inert page behind it.
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  const requestExit = useCallback(() => {
    if (phase === "playing" && game.answers.length > 0) setLeaving(true);
    else onClose();
  }, [phase, game.answers.length, onClose]);

  // Keep questions coming: ask for more when the queue runs low, and while waiting for the first ones.
  const wanted = phase === "loading" || (phase === "playing" && queue.length - index <= PREFETCH_WHEN_LEFT);
  useEffect(() => {
    if (!wanted || fetching.current) return;
    fetching.current = true;
    const controller = new AbortController();
    api
      .quiz(userId, LEVEL, state.seen.slice(-REMEMBER_SEEN), BATCH, controller.signal)
      .then((batch) => {
        fetching.current = false;
        dispatch({ type: "loaded", questions: batch.questions, at: performance.now() });
      })
      .catch((e: Error) => {
        fetching.current = false;
        if (e.name !== "AbortError") dispatch({ type: "failed", message: navigator.onLine ? "We couldn't load questions just now." : "You're offline. Connect and try again." });
      });
    return () => controller.abort();
    // The seen list is read when the request starts; it changing alone shouldn't cancel one already in flight.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, userId, queue.length, state.nonce]);

  // One clock for the whole round, not one per question.
  useEffect(() => {
    if (phase !== "playing") return;
    const id = window.setInterval(() => dispatch({ type: "tick", at: performance.now() }), 100);
    return () => window.clearInterval(id);
  }, [phase]);

  // A pick shows briefly, right or wrong, then the next question comes on its own. No pausing to read an explanation.
  useEffect(() => {
    if (picked === null || phase !== "playing") return;
    const id = window.setTimeout(() => dispatch({ type: "advance" }), 450);
    return () => window.clearTimeout(id);
  }, [picked, phase]);

  // The end of the round: remember the best score.
  useEffect(() => {
    if (phase !== "over") return;
    saveSpeedIfBest(game);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // Where the keyboard and screen reader should be.
  useEffect(() => {
    if (phase === "playing" || phase === "over" || phase === "intro" || phase === "error") heading.current?.focus({ preventScroll: true });
  }, [phase, index]);

  // Answer with 1 to 4 or A to D.
  useEffect(() => {
    if (phase !== "playing" || !question || picked !== null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const i = "1234".indexOf(e.key) >= 0 ? "1234".indexOf(e.key) : "abcd".indexOf(e.key.toLowerCase());
      if (i >= 0 && i < question.options.length) dispatch({ type: "answer", pick: i });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, question, picked]);

  const start = () => {
    setBestAtStart(readSpeedBest()); // a round just finished may have set a new best
    dispatch({ type: "start" });
  };

  const newBest = phase === "over" && game.correct > (bestAtStart?.correct ?? 0);

  return (
    <dialog
      ref={dialog}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        requestExit();
      }}
      className="m-0 h-dvh max-h-none w-dvw max-w-none overflow-y-auto bg-paper p-0 text-ink"
    >
      <div className="pt-safe px-safe mx-auto flex min-h-dvh w-full max-w-xl flex-col pb-6">
        <header className="flex h-14 items-center gap-2">
          <span className="font-display text-xl">Vantage</span>
          <div className="ml-auto flex items-center">
            {phase === "playing" && (
              <p className="mr-2 text-right leading-tight" aria-live="off">
                <span className="block font-display text-2xl tabular-nums">{game.correct}</span>
                <span className="block font-mono text-xs text-muted">right</span>
              </p>
            )}
            <button type="button" onClick={requestExit} aria-label="Close Speed Round" className="-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink">
              <CloseIcon width={22} height={22} />
            </button>
          </div>
        </header>

        {leaving && (
          <div role="alertdialog" aria-label="Leave Speed Round?" className="raised mb-4 rounded-2xl p-4">
            <p className="font-semibold">Leave Speed Round?</p>
            <p className="mt-1 text-sm text-muted">Your {game.correct} right {game.correct === 1 ? "answer" : "answers"} so far won&apos;t be saved.</p>
            <div className="mt-3 flex gap-2">
              <Button variant="primary" onClick={() => setLeaving(false)}>
                Keep playing
              </Button>
              <Button onClick={onClose}>Leave</Button>
            </div>
          </div>
        )}

        {phase === "intro" && (
          <div className="rise my-auto py-6">
            <p className="font-mono text-xs text-accent">Speed Round</p>
            <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-2 font-display text-[40px] leading-[1.05] outline-none">
              How many can you get in a minute?
            </h1>
            <p className="mt-4 text-[17px] leading-relaxed text-muted">
              One clock for the whole round, not one per question. Every answer, right or wrong, moves straight to the next one. No lives to lose, just a minute to see how far you get.
            </p>
            <ul className="mt-5 grid grid-cols-2 gap-2 text-center text-sm">
              {[[`${ROUND_SECONDS}s`, "on the clock"], ["No limit", "on questions"]].map(([big, small]) => (
                <li key={small} className="raised rounded-xl px-2 py-3">
                  <span className="block font-display text-xl">{big}</span>
                  <span className="text-muted">{small}</span>
                </li>
              ))}
            </ul>
            {bestAtStart && (
              <p className="mt-4 text-sm text-muted">
                Your best so far: <span className="font-semibold text-ink">{bestAtStart.correct}</span> right.
              </p>
            )}
            <Button variant="primary" onClick={start} className="mt-6 w-full">
              Start
            </Button>
            <p className="mt-3 text-center text-sm text-muted">Tip: press 1 to 4 to answer.</p>
            <PartnerBadge size="sm" className="mt-6 justify-center border-t border-line pt-4" />
          </div>
        )}

        {phase === "loading" && (
          <div role="status" className="my-auto py-10 text-center text-muted">
            <p className="font-display text-2xl text-ink">{game.answers.length === 0 ? "Getting your questions ready" : "One moment"}</p>
            <p className="mt-2 text-sm">Picking ones you haven&apos;t seen yet.</p>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="my-auto py-10 text-center">
            <h1 id={titleId} ref={heading} tabIndex={-1} className="font-display text-2xl outline-none">
              We couldn&apos;t start Speed Round
            </h1>
            <p className="mt-2 text-muted">{state.error}</p>
            <div className="mt-5 flex justify-center gap-2">
              <Button variant="primary" onClick={start}>
                Try again
              </Button>
              <Button onClick={onClose}>Close</Button>
            </div>
          </div>
        )}

        {phase === "playing" && question && (
          <div className="flex flex-1 flex-col">
            <div aria-hidden className="h-1.5 w-full overflow-hidden rounded-full bg-sunken">
              <div
                className={cx("h-full rounded-full transition-[width] duration-100 ease-linear", state.left <= 10 ? "bg-accent" : "bg-ink/70")}
                style={{ width: `${Math.max(0, Math.min(100, (state.left / ROUND_SECONDS) * 100))}%` }}
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              {question.field && <Chip>{question.field}</Chip>}
              <span role="timer" className="ml-auto font-mono text-muted tabular-nums" aria-label="Seconds left in the round">
                {Math.ceil(state.left)}s
              </span>
            </div>

            <h2 id={titleId} ref={heading} tabIndex={-1} className="mt-5 font-display text-[28px] leading-[1.15] outline-none md:text-[32px]">
              {question.prompt}
            </h2>
            {question.context && <blockquote className="mt-4 font-display text-[19px] italic leading-snug">&ldquo;{question.context}&rdquo;</blockquote>}

            <div role="group" aria-labelledby={titleId} className="mt-6 grid gap-2.5">
              {question.options.map((option, i) => {
                const revealed = picked !== null;
                const isRight = revealed && i === question.answer;
                const isWrong = revealed && i === picked && i !== question.answer;
                return (
                  <button
                    key={`${question.id}-${i}`}
                    type="button"
                    disabled={revealed}
                    onClick={() => dispatch({ type: "answer", pick: i })}
                    className={cx(
                      "flex min-h-14 w-full items-center gap-3 rounded-xl border px-3.5 py-2.5 text-left text-[16px] leading-snug transition-colors disabled:cursor-default",
                      !revealed && "border-line bg-surface hover:border-muted",
                      isRight && "border-good bg-good-soft text-ink",
                      isWrong && "border-accent bg-accent-soft text-ink",
                      revealed && !isRight && !isWrong && "border-line bg-surface opacity-60",
                    )}
                  >
                    <span
                      className={cx(
                        "flex size-8 shrink-0 items-center justify-center rounded-lg border font-mono text-sm",
                        isRight ? "border-good text-good" : isWrong ? "border-accent text-accent" : "border-line text-muted",
                      )}
                    >
                      {isRight ? <CheckIcon width={16} height={16} /> : isWrong ? <CloseIcon width={16} height={16} /> : "ABCD"[i]}
                    </span>
                    <span className="flex-1">{option}</span>
                    {isRight && <span className="sr-only">Correct answer</span>}
                    {isWrong && <span className="sr-only">Your answer, not correct</span>}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {phase === "over" && (
          <div className="rise flex flex-col gap-5 py-2">
            <div>
              <p className="font-mono text-xs text-accent">Time&apos;s up</p>
              <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-1 font-display text-[34px] leading-[1.1] outline-none">
                {game.correct} right in {ROUND_SECONDS} seconds
              </h1>
              <p className="mt-2 text-muted">
                {game.answers.length} answered, {accuracy(game)}% accuracy
                {newBest ? <span className="ml-2 rounded bg-accent-soft px-2 py-0.5 text-sm font-semibold text-accent">New best</span> : bestAtStart ? `, your best is ${bestAtStart.correct}` : ""}
              </p>
            </div>
            <ShareBar
              card={speedShareCard(game)}
              fileName="vantage-speed-round.png"
              shareTitle="My Vantage Speed Round score"
              shareText={`I got ${game.correct} right in ${ROUND_SECONDS} seconds on the Vantage Speed Round (${accuracy(game)}% accuracy). Think you can beat that?`}
              url={typeof window === "undefined" ? "" : `${window.location.origin}/games`}
            />
            <div className="flex gap-2">
              <Button variant="primary" onClick={start}>
                Play again
              </Button>
              <Button onClick={onClose}>Back to Games</Button>
            </div>
            <PartnerBadge size="sm" className="border-t border-line pt-4" />
          </div>
        )}
      </div>
    </dialog>
  );
}
