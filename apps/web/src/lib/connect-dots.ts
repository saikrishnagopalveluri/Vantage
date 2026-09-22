/** Rules and helpers for Connect the Dots: build a chain of real, related job roles. Each role's related
 *  roles (already computed server-side from shared skills, via /taxonomy/roles/{id}) become the next dots
 *  you can tap. A role already in the chain can't be reused. Reach the target length to win; if every
 *  neighbor of the current dot is already used, the chain breaks. There's no invented "right answer" —
 *  every offered dot is already a real connection, and the challenge is not painting yourself into a
 *  corner. Kept free of React so it can be tested on its own, the same way the other games' rule modules
 *  are. */

export const CHAIN_TARGET = 6; // dots in a winning chain, start included

export interface ChainDot {
  id: string;
  title: string;
}

export interface ChainState {
  chain: ChainDot[];
  options: ChainDot[]; // the current dot's neighbors that aren't already in the chain
  status: "playing" | "won" | "lost";
}

function unusedNeighbors(chain: ChainDot[], neighbors: ChainDot[]): ChainDot[] {
  const used = new Set(chain.map((d) => d.id));
  const seen = new Set<string>();
  return neighbors.filter((n) => {
    if (used.has(n.id) || seen.has(n.id)) return false;
    seen.add(n.id);
    return true;
  });
}

function statusFor(chain: ChainDot[], options: ChainDot[]): ChainState["status"] {
  if (chain.length >= CHAIN_TARGET) return "won";
  if (options.length === 0) return "lost";
  return "playing";
}

export function startChain(start: ChainDot, neighbors: ChainDot[]): ChainState {
  const chain = [start];
  const options = unusedNeighbors(chain, neighbors);
  return { chain, options, status: statusFor(chain, options) };
}

/** Extends the chain with a picked dot and that dot's own neighbors (fetched by the caller, since a real
 *  lookup sits between one hop and the next — there's no way to know a role's connections before asking
 *  for it). Picking anything not currently offered is a no-op: the caller shouldn't be able to trigger
 *  this, but state stays honest either way. */
export function extendChain(state: ChainState, picked: ChainDot, pickedNeighbors: ChainDot[]): ChainState {
  if (state.status !== "playing" || !state.options.some((o) => o.id === picked.id)) return state;
  const chain = [...state.chain, picked];
  const options = unusedNeighbors(chain, pickedNeighbors);
  return { chain, options, status: statusFor(chain, options) };
}

// ---- best chain --------------------------------------------------------------------------------------------------------

const BEST_KEY = "vantage.connectdots.best";

export function readChainBest(): number | null {
  try {
    const raw = window.localStorage.getItem(BEST_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) && n > 0 ? n : null;
  } catch {
    return null;
  }
}

/** The longest chain reached counts, whether it ended in a win or a dead end — there's no losing state
 *  that erases progress here, only a shorter or longer chain. Returns whether this one set a new best. */
export function saveChainIfBest(length: number): boolean {
  const best = readChainBest();
  if (best !== null && best >= length) return false;
  try {
    window.localStorage.setItem(BEST_KEY, String(length));
  } catch {}
  return true;
}
