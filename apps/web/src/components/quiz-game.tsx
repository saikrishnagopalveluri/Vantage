"use client";

import { useCallback, useEffect, useId, useReducer, useRef, useState } from "react";
import { api } from "@/lib/api";
import {
  BATCH,
  LIVES,
  PREFETCH_WHEN_LEFT,
  REMEMBER_SEEN,
  accuracy,
  applyAnswer,
  intents,
  isOver,
  newGame,
  nextRank,
  rankFor,
  readBest,
  resultOf,
  saveIfBest,
  secondsFor,
  shareText,
  shareUrl,
  type Game,
  type QuizQuestion,
} from "@/lib/quiz";
import { buzz, setSound, sounds, useSound } from "@/lib/quiz-sound";
import { drawShareCard } from "@/lib/share-card";
import { CheckIcon, CloseIcon, CopyIcon, DownloadIcon, HeartIcon, MuteIcon, ShareIcon, SpeakerIcon } from "./icons";
import { PartnerBadge } from "./partner-badge";
import { Button, Chip, cx } from "./ui";

// ---- game state ---------------------------------------------------------------------------------------------------------

type Phase = "intro" | "loading" | "playing" | "revealed" | "over" | "error";

interface State {
  phase: Phase;
  game: Game;
  queue: QuizQuestion[];
  seen: string[];
  index: number;
  picked: number | null;
  deadline: number; // performance.now() value when time runs out
  left: number; // seconds left, for display
  points: number;
  leveledUp: boolean;
  error: string | null;
  nonce: number; // bumped whenever a batch arrives, so the loader looks again
}

type Action =
  | { type: "start" }
  | { type: "loaded"; questions: QuizQuestion[]; at: number; level: number }
  | { type: "failed"; message: string }
  | { type: "tick"; at: number }
  | { type: "answer"; pick: number | null; at: number }
  | { type: "next"; at: number };

const initial = (): State => ({
  phase: "intro", game: newGame(), queue: [], seen: [], index: 0, picked: null, deadline: 0, left: secondsFor(1), points: 0, leveledUp: false, error: null, nonce: 0,
});

function settle(state: State, pick: number | null, at: number): State {
  const question = state.queue[state.index];
  if (state.phase !== "playing" || !question) return state;
  const secondsLeft = Math.max(0, (state.deadline - at) / 1000);
  const { game, points, leveledUp } = applyAnswer(state.game, question, pick, secondsLeft);
  // Questions already fetched were picked for the old level, so on a level-up they are dropped and new ones are asked for.
  const queue = leveledUp ? state.queue.slice(0, state.index + 1) : state.queue;
  return { ...state, phase: "revealed", game, queue, picked: pick, points, leveledUp, left: secondsLeft };
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initial(), phase: "loading" };
    case "loaded": {
      if (action.level < state.game.level) return { ...state, nonce: state.nonce + 1 }; // asked for before a level-up: ask again
      const fresh = action.questions.filter((q) => !state.seen.includes(q.id));
      if (fresh.length === 0 && state.queue.length <= state.index) return { ...state, phase: "error", error: "We couldn't find more questions. Try again in a moment." };
      const queue = [...state.queue, ...fresh];
      const seen = [...state.seen, ...fresh.map((q) => q.id)].slice(-REMEMBER_SEEN * 2);
      if (state.phase === "loading") {
        return { ...state, queue, seen, nonce: state.nonce + 1, phase: "playing", deadline: action.at + secondsFor(state.game.level) * 1000, left: secondsFor(state.game.level) };
      }
      return { ...state, queue, seen, nonce: state.nonce + 1 };
    }
    case "failed":
      return { ...state, phase: "error", error: action.message };
    case "tick": {
      if (state.phase !== "playing") return state;
      const left = (state.deadline - action.at) / 1000;
      return left <= 0 ? settle(state, null, action.at) : { ...state, left };
    }
    case "answer":
      return settle(state, action.pick, action.at);
    case "next": {
      if (state.phase !== "revealed") return state;
      if (isOver(state.game)) return { ...state, phase: "over" };
      const index = state.index + 1;
      if (index >= state.queue.length) return { ...state, index, phase: "loading" };
      const seconds = secondsFor(state.game.level);
      return { ...state, index, phase: "playing", picked: null, points: 0, leveledUp: false, deadline: action.at + seconds * 1000, left: seconds };
    }
  }
}

// ---- pieces -------------------------------------------------------------------------------------------------------------

function Hearts({ lives }: { lives: number }) {
  return (
    <div role="img" aria-label={`${lives} of ${LIVES} lives left`} className="flex gap-1">
      {Array.from({ length: LIVES }, (_, i) => (
        <HeartIcon key={i} width={24} height={24} filled={i < lives} className={cx("transition-colors duration-300", i < lives ? "text-accent" : "text-line")} />
      ))}
    </div>
  );
}

function SoundToggle() {
  const on = useSound();
  return (
    <button
      type="button"
      onClick={() => setSound(!on)}
      aria-pressed={on}
      aria-label={on ? "Sound on" : "Sound off"}
      className="flex size-11 items-center justify-center rounded-full text-muted hover:text-ink"
    >
      {on ? <SpeakerIcon width={20} height={20} /> : <MuteIcon width={20} height={20} />}
    </button>
  );
}

function ShareBar({ game }: { game: Game }) {
  const [status, setStatus] = useState("");
  const result = resultOf(game);
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const url = shareUrl(origin, result);
  const text = shareText(result);
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  const image = () => drawShareCard(result, origin);

  const share = async () => {
    try {
      const blob = await image();
      const file = new File([blob], "vantage-pop-quiz.png", { type: "image/png" });
      const withFile = navigator.canShare?.({ files: [file] }) ? { files: [file] } : {};
      await navigator.share({ title: "My Vantage pop quiz score", text, url, ...withFile });
    } catch (e) {
      if ((e as Error).name !== "AbortError") setStatus("Sharing didn't work here. Try one of the buttons instead.");
    }
  };
  const save = async () => {
    try {
      const blob = await image();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = "vantage-pop-quiz.png";
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(href), 2000);
      setStatus("Image saved. Attach it to your post.");
    } catch {
      setStatus("Couldn't make the image in this browser.");
    }
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${text} ${url}`);
      setStatus("Copied. Paste it wherever you like.");
    } catch {
      setStatus("Couldn't copy. Select the text and copy it yourself.");
    }
  };

  const link = "btn-raised inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-[15px] font-semibold text-ink";
  return (
    <section aria-labelledby="share-title" className="raised rounded-2xl p-4">
      <h3 id="share-title" className="font-display text-xl">
        Post your score
      </h3>
      <p className="mt-1 text-sm text-muted">Your post shows only your score and title. Not your name, email or profile.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {canShare && (
          <Button variant="primary" onClick={share} className="px-3.5">
            <ShareIcon width={18} height={18} />
            Share
          </Button>
        )}
        <a className={link} href={intents.linkedin(url)} target="_blank" rel="noopener noreferrer">
          LinkedIn
        </a>
        <a className={link} href={intents.x(text, url)} target="_blank" rel="noopener noreferrer">
          X
        </a>
        <a className={link} href={intents.whatsapp(text, url)} target="_blank" rel="noopener noreferrer">
          WhatsApp
        </a>
        <Button onClick={save} className="px-3.5">
          <DownloadIcon width={18} height={18} />
          Save image
        </Button>
        <Button onClick={copy} className="px-3.5">
          <CopyIcon width={18} height={18} />
          Copy text
        </Button>
      </div>
      <p role="status" className="mt-2 min-h-5 text-sm text-muted">
        {status}
      </p>
    </section>
  );
}

function Score({ value }: { value: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const id = window.setTimeout(() => setShown(value), 0);
      return () => window.clearTimeout(id);
    }
    const start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 900);
      setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return (
    <p className="font-display text-7xl leading-none tabular-nums">
      <span className="sr-only">{value.toLocaleString("en-IN")} points</span>
      <span aria-hidden data-testid="score">
        {shown.toLocaleString("en-IN")}
      </span>
    </p>
  );
}

// ---- the game ------------------------------------------------------------------------------------------------------------

export function QuizGame({ userId, onClose }: { userId: string; onClose: () => void }) {
  const [state, dispatch] = useReducer(reducer, undefined, initial);
  const [leaving, setLeaving] = useState(false);
  const [bestAtStart, setBestAtStart] = useState(() => readBest());
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const nextButton = useRef<HTMLButtonElement>(null);
  const fetching = useRef(false);
  const titleId = useId();
  const { phase, game, queue, index } = state;
  const question = queue[index];
  const sound = useSound();

  // A native modal dialog gives us focus trapping, Escape handling and an inert page behind it.
  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  const requestExit = useCallback(() => {
    if ((phase === "playing" || phase === "revealed") && game.answers.length > 0) setLeaving(true);
    else onClose();
  }, [phase, game.answers.length, onClose]);

  // Keep questions coming: ask for more when the queue runs low, and while waiting for the first ones.
  const wanted = phase === "loading" || ((phase === "playing" || phase === "revealed") && queue.length - index <= PREFETCH_WHEN_LEFT);
  useEffect(() => {
    if (!wanted || fetching.current) return;
    fetching.current = true;
    const controller = new AbortController();
    const level = game.level;
    api
      .quiz(userId, level, state.seen.slice(-REMEMBER_SEEN), BATCH, controller.signal)
      .then((batch) => {
        fetching.current = false;
        dispatch({ type: "loaded", questions: batch.questions, at: performance.now(), level });
      })
      .catch((e: Error) => {
        fetching.current = false;
        if (e.name !== "AbortError") dispatch({ type: "failed", message: navigator.onLine ? "We couldn't load questions just now." : "You're offline. Connect and try again." });
      });
    return () => controller.abort();
    // The level and the seen list are read when the request starts; changes to them alone shouldn't cancel one in flight.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, userId, queue.length, state.nonce]);

  // The clock.
  useEffect(() => {
    if (phase !== "playing") return;
    const id = window.setInterval(() => dispatch({ type: "tick", at: performance.now() }), 100);
    return () => window.clearInterval(id);
  }, [phase, index]);

  // Sounds and buzzes follow the answers, not the clicks, so a timeout sounds the same as a wrong pick.
  const answered = game.answers.length;
  const lastRight = game.answers[answered - 1]?.right;
  useEffect(() => {
    if (answered === 0) return;
    if (lastRight) {
      sounds.right(game.streak);
      if (state.leveledUp) window.setTimeout(sounds.levelUp, 260);
      buzz(20);
    } else {
      sounds.wrong();
      buzz([40, 60, 40]);
    }
    // Only when a new answer lands.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answered]);

  // A right answer moves on by itself after a moment. A wrong one waits, so the explanation can be read.
  const autoAdvance = phase === "revealed" && lastRight && !isOver(game);
  useEffect(() => {
    if (!autoAdvance) return;
    const id = window.setTimeout(() => dispatch({ type: "next", at: performance.now() }), 2200);
    return () => window.clearTimeout(id);
  }, [autoAdvance, index]);

  // The end of the game: remember the best score and play the closing sound.
  useEffect(() => {
    if (phase !== "over") return;
    saveIfBest(game);
    sounds.over();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // Where the keyboard and screen reader should be.
  useEffect(() => {
    if (phase === "playing" || phase === "over" || phase === "intro" || phase === "error") heading.current?.focus({ preventScroll: true });
    if (phase === "revealed") nextButton.current?.focus({ preventScroll: true });
  }, [phase, index]);

  // Answer with 1 to 4 or A to D.
  useEffect(() => {
    if (phase !== "playing" || !question) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const i = "1234".indexOf(e.key) >= 0 ? "1234".indexOf(e.key) : "abcd".indexOf(e.key.toLowerCase());
      if (i >= 0 && i < question.options.length) dispatch({ type: "answer", pick: i, at: performance.now() });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, question]);

  const start = () => {
    sounds.start();
    setBestAtStart(readBest()); // a game just finished may have set a new best
    dispatch({ type: "start" });
  };

  const rank = rankFor(game.correct);
  const more = nextRank(game.correct);
  const newBest = phase === "over" && game.score > (bestAtStart?.score ?? 0);
  const last = game.answers[answered - 1];
  const multiplier = (1 + Math.min(game.streak, 10) * 0.1).toFixed(1);

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
          {phase === "playing" || phase === "revealed" ? <Hearts lives={game.lives} /> : <span className="font-display text-xl">Vantage</span>}
          <div className="ml-auto flex items-center">
            {(phase === "playing" || phase === "revealed") && (
              <p className="mr-2 text-right leading-tight" aria-live="off">
                <span className="block font-display text-2xl tabular-nums">{game.score.toLocaleString("en-IN")}</span>
                <span className="block font-mono text-xs text-muted">points</span>
              </p>
            )}
            <SoundToggle />
            <button type="button" onClick={requestExit} aria-label="Close the quiz" className="-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink">
              <CloseIcon width={22} height={22} />
            </button>
          </div>
        </header>

        {leaving && (
          <div role="alertdialog" aria-label="Leave the quiz?" className="raised mb-4 rounded-2xl p-4">
            <p className="font-semibold">Leave the quiz?</p>
            <p className="mt-1 text-sm text-muted">Your score of {game.score.toLocaleString("en-IN")} won&apos;t be saved.</p>
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
            <p className="font-mono text-xs text-accent">Pop quiz</p>
            <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-2 font-display text-[40px] leading-[1.05] outline-none">
              How well do you know your field?
            </h1>
            <p className="mt-4 text-[17px] leading-relaxed text-muted">
              The questions come from your fields, roles and companies, plus a few management basics. Keep going until you get three wrong. It gets harder every four right answers, and the clock gets shorter.
            </p>
            <ul className="mt-5 grid grid-cols-3 gap-2 text-center text-sm">
              {[
                [`${LIVES}`, "lives"],
                [`${secondsFor(1)}s`, "to start"],
                ["No limit", "on questions"],
              ].map(([big, small]) => (
                <li key={small} className="raised rounded-xl px-2 py-3">
                  <span className="block font-display text-xl">{big}</span>
                  <span className="text-muted">{small}</span>
                </li>
              ))}
            </ul>
            {bestAtStart && <p className="mt-4 text-sm text-muted">Your best so far: <span className="font-semibold text-ink">{bestAtStart.score.toLocaleString("en-IN")}</span> points.</p>}
            <Button variant="primary" onClick={start} className="mt-6 w-full">
              Start
            </Button>
            <p className="mt-3 text-center text-sm text-muted">Tip: press 1 to 4 to answer.</p>
            <PartnerBadge size="sm" className="mt-6 justify-center border-t border-line pt-4" />
          </div>
        )}

        {phase === "loading" && (
          <div role="status" className="my-auto py-10 text-center text-muted">
            <p className="font-display text-2xl text-ink">
              {game.answers.length === 0 ? "Getting your questions ready" : "One moment"}
            </p>
            <p className="mt-2 text-sm">Picking ones you haven&apos;t seen yet.</p>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="my-auto py-10 text-center">
            <h1 id={titleId} ref={heading} tabIndex={-1} className="font-display text-2xl outline-none">
              We couldn&apos;t start the quiz
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

        {(phase === "playing" || phase === "revealed") && question && (
          <div className="flex flex-1 flex-col">
            <div aria-hidden className="h-1.5 w-full overflow-hidden rounded-full bg-sunken">
              <div
                className={cx("h-full rounded-full transition-[width] duration-100 ease-linear", state.left <= 5 ? "bg-accent" : "bg-ink/70")}
                style={{ width: `${phase === "revealed" ? 0 : Math.max(0, Math.min(100, (state.left / secondsFor(game.level)) * 100))}%` }}
              />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              <Chip tone="accent">Level {game.level}</Chip>
              {question.field && <Chip>{question.field}</Chip>}
              {game.streak >= 2 && <Chip tone="good">Streak {game.streak} · x{multiplier}</Chip>}
              <span role="timer" className="ml-auto font-mono text-muted tabular-nums" aria-label="Seconds left">
                {phase === "playing" ? `${Math.ceil(state.left)}s` : ""}
              </span>
            </div>

            <h2 id={titleId} ref={heading} tabIndex={-1} className="mt-5 font-display text-[28px] leading-[1.15] outline-none md:text-[32px]">
              {question.prompt}
            </h2>
            {question.context && (
              <blockquote className="mt-4 font-display text-[19px] italic leading-snug">&ldquo;{question.context}&rdquo;</blockquote>
            )}

            <div role="group" aria-labelledby={titleId} className="mt-6 grid gap-2.5">
              {question.options.map((option, i) => {
                const revealed = phase === "revealed";
                const isRight = revealed && i === question.answer;
                const isWrong = revealed && i === state.picked && i !== question.answer;
                return (
                  <button
                    key={`${question.id}-${i}`}
                    type="button"
                    disabled={revealed}
                    onClick={() => dispatch({ type: "answer", pick: i, at: performance.now() })}
                    className={cx(
                      "flex min-h-14 w-full items-center gap-3 rounded-xl border px-3.5 py-2.5 text-left text-[16px] leading-snug transition-colors disabled:cursor-default",
                      !revealed && "border-line bg-surface hover:border-muted",
                      isRight && "border-good bg-good-soft text-ink",
                      isWrong && "border-accent bg-accent-soft text-ink",
                      revealed && !isRight && !isWrong && "border-line bg-surface opacity-60",
                    )}
                  >
                    <span className={cx("flex size-8 shrink-0 items-center justify-center rounded-lg border font-mono text-sm", isRight ? "border-good text-good" : isWrong ? "border-accent text-accent" : "border-line text-muted")}>
                      {isRight ? <CheckIcon width={16} height={16} /> : isWrong ? <CloseIcon width={16} height={16} /> : "ABCD"[i]}
                    </span>
                    <span className="flex-1">{option}</span>
                    {isRight && <span className="sr-only">Correct answer</span>}
                    {isWrong && <span className="sr-only">Your answer, not correct</span>}
                  </button>
                );
              })}
            </div>

            <div role="status" aria-live="polite" className="mt-5">
              {phase === "revealed" && last && (
                <div className="rise raised rounded-2xl p-4">
                  <p className="font-display text-xl">
                    {last.right ? `Correct. +${state.points}` : last.picked === null ? "Time's up." : "Not quite."}
                  </p>
                  {!last.right && <p className="mt-1 text-[15px]">The answer is {question.options[question.answer]}.</p>}
                  <p className="mt-1 text-[15px] leading-snug text-muted">{question.explain}</p>
                  {state.leveledUp && <p className="mt-2 text-[15px] font-semibold text-accent">Level {game.level}. Harder questions and less time from here.</p>}
                  {!last.right && (
                    <p className="mt-2 text-sm text-muted">{game.lives > 0 ? `${game.lives} ${game.lives === 1 ? "life" : "lives"} left.` : "That was your last life."}</p>
                  )}
                  <Button ref={nextButton} variant="primary" className="mt-3 w-full" onClick={() => dispatch({ type: "next", at: performance.now() })}>
                    {isOver(game) ? "See your result" : "Next question"}
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}

        {phase === "over" && (
          <div className="rise flex flex-col gap-5 py-2">
            <div>
              <p className="font-mono text-xs text-accent">Game over</p>
              <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-1 font-display text-[34px] leading-[1.1] outline-none">
                You made it to {rank.title}
              </h1>
              <div className="mt-4">
                <Score value={game.score} />
                <p className="mt-1 text-muted">
                  points{newBest ? <span className="ml-2 rounded bg-accent-soft px-2 py-0.5 text-sm font-semibold text-accent">New best</span> : bestAtStart ? `, your best is ${bestAtStart.score.toLocaleString("en-IN")}` : ""}
                </p>
              </div>
            </div>
            <dl className="grid grid-cols-3 gap-2 text-center">
              {[
                [game.correct, "right"],
                [game.bestStreak, "best streak"],
                [`${accuracy(game)}%`, "accuracy"],
              ].map(([value, label]) => (
                <div key={String(label)} className="raised rounded-xl px-2 py-3">
                  <dd className="font-display text-2xl">{value}</dd>
                  <dt className="text-sm text-muted">{label}</dt>
                </div>
              ))}
            </dl>
            {more && (
              <p className="text-[15px] text-muted">
                {more.needed} more right {more.needed === 1 ? "answer" : "answers"} would have made you {more.title}.
              </p>
            )}
            <ShareBar game={game} />
            {game.answers.some((a) => !a.right) && (
              <details className="raised rounded-2xl p-4">
                <summary className="cursor-pointer font-semibold">What you missed</summary>
                <ul className="mt-3 space-y-3">
                  {game.answers
                    .filter((a) => !a.right)
                    .slice(-10)
                    .map((a) => (
                      <li key={a.question.id} className="text-[15px] leading-snug">
                        <p className="font-semibold">{a.question.context ? `${a.question.prompt} “${a.question.context}”` : a.question.prompt}</p>
                        <p className="text-muted">Answer: {a.question.options[a.question.answer]}. {a.question.explain}</p>
                      </li>
                    ))}
                </ul>
              </details>
            )}
            <div className="flex gap-2">
              <Button variant="primary" onClick={start} className="flex-1">
                Play again
              </Button>
              <Button onClick={onClose} className="flex-1">
                Close
              </Button>
            </div>
          </div>
        )}
      </div>
      <p className="sr-only" aria-live="polite">
        {sound ? "" : "Sound is off."}
      </p>
    </dialog>
  );
}
