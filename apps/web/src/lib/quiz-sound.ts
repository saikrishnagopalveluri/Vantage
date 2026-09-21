/**
 * Small sound effects for the quiz, made with the Web Audio API so there are no files to download.
 * Quiet by design, and off with one tap. The choice is remembered on the device.
 */
import { useSyncExternalStore } from "react";

const KEY = "vantage.quiz.sound";
const EVENT = "vantage:quiz-sound";
let context: AudioContext | null = null;

function readOn(): boolean {
  try {
    return window.localStorage.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}

export function setSound(on: boolean) {
  try {
    window.localStorage.setItem(KEY, on ? "on" : "off");
  } catch {}
  window.dispatchEvent(new Event(EVENT));
}

export function useSound(): boolean {
  return useSyncExternalStore(
    (l) => {
      window.addEventListener(EVENT, l);
      return () => window.removeEventListener(EVENT, l);
    },
    readOn,
    () => true,
  );
}

function audio(): AudioContext | null {
  if (typeof window === "undefined" || !readOn()) return null;
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return null;
    context = context ?? new Ctx();
    if (context.state === "suspended") void context.resume();
    return context;
  } catch {
    return null;
  }
}

function tone(ctx: AudioContext, frequency: number, start: number, length: number, type: OscillatorType = "sine", volume = 0.05) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(frequency, ctx.currentTime + start);
  // A short attack and a smooth release, so there is no click.
  gain.gain.setValueAtTime(0.0001, ctx.currentTime + start);
  gain.gain.linearRampToValueAtTime(volume, ctx.currentTime + start + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + length);
  osc.connect(gain).connect(ctx.destination);
  osc.start(ctx.currentTime + start);
  osc.stop(ctx.currentTime + start + length + 0.02);
}

const NOTE = { c5: 523.25, e5: 659.25, g5: 783.99, c6: 1046.5, a3: 220, e3: 164.81, g4: 392 };

export const sounds = {
  start() {
    const c = audio();
    if (!c) return;
    tone(c, NOTE.g4, 0, 0.12);
    tone(c, NOTE.c5, 0.09, 0.16);
  },
  right(streak: number) {
    const c = audio();
    if (!c) return;
    tone(c, NOTE.c5, 0, 0.12);
    tone(c, streak >= 4 ? NOTE.g5 : NOTE.e5, 0.08, 0.16);
    if (streak >= 4) tone(c, NOTE.c6, 0.17, 0.2);
  },
  wrong() {
    const c = audio();
    if (!c) return;
    tone(c, NOTE.a3, 0, 0.2, "triangle", 0.07);
    tone(c, NOTE.e3, 0.12, 0.28, "triangle", 0.07);
  },
  levelUp() {
    const c = audio();
    if (!c) return;
    [NOTE.c5, NOTE.e5, NOTE.g5, NOTE.c6].forEach((f, i) => tone(c, f, i * 0.08, 0.16));
  },
  over() {
    const c = audio();
    if (!c) return;
    [NOTE.g5, NOTE.e5, NOTE.c5, NOTE.g4].forEach((f, i) => tone(c, f, i * 0.14, 0.24, "triangle", 0.06));
  },
};

/** A short buzz on phones that support it. */
export function buzz(pattern: number | number[]) {
  try {
    if (readOn()) navigator.vibrate?.(pattern);
  } catch {}
}
