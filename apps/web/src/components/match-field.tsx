"use client";

import { useCallback, useEffect, useId, useReducer, useRef, useState } from "react";
import { api } from "@/lib/api";
import {
  MIN_PAIRS,
  isSolved,
  newMatchState,
  pickPairs,
  readMatchBest,
  saveMatchIfBest,
  selectLeft,
  tryMatch,
  type MatchPair,
  type MatchState,
} from "@/lib/match-field";
import { CheckIcon, CloseIcon } from "./icons";
import { PartnerBadge } from "./partner-badge";
import { Button, cx } from "./ui";

// ---- game state -----------------------------------------------------------------------------------------------------

type Phase = "intro" | "loading" | "playing" | "over" | "error";

interface State {
  phase: Phase;
  match: MatchState;
  startedAt: number;
  elapsed: number;
  lastWrong: { left: string; right: string } | null;
  error: string | null;
}

type Action =
  | { type: "start" }
  | { type: "loaded"; pairs: MatchPair[]; at: number }
  | { type: "failed"; message: string }
  | { type: "selectLeft"; id: string }
  | { type: "tryMatch"; id: string; at: number }
  | { type: "clearWrong" }
  | { type: "tick"; at: number };

const initial = (): State => ({ phase: "intro", match: newMatchState([]), startedAt: 0, elapsed: 0, lastWrong: null, error: null });

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initial(), phase: "loading" };
    case "loaded": {
      if (action.pairs.length < MIN_PAIRS) {
        return { ...state, phase: "error", error: "We couldn't find enough companies with different industries. Try again in a moment." };
      }
      return { ...state, phase: "playing", match: newMatchState(action.pairs), startedAt: action.at, elapsed: 0 };
    }
    case "failed":
      return { ...state, phase: "error", error: action.message };
    case "selectLeft":
      return state.phase === "playing" ? { ...state, match: selectLeft(state.match, action.id) } : state;
    case "tryMatch": {
      if (state.phase !== "playing") return state;
      const wasSelected = state.match.selectedLeft;
      const { state: match, correct } = tryMatch(state.match, action.id);
      if (!correct) return { ...state, match, lastWrong: wasSelected ? { left: wasSelected, right: action.id } : null };
      const solved = isSolved(match);
      return solved ? { ...state, match, phase: "over", elapsed: (action.at - state.startedAt) / 1000 } : { ...state, match };
    }
    case "clearWrong":
      return { ...state, lastWrong: null };
    case "tick":
      return state.phase === "playing" ? { ...state, elapsed: (action.at - state.startedAt) / 1000 } : state;
  }
}

// ---- the game ---------------------------------------------------------------------------------------------------------

export function MatchField({ onClose }: { onClose: () => void }) {
  const [state, dispatch] = useReducer(reducer, undefined, initial);
  const [bestAtStart, setBestAtStart] = useState(() => readMatchBest());
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const fetching = useRef(false);
  const titleId = useId();
  const { phase, match } = state;

  // A native modal dialog gives us focus trapping, Escape handling and an inert page behind it.
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  // A fresh batch of real companies, once per round.
  useEffect(() => {
    if (phase !== "loading" || fetching.current) return;
    fetching.current = true;
    const controller = new AbortController();
    api
      .companies("", null, controller.signal, 40, true)
      .then((companies) => {
        fetching.current = false;
        dispatch({ type: "loaded", pairs: pickPairs(companies), at: performance.now() });
      })
      .catch((e: Error) => {
        fetching.current = false;
        if (e.name !== "AbortError") dispatch({ type: "failed", message: navigator.onLine ? "We couldn't load companies just now." : "You're offline. Connect and try again." });
      });
    return () => controller.abort();
  }, [phase]);

  // A stopwatch, not a countdown: it only ever shows how long the round has taken so far.
  useEffect(() => {
    if (phase !== "playing") return;
    const id = window.setInterval(() => dispatch({ type: "tick", at: performance.now() }), 200);
    return () => window.clearInterval(id);
  }, [phase]);

  // A wrong pair flashes briefly, then clears on its own.
  useEffect(() => {
    if (!state.lastWrong) return;
    const id = window.setTimeout(() => dispatch({ type: "clearWrong" }), 500);
    return () => window.clearTimeout(id);
  }, [state.lastWrong]);

  // The end of the round: remember the best time.
  useEffect(() => {
    if (phase !== "over") return;
    saveMatchIfBest(state.elapsed, match.mistakes);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    if (phase === "playing" || phase === "over" || phase === "intro" || phase === "error") heading.current?.focus({ preventScroll: true });
  }, [phase]);

  const start = useCallback(() => {
    setBestAtStart(readMatchBest());
    dispatch({ type: "start" });
  }, []);

  const newBest = phase === "over" && (!bestAtStart || state.elapsed < bestAtStart.seconds);

  return (
    <dialog ref={dialog} aria-labelledby={titleId} onCancel={(e) => { e.preventDefault(); onClose(); }} className="m-0 h-dvh max-h-none w-dvw max-w-none overflow-y-auto bg-paper p-0 text-ink">
      <div className="pt-safe px-safe mx-auto flex min-h-dvh w-full max-w-xl flex-col pb-6">
        <header className="flex h-14 items-center gap-2">
          <span className="font-display text-xl">Vantage</span>
          <div className="ml-auto flex items-center">
            {phase === "playing" && (
              <p className="mr-2 text-right leading-tight" aria-live="off">
                <span className="block font-display text-2xl tabular-nums">{Math.floor(state.elapsed)}s</span>
                <span className="block font-mono text-xs text-muted">{match.matched.size} of {match.pairs.length}</span>
              </p>
            )}
            <button type="button" onClick={onClose} aria-label="Close Match the Field" className="-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink">
              <CloseIcon width={22} height={22} />
            </button>
          </div>
        </header>

        {phase === "intro" && (
          <div className="rise my-auto py-6">
            <p className="font-mono text-xs text-accent">Match the Field</p>
            <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-2 font-display text-[40px] leading-[1.05] outline-none">
              Which industry is each company in?
            </h1>
            <p className="mt-4 text-[17px] leading-relaxed text-muted">
              Tap a company, then tap the industry it belongs to. No lives, no rush, just real companies from the taxonomy. A wrong pair costs nothing but a moment.
            </p>
            {bestAtStart && (
              <p className="mt-4 text-sm text-muted">
                Your best so far: <span className="font-semibold text-ink">{Math.round(bestAtStart.seconds)}s</span>.
              </p>
            )}
            <Button variant="primary" onClick={start} className="mt-6 w-full">
              Start
            </Button>
            <PartnerBadge size="sm" className="mt-6 justify-center border-t border-line pt-4" />
          </div>
        )}

        {phase === "loading" && (
          <div role="status" className="my-auto py-10 text-center text-muted">
            <p className="font-display text-2xl text-ink">Picking five companies</p>
            <p className="mt-2 text-sm">From the same taxonomy the feed uses.</p>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="my-auto py-10 text-center">
            <h1 id={titleId} ref={heading} tabIndex={-1} className="font-display text-2xl outline-none">
              We couldn&apos;t start Match the Field
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

        {phase === "playing" && (
          <div className="flex flex-1 flex-col">
            <h2 id={titleId} ref={heading} tabIndex={-1} className="mt-5 font-display text-[26px] leading-[1.15] outline-none">
              Tap a company, then its industry.
            </h2>
            <div className="mt-6 grid grid-cols-2 gap-3">
              <ul aria-label="Companies" className="flex flex-col gap-2">
                {match.leftOrder.map((id) => {
                  const pair = match.pairs.find((p) => p.id === id)!;
                  const done = match.matched.has(id);
                  const selected = match.selectedLeft === id;
                  const wrong = state.lastWrong?.left === id;
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        disabled={done}
                        aria-pressed={selected}
                        onClick={() => dispatch({ type: "selectLeft", id })}
                        className={cx(
                          "flex min-h-14 w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-[15px] leading-snug transition-colors disabled:cursor-default",
                          done && "border-good bg-good-soft text-ink",
                          !done && selected && "border-ink bg-sunken",
                          !done && wrong && "border-accent bg-accent-soft",
                          !done && !selected && !wrong && "border-line bg-surface hover:border-muted",
                        )}
                      >
                        {done && <CheckIcon width={16} height={16} className="shrink-0 text-good" />}
                        <span className="flex-1">{pair.left}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <ul aria-label="Industries" className="flex flex-col gap-2">
                {match.rightOrder.map((id) => {
                  const pair = match.pairs.find((p) => p.id === id)!;
                  const done = match.matched.has(id);
                  const wrong = state.lastWrong?.right === id;
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        disabled={done}
                        onClick={() => dispatch({ type: "tryMatch", id, at: performance.now() })}
                        className={cx(
                          "flex min-h-14 w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-[15px] leading-snug transition-colors disabled:cursor-default",
                          done && "border-good bg-good-soft text-ink",
                          !done && wrong && "border-accent bg-accent-soft",
                          !done && !wrong && "border-line bg-surface hover:border-muted",
                        )}
                      >
                        {done && <CheckIcon width={16} height={16} className="shrink-0 text-good" />}
                        <span className="flex-1">{pair.right}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
            <p role="status" aria-live="polite" className="sr-only">
              {state.lastWrong ? "Not quite. Try another pair." : ""}
            </p>
          </div>
        )}

        {phase === "over" && (
          <div className="rise flex flex-col gap-5 py-2">
            <div>
              <p className="font-mono text-xs text-accent">Solved</p>
              <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-1 font-display text-[34px] leading-[1.1] outline-none">
                All five in {Math.round(state.elapsed)}s
              </h1>
              <p className="mt-2 text-muted">
                {match.mistakes === 0 ? "No wrong guesses." : `${match.mistakes} wrong ${match.mistakes === 1 ? "guess" : "guesses"}.`}
                {newBest ? <span className="ml-2 rounded bg-accent-soft px-2 py-0.5 text-sm font-semibold text-accent">New best</span> : bestAtStart ? `, your best is ${Math.round(bestAtStart.seconds)}s` : ""}
              </p>
            </div>
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
