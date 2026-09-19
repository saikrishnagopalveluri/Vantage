import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

interface Settled<T> {
  key: string;
  data?: T;
  error?: Error;
}

/**
 * Runs `fn` whenever `key` changes. Keeps the previous data while reloading so screens
 * don't flash empty; `loading` is derived, so no state is set synchronously in the effect.
 */
export function useAsync<T>(fn: (signal: AbortSignal) => Promise<T>, key: string) {
  const [tick, setTick] = useState(0);
  const [result, setResult] = useState<Settled<T>>();
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });

  const fullKey = `${key}#${tick}`;
  useEffect(() => {
    const controller = new AbortController();
    fnRef.current(controller.signal).then(
      (data) => !controller.signal.aborted && setResult({ key: fullKey, data }),
      (error: Error) => !controller.signal.aborted && setResult({ key: fullKey, error }),
    );
    return () => controller.abort();
  }, [fullKey]);

  const settled = result?.key === fullKey;
  return {
    data: result?.data,
    error: settled ? result?.error : undefined,
    loading: !settled,
    reload: useCallback(() => setTick((t) => t + 1), []),
    setData: useCallback((data: T) => setResult((r) => ({ key: r?.key ?? "", ...r, data })), []),
  };
}

export function useDebounced<T>(value: T, ms = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

function subscribeOnline(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

export function useOnline(): boolean {
  return useSyncExternalStore(
    subscribeOnline,
    () => navigator.onLine,
    () => true,
  );
}

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

/** Install affordances: native prompt where the browser offers one, instructions on iOS. */
export function useInstall() {
  const [event, setEvent] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setEvent(e as InstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setEvent(null);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  const standalone = useSyncExternalStore(
    () => () => {},
    () =>
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true,
    () => false,
  );
  const ios = useSyncExternalStore(
    () => () => {},
    () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1),
    () => false,
  );

  const install = useCallback(async () => {
    if (!event) return;
    await event.prompt();
    const { outcome } = await event.userChoice;
    if (outcome === "accepted") setInstalled(true);
    setEvent(null);
  }, [event]);

  return { canPrompt: event !== null, install, ios, standalone: standalone || installed };
}
