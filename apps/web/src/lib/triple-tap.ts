import { useCallback, useRef, type MouseEvent } from "react";

export const OPEN_QUIZ_EVENT = "vantage:open-quiz";

/**
 * A handler that fires `onTriple` when it is clicked three times in quick succession. The third click is
 * swallowed so it doesn't also follow a link. Works the same for taps, mouse clicks and Enter on a focused link.
 */
export function useMultiTap(onTriple: () => void, taps = 3, windowMs = 800) {
  const times = useRef<number[]>([]);
  return useCallback(
    (event?: MouseEvent) => {
      const now = performance.now();
      times.current = [...times.current.filter((t) => now - t < windowMs), now];
      if (times.current.length >= taps) {
        times.current = [];
        event?.preventDefault();
        onTriple();
      }
    },
    [onTriple, taps, windowMs],
  );
}

/** Ask the app to open the pop quiz from anywhere, for example a button on the profile page. */
export const openQuiz = () => window.dispatchEvent(new Event(OPEN_QUIZ_EVENT));
