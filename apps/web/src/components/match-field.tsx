"use client";

import { useCallback, useEffect, useId, useReducer, useRef, useState } from "react";
import { api } from "@/lib/api";
import {
  BOARD_SIZE,
  MIN_QUEUE,
  ROUND_SECONDS,
  accuracy,
  matchShareCard,
  newMatchState,
  readMatchBest,
  saveMatchIfBest,
  selectLeft,
  tryMatch,
  type MatchState,
} from "@/lib/match-field";
import { CloseIcon } from "./icons";
import { ShareBar } from "./games/share-bar";
import { PartnerBadge } from "./partner-badge";
import { Button, cx } from "./ui";

// ---- game state -----------------------------------------------------------------------------------------------------

type Phase = "intro" | "loading" | "playing" | "over" | "error";

interface State {
  phase: Phase;
  match: MatchState;
  deadline: number; // performance.now() value when the round ends
  left: number; // seconds left, for display
  lastWrong: { left: string; right: string } | null;
  error: string | null;
}

type Action =
  | { type: "start" }
  | { type: "loaded"; match: MatchState; at: number }
  | { type: "failed"; message: string }
  | { type: "selectLeft"; id: string }
  | { type: "tryMatch"; id: string }
  | { type: "clearWrong" }
  | { type: "tick"; at: number };

const initial = (): State => ({ phase: "intro", match: newMatchState([]), deadline: 0, left: ROUND_SECONDS, lastWrong: null, error: null });

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initial(), phase: "loading" };
    case "loaded":
      if (state.phase !== "loading") return state;
      if (action.match.board.length < Math.min(MIN_QUEUE, BOARD_SIZE)) {
        return { ...state, phase: "error", error: "We couldn't find enough companies with different industries. Try again in a moment." };
      }
      return { ...state, phase: "playing", match: action.match, deadline: action.at + ROUND_SECONDS * 1000, left: ROUND_SECONDS };
    case "failed":
      return { ...state, phase: "error", error: action.message };
    case "selectLeft":
      return state.phase === "playing" ? { ...state, match: selectLeft(state.match, action.id) } : state;
    case "tryMatch": {
      if (state.phase !== "playing") return state;
      const wasSelected = state.match.selectedLeft;
      const { state: match, correct } = tryMatch(state.match, action.id);
      return { ...state, match, lastWrong: !correct && wasSelected ? { left: wasSelected, right: action.id } : null };
    }
    case "clearWrong":
      return { ...state, lastWrong: null };
    case "tick": {
      if (state.phase !== "playing") return state;
      const left = (state.deadline - action.at) / 1000;
      return left <= 0 ? { ...state, phase: "over", left: 0 } : { ...state, left };
    }
  }
}

// ---- the game ---------------------------------------------------------------------------------------------------------

export function MatchField({ onClose }: { onClose: () => void }) {
  const [state, dispatch] = useReducer(reducer, undefined, initial);
  const [leaving, setLeaving] = useState(false);
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

  const requestExit = useCallback(() => {
    if (phase === "playing" && match.correct > 0) setLeaving(true);
    else onClose();
  }, [phase, match.correct, onClose]);

  // A large batch of real companies, once per round — enough to cover a fast 60 seconds without asking again.
  useEffect(() => {
    if (phase !== "loading" || fetching.current) return;
    fetching.current = true;
    const controller = new AbortController();
    api
      .companies("", null, controller.signal, 200, true)
      .then((companies) => {
        fetching.current = false;
        dispatch({ type: "loaded", match: newMatchState(companies), at: performance.now() });
      })
      .catch((e: Error) => {
        fetching.current = false;
        if (e.name !== "AbortError") dispatch({ type: "failed", message: navigator.onLine ? "We couldn't load companies just now." : "You're offline. Connect and try again." });
      });
    return () => controller.abort();
  }, [phase]);

  // One clock for the whole round.
  useEffect(() => {
    if (phase !== "playing") return;
    const id = window.setInterval(() => dispatch({ type: "tick", at: performance.now() }), 100);
    return () => window.clearInterval(id);
  }, [phase]);

  // A wrong pair flashes briefly, then clears on its own.
  useEffect(() => {
    if (!state.lastWrong) return;
    const id = window.setTimeout(() => dispatch({ type: "clearWrong" }), 500);
    return () => window.clearTimeout(id);
  }, [state.lastWrong]);

  // The end of the round: remember the best score.
  useEffect(() => {
    if (phase !== "over") return;
    saveMatchIfBest(match);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    if (phase === "playing" || phase === "over" || phase === "intro" || phase === "error") heading.current?.focus({ preventScroll: true });
  }, [phase]);

  const start = useCallback(() => {
    setBestAtStart(readMatchBest());
    dispatch({ type: "start" });
  }, []);

  const newBest = phase === "over" && match.correct > (bestAtStart?.correct ?? 0);

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
                <span className="block font-display text-2xl tabular-nums">{match.correct}</span>
                <span className="block font-mono text-xs text-muted">matched</span>
              </p>
            )}
            <button type="button" onClick={requestExit} aria-label="Close Match the Field" className="-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink">
              <CloseIcon width={22} height={22} />
            </button>
          </div>
        </header>

        {leaving && (
          <div role="alertdialog" aria-label="Leave Match the Field?" className="raised mb-4 rounded-2xl p-4">
            <p className="font-semibold">Leave Match the Field?</p>
            <p className="mt-1 text-sm text-muted">Your {match.correct} {match.correct === 1 ? "match" : "matches"} so far won&apos;t be saved.</p>
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
            <p className="font-mono text-xs text-accent">Match the Field</p>
            <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-2 font-display text-[40px] leading-[1.05] outline-none">
              How many can you match in a minute?
            </h1>
            <p className="mt-4 text-[17px] leading-relaxed text-muted">
              Tap a company, then tap the industry it belongs to. A wrong pair costs nothing but a moment — the clock never stops, so just keep matching until time runs out.
            </p>
            <ul className="mt-5 grid grid-cols-2 gap-2 text-center text-sm">
              {[[`${ROUND_SECONDS}s`, "on the clock"], ["No limit", "on matches"]].map(([big, small]) => (
                <li key={small} className="raised rounded-xl px-2 py-3">
                  <span className="block font-display text-xl">{big}</span>
                  <span className="text-muted">{small}</span>
                </li>
              ))}
            </ul>
            {bestAtStart && (
              <p className="mt-4 text-sm text-muted">
                Your best so far: <span className="font-semibold text-ink">{bestAtStart.correct}</span> matched.
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
            <p className="font-display text-2xl text-ink">Lining up companies</p>
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
            <div aria-hidden className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-sunken">
              <div
                className={cx("h-full rounded-full transition-[width] duration-100 ease-linear", state.left <= 10 ? "bg-accent" : "bg-ink/70")}
                style={{ width: `${Math.max(0, Math.min(100, (state.left / ROUND_SECONDS) * 100))}%` }}
              />
            </div>
            <div className="mt-3 flex items-center gap-2 text-sm">
              <h2 id={titleId} ref={heading} tabIndex={-1} className="font-display text-[20px] leading-[1.15] outline-none">
                Tap a company, then its industry.
              </h2>
              <span role="timer" className="ml-auto font-mono text-muted tabular-nums" aria-label="Seconds left in the round">
                {Math.ceil(state.left)}s
              </span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <ul aria-label="Companies" className="flex flex-col gap-2">
                {match.leftOrder.map((id) => {
                  const pair = match.board.find((p) => p.id === id)!;
                  const selected = match.selectedLeft === id;
                  const wrong = state.lastWrong?.left === id;
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        aria-pressed={selected}
                        onClick={() => dispatch({ type: "selectLeft", id })}
                        className={cx(
                          "flex min-h-14 w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-[15px] leading-snug transition-colors",
                          selected && "border-ink bg-sunken",
                          wrong && "border-accent bg-accent-soft",
                          !selected && !wrong && "border-line bg-surface hover:border-muted",
                        )}
                      >
                        <span className="flex-1">{pair.left}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <ul aria-label="Industries" className="flex flex-col gap-2">
                {match.rightOrder.map((id) => {
                  const pair = match.board.find((p) => p.id === id)!;
                  const wrong = state.lastWrong?.right === id;
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        onClick={() => dispatch({ type: "tryMatch", id })}
                        className={cx(
                          "flex min-h-14 w-full items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-[15px] leading-snug transition-colors",
                          wrong && "border-accent bg-accent-soft",
                          !wrong && "border-line bg-surface hover:border-muted",
                        )}
                      >
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
              <p className="font-mono text-xs text-accent">Time&apos;s up</p>
              <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-1 font-display text-[34px] leading-[1.1] outline-none">
                {match.correct} matched in {ROUND_SECONDS} seconds
              </h1>
              <p className="mt-2 text-muted">
                {accuracy(match)}% accuracy
                {newBest ? <span className="ml-2 rounded bg-accent-soft px-2 py-0.5 text-sm font-semibold text-accent">New best</span> : bestAtStart ? `, your best is ${bestAtStart.correct}` : ""}
              </p>
            </div>
            <ShareBar
              card={matchShareCard(match)}
              fileName="vantage-match-the-field.png"
              shareTitle="My Vantage Match the Field score"
              shareText={`I matched ${match.correct} ${match.correct === 1 ? "company" : "companies"} to their industry in ${ROUND_SECONDS} seconds on Vantage (${accuracy(match)}% accuracy). Think you can beat that?`}
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
