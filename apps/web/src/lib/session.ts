// Who is using this device. A signed-in account is proven by an HttpOnly cookie the browser keeps; the
// user id kept here only tells the app which profile to ask for. A guest has no account: a random id
// on this device stands in, sent as X-User-Id.
import { useSyncExternalStore } from "react";

const KEY = "vantage.userId";
const ACCOUNT_KEY = "vantage.account";
const EVENT = "vantage:session";

function read(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null; // private mode or blocked storage
  }
}

export function getUserId(): string | null {
  return typeof window === "undefined" ? null : read();
}

export function setUserId(id: string, account = false): void {
  try {
    window.localStorage.setItem(KEY, id);
    if (account) window.localStorage.setItem(ACCOUNT_KEY, "1");
    else window.localStorage.removeItem(ACCOUNT_KEY);
  } catch {}
  dropCachedReads();
  window.dispatchEvent(new Event(EVENT));
}

/** A device id to act as, creating a guest one on the spot if this is the first time it's needed
 * (e.g. adding a missing role/company mid-onboarding, before the account exists yet). */
export function ensureUserId(): string {
  const existing = getUserId();
  if (existing) return existing;
  const id = createUserId();
  setUserId(id);
  return id;
}

export function isAccount(): boolean {
  try {
    return typeof window !== "undefined" && window.localStorage.getItem(ACCOUNT_KEY) === "1";
  } catch {
    return false;
  }
}

/** Cached API reads are personal, so drop them whenever the identity changes. */
function dropCachedReads(): void {
  navigator.serviceWorker?.controller?.postMessage("clear-runtime");
}

export function clearSession(): void {
  try {
    window.localStorage.removeItem(KEY);
    window.localStorage.removeItem(ACCOUNT_KEY);
  } catch {}
  dropCachedReads();
  window.dispatchEvent(new Event(EVENT));
}

export function createUserId(): string {
  // randomUUID needs a secure context; testing over plain-http LAN would otherwise crash.
  const c: Crypto = crypto;
  if (typeof c.randomUUID === "function") return c.randomUUID();
  const bytes = c.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function subscribe(callback: () => void): () => void {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/** Whether this device is signed in with an account (false while hydrating, so server and client agree). */
export function useIsAccount(): boolean {
  return useSyncExternalStore(subscribe, isAccount, () => false);
}

const DELETED_KEY = "vantage.deleted";

export function rememberDeletion(): void {
  try {
    window.sessionStorage.setItem(DELETED_KEY, "1");
  } catch {}
}

export function useDeletedNotice(): [boolean, () => void] {
  const shown = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return window.sessionStorage.getItem(DELETED_KEY) === "1";
      } catch {
        return false;
      }
    },
    () => false,
  );
  const dismiss = () => {
    try {
      window.sessionStorage.removeItem(DELETED_KEY);
    } catch {}
    window.dispatchEvent(new Event(EVENT));
  };
  return [shown, dismiss];
}

/** undefined while hydrating, null when signed out, otherwise the user id. */
export function useUserId(): string | null | undefined {
  return useSyncExternalStore(subscribe, read, () => undefined);
}
