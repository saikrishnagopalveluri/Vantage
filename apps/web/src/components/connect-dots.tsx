"use client";

import { useCallback, useEffect, useId, useReducer, useRef, useState } from "react";
import { api } from "@/lib/api";
import { CHAIN_TARGET, extendChain, readChainBest, saveChainIfBest, startChain, type ChainDot, type ChainState } from "@/lib/connect-dots";
import { CloseIcon } from "./icons";
import { PartnerBadge } from "./partner-badge";
import { Button, cx } from "./ui";

// ---- game state -----------------------------------------------------------------------------------------------------

type Phase = "intro" | "loading" | "playing" | "over" | "error";

interface State {
  phase: Phase;
  chain: ChainState | null;
  pending: ChainDot | null; // the dot whose own neighbors are being fetched
  error: string | null;
}

type Action =
  | { type: "start" }
  | { type: "loaded"; start: ChainDot; neighbors: ChainDot[] }
  | { type: "pick"; dot: ChainDot }
  | { type: "extended"; neighbors: ChainDot[] }
  | { type: "failed"; message: string };

const initial = (): State => ({ phase: "intro", chain: null, pending: null, error: null });

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...initial(), phase: "loading" };
    case "loaded": {
      const chain = startChain(action.start, action.neighbors);
      return { phase: chain.status === "playing" ? "playing" : "over", chain, pending: null, error: null };
    }
    case "pick":
      return state.phase === "playing" ? { ...state, phase: "loading", pending: action.dot } : state;
    case "extended": {
      if (!state.chain || !state.pending) return state;
      const chain = extendChain(state.chain, state.pending, action.neighbors);
      return { ...state, chain, phase: chain.status === "playing" ? "playing" : "over", pending: null };
    }
    case "failed":
      return { ...state, phase: "error", error: action.message };
  }
}

const asDots = (related: { role: { id: string; title: string } }[]): ChainDot[] => related.map((r) => ({ id: r.role.id, title: r.role.title }));

// ---- the game ---------------------------------------------------------------------------------------------------------

export function ConnectDots({ onClose }: { onClose: () => void }) {
  const [state, dispatch] = useReducer(reducer, undefined, initial);
  const [bestAtStart, setBestAtStart] = useState(() => readChainBest());
  const dialog = useRef<HTMLDialogElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const fetching = useRef(false);
  const titleId = useId();
  const { phase, chain, pending } = state;

  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
    return () => {
      if (d?.open) d.close();
    };
  }, []);

  // Either the very first role, or the next hop's neighbors — both are a role lookup away.
  useEffect(() => {
    if (phase !== "loading" || fetching.current) return;
    fetching.current = true;
    const controller = new AbortController();
    const failMessage = () => (navigator.onLine ? "We couldn't look up a role just now." : "You're offline. Connect and try again.");

    if (!pending) {
      api
        .roles("", null, controller.signal, 40, true)
        .then((roles) => {
          if (roles.length === 0) throw new Error("no-roles");
          const start = roles[Math.floor(Math.random() * roles.length)];
          return api.roleDetail(start.id, controller.signal).then((detail) => {
            fetching.current = false;
            dispatch({ type: "loaded", start: { id: start.id, title: start.title }, neighbors: asDots(detail.related_roles) });
          });
        })
        .catch((e: Error) => {
          fetching.current = false;
          if (e.name !== "AbortError") dispatch({ type: "failed", message: failMessage() });
        });
    } else {
      api
        .roleDetail(pending.id, controller.signal)
        .then((detail) => {
          fetching.current = false;
          dispatch({ type: "extended", neighbors: asDots(detail.related_roles) });
        })
        .catch((e: Error) => {
          fetching.current = false;
          if (e.name !== "AbortError") dispatch({ type: "failed", message: failMessage() });
        });
    }
    return () => controller.abort();
  }, [phase, pending]);

  useEffect(() => {
    if (phase !== "over" || !chain) return;
    saveChainIfBest(chain.chain.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    if (phase === "playing" || phase === "over" || phase === "intro" || phase === "error") heading.current?.focus({ preventScroll: true });
  }, [phase]);

  const start = useCallback(() => {
    setBestAtStart(readChainBest());
    dispatch({ type: "start" });
  }, []);

  const newBest = phase === "over" && chain !== null && (bestAtStart === null || chain.chain.length > bestAtStart);

  return (
    <dialog ref={dialog} aria-labelledby={titleId} onCancel={(e) => { e.preventDefault(); onClose(); }} className="m-0 h-dvh max-h-none w-dvw max-w-none overflow-y-auto bg-paper p-0 text-ink">
      <div className="pt-safe px-safe mx-auto flex min-h-dvh w-full max-w-xl flex-col pb-6">
        <header className="flex h-14 items-center gap-2">
          <span className="font-display text-xl">Vantage</span>
          <div className="ml-auto flex items-center">
            {phase === "playing" && chain && (
              <p className="mr-2 text-right leading-tight" aria-live="off">
                <span className="block font-display text-2xl tabular-nums">{chain.chain.length}</span>
                <span className="block font-mono text-xs text-muted">of {CHAIN_TARGET}</span>
              </p>
            )}
            <button type="button" onClick={onClose} aria-label="Close Connect the Dots" className="-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink">
              <CloseIcon width={22} height={22} />
            </button>
          </div>
        </header>

        {phase === "intro" && (
          <div className="rise my-auto py-6">
            <p className="font-mono text-xs text-accent">Connect the Dots</p>
            <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-2 font-display text-[40px] leading-[1.05] outline-none">
              Chain six real, related roles.
            </h1>
            <p className="mt-4 text-[17px] leading-relaxed text-muted">
              Every role shown is a real connection, worked out from the skills it shares with the one before it. Tap one to extend the chain. You can&apos;t reuse a role, so the trick is not running out of new ones to reach.
            </p>
            {bestAtStart && (
              <p className="mt-4 text-sm text-muted">
                Your longest chain: <span className="font-semibold text-ink">{bestAtStart}</span>.
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
            <p className="font-display text-2xl text-ink">{pending ? "Looking up that role" : "Picking a place to start"}</p>
            <p className="mt-2 text-sm">From the real roles and skills in the taxonomy.</p>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="my-auto py-10 text-center">
            <h1 id={titleId} ref={heading} tabIndex={-1} className="font-display text-2xl outline-none">
              We couldn&apos;t start Connect the Dots
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

        {phase === "playing" && chain && (
          <div className="flex flex-1 flex-col">
            <h2 id={titleId} ref={heading} tabIndex={-1} className="mt-5 font-display text-[26px] leading-[1.15] outline-none">
              Pick the next link.
            </h2>
            <ol aria-label="Your chain so far" className="mt-5 flex flex-wrap items-center gap-x-1.5 gap-y-2">
              {chain.chain.map((dot, i) => (
                <li key={dot.id} className="flex items-center gap-1.5">
                  {i > 0 && <span aria-hidden className="text-muted">&rarr;</span>}
                  <span className="rounded-full border border-line bg-surface px-3 py-1 text-sm font-semibold">{dot.title}</span>
                </li>
              ))}
            </ol>
            <p className="mt-6 font-mono text-xs text-muted">Connected to {chain.chain[chain.chain.length - 1].title}</p>
            <ul aria-label="Roles you can connect next" className="mt-2 flex flex-col gap-2">
              {chain.options.map((dot) => (
                <li key={dot.id}>
                  <button
                    type="button"
                    onClick={() => dispatch({ type: "pick", dot })}
                    className={cx("btn-raised flex min-h-14 w-full items-center rounded-xl px-3.5 text-left text-[15px] font-semibold")}
                  >
                    {dot.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {phase === "over" && chain && (
          <div className="rise flex flex-col gap-5 py-2">
            <div>
              <p className="font-mono text-xs text-accent">{chain.status === "won" ? "Chain complete" : "Chain broken"}</p>
              <h1 id={titleId} ref={heading} tabIndex={-1} className="mt-1 font-display text-[34px] leading-[1.1] outline-none">
                {chain.chain.length} {chain.chain.length === 1 ? "role" : "roles"} connected
              </h1>
              <p className="mt-2 text-muted">
                {chain.status === "won" ? "You reached the target." : `No new role connects to ${chain.chain[chain.chain.length - 1].title} anymore.`}
                {newBest ? <span className="ml-2 rounded bg-accent-soft px-2 py-0.5 text-sm font-semibold text-accent">New best</span> : bestAtStart ? `, your longest is ${bestAtStart}` : ""}
              </p>
              <ol aria-label="Your chain" className="mt-3 flex flex-wrap items-center gap-x-1.5 gap-y-2">
                {chain.chain.map((dot, i) => (
                  <li key={dot.id} className="flex items-center gap-1.5">
                    {i > 0 && <span aria-hidden className="text-muted">&rarr;</span>}
                    <span className="rounded-full border border-line bg-surface px-3 py-1 text-sm">{dot.title}</span>
                  </li>
                ))}
              </ol>
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
