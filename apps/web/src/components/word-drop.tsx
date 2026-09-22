"use client";

import { useCallback, useEffect, useId, useReducer, useRef, useState } from "react";
import { api } from "@/lib/api";
import {
  MAX_GUESSES,
  newWordState,
  pickWord,
  readWordBest,
  saveWordIfBest,
  scoreGuess,
  submitGuess,
  type LetterState,
  type WordState,
} from "@/lib/word-drop";
import { CloseIcon } from "./icons";
import { PartnerBadge } from "./partner-badge";
import { Button, cx } from "./ui";

// ---- game state -----------------------------------------------------------------------------------------------------

type Phase = "intro" | "loading" | "playing" | "over" | "error";

interface State {
  phase: Phase;
  word: WordState;
  input: string;
  message: string | null;
  error: string | null;
}

type Action =
  | { type: "start" }
  | { type: "loaded"; target: string }
  | { type: "failed"; message: string }
  | { type: "type"; value: string }
  | { type: "submit" }
  | { type: "clearMessage" };

const initial = (): State => ({ phase: "intro", word: newWordState(""), input: "", message: null, error: null });

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initial(), phase: "loading" };
    case "loaded":
      return { ...state, phase: "playing", word: newWordState(action.target) };
    case "failed":
      return { ...state, phase: "error", error: action.message };
    case "type":
      return state.phase === "playing" ? { ...state, input: action.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, state.word.target.length) } : state;
    case "submit": {
      if (state.phase !== "playing") return state;
      if (state.input.length !== state.word.target.length) {
        return { ...state, message: `Needs to be ${state.word.target.length} letters.` };
      }
      const word = submitGuess(state.word, state.input);
      return { ...state, word, input: "", message: null, phase: word.status === "playing" ? "playing" : "over" };
    }
    case "clearMessage":
      return { ...state, message: null };
  }
}

// ---- pieces -------------------------------------------------------------------------------------------------------------

const TILE_STYLE: Record<LetterState, string> = {
  correct: "border-good bg-good-soft text-ink",
  present: "border-accent bg-accent-soft text-ink",
  absent: "border-line bg-sunken text-muted",
};

function Row({ length, letters, states }: { length: number; letters: string; states?: LetterState[] }) {
  const cells = Array.from({ length }, (_, i) => letters[i] ?? "");
  return (
    <div className="flex justify-center gap-1.5" role={states ? "img" : undefined} aria-label={states ? letters.split("").join(" ") : undefined}>
      {cells.map((ch, i) => (
        <span
          key={i}
          aria-hidden={!states}
          className={cx(
            "flex size-10 items-center justify-center rounded-lg border font-mono text-lg font-semibold uppercase",
            states ? TILE_STYLE[states[i]] : ch ? "border-ink text-ink" : "border-line text-muted",
          )}
        >
          {ch}
        </span>
      ))}
    </div>
  );
}

// ---- the game ---------------------------------------------------------------------------------------------------------

export function WordDrop({ onClose }: { onClose: () => void }) {
  const [state, dispatch] = useReducer(reducer, undefined, initial);
  const [bestAtStart, setBestAtStart] = useState(() => readWordBest());
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const fetching = useRef(false);
  const titleId = useId();
  const { phase, word } = state;

  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  // One real skill or tool, once per round.
  useEffect(() => {
    if (phase !== "loading" || fetching.current) return;
    fetching.current = true;
    const controller = new AbortController();
    api
      .capabilities("", null, undefined, controller.signal, 80, true)
      .then((capabilities) => {
        fetching.current = false;
        const target = pickWord(capabilities);
        if (target) dispatch({ type: "loaded", target });
        else dispatch({ type: "failed", message: "We couldn't find a short enough skill or tool name. Try again in a moment." });
      })
      .catch((e: Error) => {
        fetching.current = false;
        if (e.name !== "AbortError") dispatch({ type: "failed", message: navigator.onLine ? "We couldn't load a word just now." : "You're offline. Connect and try again." });
      });
    return () => controller.abort();
  }, [phase]);

  useEffect(() => {
    if (!state.message) return;
    const id = window.setTimeout(() => dispatch({ type: "clearMessage" }), 1600);
    return () => window.clearTimeout(id);
  }, [state.message]);

  useEffect(() => {
    if (phase !== "over") return;
    saveWordIfBest(word);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    if (phase === "playing" || phase === "over" || phase === "intro" || phase === "error") heading.current?.focus({ preventScroll: true });
    if (phase === "playing") input.current?.focus();
  }, [phase]);

  const start = useCallback(() => {
    setBestAtStart(readWordBest());
    dispatch({ type: "start" });
  }, []);

  const newBest = phase === "over" && word.status === "won" && (bestAtStart === null || word.guesses.length < bestAtStart);

  return (
    <dialog ref={dialog} aria-labelledby={titleId} onCancel={(e) => { e.preventDefault(); onClose(); }} className="m-0 h-dvh max-h-none w-dvw max-w-none overflow-y-auto bg-paper p-0 text-ink">
      <div className="pt-safe px-safe mx-auto flex min-h-dvh w-full max-w-xl flex-col pb-6">
        <header className="flex h-14 items-center gap-2">
          <span className="font-display text-xl">Vantage</span>
          <div className="ml-auto flex items-center">
            {phase === "playing" && (
              <p className="mr-2 text-right leading-tight" aria-live="off">
                <span className="block font-display text-2xl tabular-nums">{word.guesses.length}</span>
                <span className="block font-mono text-xs text-muted">of {MAX_GUESSES}</span>
              </p>
            )}
            <button type="button" onClick={onClose} aria-label="Close Word Drop" className="-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink">
              <CloseIcon width={22} height={22} />
            </button>
          </div>
        </header>

        {phase === "intro" && (
          <div className="rise my-auto py-6">
            <p className="font-mono text-xs text-accent">Word Drop</p>
            <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-2 font-display text-[40px] leading-[1.05] outline-none">
              Guess a real skill or tool.
            </h1>
            <p className="mt-4 text-[17px] leading-relaxed text-muted">
              Six tries. After each guess, a letter turns green in the right spot, amber if it&apos;s in the word but the wrong spot, and grey if it isn&apos;t there. There&apos;s no dictionary behind this: a guess just has to be the right length.
            </p>
            {bestAtStart && (
              <p className="mt-4 text-sm text-muted">
                Fewest guesses so far: <span className="font-semibold text-ink">{bestAtStart}</span>.
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
            <p className="font-display text-2xl text-ink">Picking a word</p>
            <p className="mt-2 text-sm">From the skills and tools in the taxonomy.</p>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="my-auto py-10 text-center">
            <h1 id={titleId} ref={heading} tabIndex={-1} className="font-display text-2xl outline-none">
              We couldn&apos;t start Word Drop
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
          <div className="flex flex-1 flex-col items-center">
            <h2 id={titleId} ref={heading} tabIndex={-1} className="sr-only outline-none">
              Guess the {word.target.length}-letter word
            </h2>
            <div className="mt-6 flex flex-col gap-1.5">
              {Array.from({ length: MAX_GUESSES }, (_, i) => {
                const guess = word.guesses[i];
                if (guess) return <Row key={i} length={word.target.length} letters={guess} states={scoreGuess(guess, word.target)} />;
                if (i === word.guesses.length) return <Row key={i} length={word.target.length} letters={state.input} />;
                return <Row key={i} length={word.target.length} letters="" />;
              })}
            </div>
            <form
              className="mt-6 flex w-full max-w-xs items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                dispatch({ type: "submit" });
              }}
            >
              <label htmlFor="word-guess" className="sr-only">
                Your guess
              </label>
              <input
                id="word-guess"
                ref={input}
                value={state.input}
                onChange={(e) => dispatch({ type: "type", value: e.target.value })}
                maxLength={word.target.length}
                autoComplete="off"
                autoCapitalize="characters"
                spellCheck={false}
                className="min-h-11 flex-1 rounded-xl border border-line bg-surface px-3.5 text-center font-mono text-lg uppercase tracking-widest outline-none focus:border-ink"
              />
              <Button type="submit" variant="primary">
                Guess
              </Button>
            </form>
            <p role="status" aria-live="polite" className="mt-3 min-h-5 text-sm text-accent">
              {state.message}
            </p>
          </div>
        )}

        {phase === "over" && (
          <div className="rise flex flex-col gap-5 py-2">
            <div>
              <p className="font-mono text-xs text-accent">{word.status === "won" ? "Got it" : "So close"}</p>
              <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-1 font-display text-[34px] leading-[1.1] outline-none">
                {word.status === "won" ? `Solved in ${word.guesses.length} ${word.guesses.length === 1 ? "guess" : "guesses"}` : `The word was ${word.target}`}
              </h1>
              {word.status === "won" && (
                <p className="mt-2 text-muted">
                  {newBest ? <span className="rounded bg-accent-soft px-2 py-0.5 text-sm font-semibold text-accent">New best</span> : bestAtStart ? `Your best is ${bestAtStart} ${bestAtStart === 1 ? "guess" : "guesses"}` : ""}
                </p>
              )}
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
