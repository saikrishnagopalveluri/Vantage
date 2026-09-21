/**
 * Read a story's summary and pointers aloud with the browser's own speech engine. Nothing is sent to
 * a server: the text is already on the page and the voices are the ones installed on the device.
 *
 * Browsers don't say whether a voice is male or female, so the gender is read from the voice's name
 * ("Microsoft Zira", "Google UK English Male"). When a device has no voice of the kind asked for, the
 * closest English voice is used with its pitch moved, and the caller is told so it can say so.
 */
import { useSyncExternalStore } from "react";

export type Gender = "female" | "male";
export interface Prefs {
  gender: Gender;
  rate: number;
}
export interface Picked {
  voice: SpeechSynthesisVoice | null;
  pitch: number;
  /** True when no voice of the requested gender exists and pitch is standing in for one. */
  approximated: boolean;
}
export type Status = "idle" | "playing" | "paused";
interface Speaking {
  id: string | null;
  status: Status;
}

export const RATES = [0.8, 1, 1.15, 1.3, 1.5] as const;
const PREFS_KEY = "vantage.voice";
const DEFAULT_PREFS: Prefs = { gender: "female", rate: 1 };
const FEMALE_PITCH = 1.15;
const MALE_PITCH = 0.85;
const CHUNK_CHARS = 180; // long utterances get cut off after about 15 seconds in Chrome

const FEMALE =
  /\b(female|woman|zira|aria|jenny|samantha|victoria|karen|moira|tessa|fiona|susan|hazel|heera|neerja|swara|priya|veena|sonia|libby|natasha|emma|salli|joanna|kendra|kimberly|ivy|amy|olivia|ava|allison|serena|nicky|kalpana|lekha|aditi|raveena|sara|michelle|clara|molly)\b/i;
const MALE =
  /\b(male|david|mark|guy|ryan|daniel|alex|fred|james|george|rishi|ravi|prabhat|hemant|liam|thomas|arthur|matthew|brian|joey|justin|russell|oliver|aaron|eric|davis|tony|christopher|steffan|gordon|kevin|jacob|sam|nathan)\b/i;

export function voiceGender(name: string): Gender | null {
  if (FEMALE.test(name)) return "female";
  if (MALE.test(name)) return "male";
  return null;
}

/** English voices only, Indian English first for our readers, then the other Englishes; "natural" neural voices sound best. */
function rank(voice: SpeechSynthesisVoice): number {
  const lang = voice.lang.replace("_", "-").toLowerCase();
  const region = lang === "en-in" ? 3 : lang === "en-gb" ? 2 : lang === "en-us" ? 2 : 1;
  const natural = /natural|neural|online/i.test(voice.name) ? 2 : 0;
  return region + natural + (voice.default ? 0.5 : 0);
}

export function pickVoice(voices: readonly SpeechSynthesisVoice[], gender: Gender): Picked {
  const english = voices.filter((v) => v.lang.replace("_", "-").toLowerCase().startsWith("en"));
  const best = (list: SpeechSynthesisVoice[]) => [...list].sort((a, b) => rank(b) - rank(a))[0] ?? null;
  const match = best(english.filter((v) => voiceGender(v.name) === gender));
  if (match) return { voice: match, pitch: 1, approximated: false };
  // Nothing of that gender: prefer a voice that is at least the other way round, so the pitch shift is small.
  const fallback = best(english.filter((v) => voiceGender(v.name) === null)) ?? best(english);
  return { voice: fallback, pitch: gender === "female" ? FEMALE_PITCH : MALE_PITCH, approximated: true };
}

/** Make text sound right read aloud: symbols spelled out, stray markup and spacing removed. */
export function speakable(text: string): string {
  return text
    .replace(/<[^>]+>/g, " ")
    .replace(/&/g, " and ")
    .replace(/₹\s?/g, "rupees ")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function sentence(text: string): string {
  const t = speakable(text);
  return !t ? "" : /[.!?…]["')\]]?$/.test(t) ? t : `${t}.`;
}

/** The order it is read in: headline, summary paragraphs, then the pointers, with spoken headings between. */
export function scriptFor(title: string, brief: { paragraphs: string[]; pointers: string[] } | null): string {
  const parts = [sentence(title)];
  if (brief?.paragraphs.length) parts.push("Summary.", ...brief.paragraphs.map(sentence));
  if (brief?.pointers.length) parts.push("Quick pointers.", ...brief.pointers.map(sentence));
  return parts.filter(Boolean).join(" ");
}

/** Split into pieces of about CHUNK_CHARS, at sentence ends where possible, so no piece is cut off mid-way. */
export function chunk(text: string, max = CHUNK_CHARS): string[] {
  const out: string[] = [];
  let line = "";
  const push = () => {
    if (line.trim()) out.push(line.trim());
    line = "";
  };
  for (const s of text.split(/(?<=[.!?…])\s+/)) {
    if (s.length > max) {
      push();
      let rest = s;
      while (rest.length > max) {
        const cut = Math.max(rest.lastIndexOf(", ", max), rest.lastIndexOf(" ", max));
        out.push(rest.slice(0, cut > 0 ? cut + 1 : max).trim());
        rest = rest.slice(cut > 0 ? cut + 1 : max);
      }
      line = rest;
    } else if ((line + " " + s).trim().length > max) {
      push();
      line = s;
    } else {
      line = (line + " " + s).trim();
    }
  }
  push();
  return out;
}

// ---- playback (one story at a time, shared by every card) ---------------------------------------------

let speaking: Speaking = { id: null, status: "idle" };
let active: { id: string; pieces: string[]; index: number } | null = null;
let approximatedNow = false;
const listeners = new Set<() => void>();

function set(next: Speaking) {
  speaking = next;
  listeners.forEach((l) => l());
}
function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function isSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window && typeof SpeechSynthesisUtterance !== "undefined";
}

export function stop() {
  if (isSupported()) window.speechSynthesis.cancel();
  active = null;
  set({ id: null, status: "idle" });
}

export function stopIfPlaying(id: string) {
  if (speaking.id === id) stop();
}

/** Start reading `pieces`, from piece `from`, replacing whatever was being read. Returns how the voice was chosen. */
export function speak(id: string, pieces: string[], prefs: Prefs, from = 0): Picked {
  const synth = window.speechSynthesis;
  synth.cancel();
  const picked = pickVoice(synth.getVoices(), prefs.gender);
  approximatedNow = picked.approximated;
  active = { id, pieces, index: from };
  pieces.slice(from).forEach((piece, offset) => {
    const u = new SpeechSynthesisUtterance(piece);
    if (picked.voice) {
      u.voice = picked.voice;
      u.lang = picked.voice.lang;
    } else {
      u.lang = "en-IN";
    }
    u.pitch = picked.pitch;
    u.rate = prefs.rate;
    u.onstart = () => {
      if (active?.id === id) active.index = from + offset;
    };
    const last = from + offset === pieces.length - 1;
    u.onend = () => {
      if (last && active?.id === id) {
        active = null;
        set({ id: null, status: "idle" });
      }
    };
    u.onerror = (e) => {
      if (e.error === "canceled" || e.error === "interrupted") return; // we cancelled it ourselves
      if (active?.id === id) {
        active = null;
        set({ id: null, status: "idle" });
      }
    };
    synth.speak(u);
  });
  set({ id, status: "playing" });
  return picked;
}

/** Same story, new voice or speed, carrying on from the sentence being read. */
export function restart(prefs: Prefs) {
  if (active) speak(active.id, active.pieces, prefs, active.index);
}

export function pause() {
  if (speaking.status !== "playing") return;
  window.speechSynthesis.pause();
  set({ id: speaking.id, status: "paused" });
}

export function resume() {
  if (speaking.status !== "paused") return;
  window.speechSynthesis.resume();
  set({ id: speaking.id, status: "playing" });
}

const SERVER: Speaking = { id: null, status: "idle" };
export function useSpeaking(): Speaking {
  return useSyncExternalStore(subscribe, () => speaking, () => SERVER);
}
export function isApproximated(): boolean {
  return approximatedNow;
}

/** Voices arrive a moment after load in Chrome; this lets a component re-render when they do. */
export function useVoicesReady(): boolean {
  return useSyncExternalStore(
    (l) => {
      if (!isSupported()) return () => {};
      window.speechSynthesis.addEventListener("voiceschanged", l);
      return () => window.speechSynthesis.removeEventListener("voiceschanged", l);
    },
    () => isSupported() && window.speechSynthesis.getVoices().length > 0,
    () => false,
  );
}

// ---- saved choice ------------------------------------------------------------------------------------------

const PREFS_EVENT = "vantage:voice";
let cached: { raw: string | null; prefs: Prefs } | null = null;

function readPrefs(): Prefs {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(PREFS_KEY);
  } catch {}
  if (cached && cached.raw === raw) return cached.prefs; // same object each time, as useSyncExternalStore requires
  let prefs = DEFAULT_PREFS;
  try {
    const parsed = raw ? (JSON.parse(raw) as Partial<Prefs>) : {};
    prefs = {
      gender: parsed.gender === "male" ? "male" : "female",
      rate: (RATES as readonly number[]).includes(parsed.rate ?? 0) ? (parsed.rate as number) : 1,
    };
  } catch {}
  cached = { raw, prefs };
  return prefs;
}

export function setPrefs(next: Partial<Prefs>) {
  const merged = { ...readPrefs(), ...next };
  try {
    window.localStorage.setItem(PREFS_KEY, JSON.stringify(merged));
  } catch {}
  cached = null;
  window.dispatchEvent(new Event(PREFS_EVENT));
  return merged;
}

export function usePrefs(): Prefs {
  return useSyncExternalStore(
    (l) => {
      window.addEventListener(PREFS_EVENT, l);
      window.addEventListener("storage", l);
      return () => {
        window.removeEventListener(PREFS_EVENT, l);
        window.removeEventListener("storage", l);
      };
    },
    readPrefs,
    () => DEFAULT_PREFS,
  );
}
