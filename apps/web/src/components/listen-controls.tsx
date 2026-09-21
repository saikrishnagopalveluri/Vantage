"use client";

import { useEffect, useMemo } from "react";
import type { Brief } from "@/lib/types";
import {
  RATES,
  chunk,
  isSupported,
  pause,
  pickVoice,
  preview,
  restart,
  resume,
  scriptFor,
  setPrefs,
  speak,
  stop,
  stopIfPlaying,
  usePrefs,
  useSpeaking,
  useVoicesReady,
  upgradeTip,
  voiceOptions,
  voiceQuality,
  type Gender,
} from "@/lib/speech";
import { PauseIcon, SpeakerIcon, StopIcon } from "./icons";
import { Button, cx } from "./ui";

const GENDERS: { id: Gender; label: string }[] = [
  { id: "female", label: "Female" },
  { id: "male", label: "Male" },
];

/** Play, pause and stop for one story's summary and pointers, with a female or male voice. */
export function ListenControls({ id, title, brief }: { id: string; title: string; brief: Brief | null }) {
  const prefs = usePrefs();
  const now = useSpeaking();
  const voicesReady = useVoicesReady();
  const supported = isSupported();
  const mine = now.id === id;
  const status = mine ? now.status : "idle";

  // Stop reading when the summary is closed or the card goes away.
  useEffect(() => () => stopIfPlaying(id), [id]);

  const chosen = prefs.voices?.[prefs.gender];
  const voices = useMemo(() => (supported && voicesReady ? window.speechSynthesis.getVoices() : []), [supported, voicesReady]);
  const picked = useMemo(() => (voices.length ? pickVoice(voices, prefs.gender, chosen) : null), [voices, prefs.gender, chosen]);
  const options = useMemo(() => voiceOptions(voices, prefs.gender), [voices, prefs.gender]);
  // Worth a tip when the voice being used is one of the plain built-in ones.
  const basic = picked?.voice ? voiceQuality(picked.voice) === "basic" : false;

  if (!supported) {
    return <p className="text-sm text-muted">Listening isn&apos;t available in this browser. Try Chrome, Edge or Safari.</p>;
  }

  const play = () => {
    if (status === "playing") pause();
    else if (status === "paused") resume();
    else speak(id, chunk(scriptFor(title, brief)), prefs);
  };
  const choose = (next: Partial<typeof prefs>) => {
    const merged = setPrefs(next);
    if (mine) restart(merged);
  };
  const pickVoiceByName = (name: string) => choose({ voices: { [prefs.gender]: name || undefined } });

  const label = status === "playing" ? "Pause" : status === "paused" ? "Resume" : "Listen";

  return (
    <div className="space-y-2 border-b border-line pb-3.5">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Listen to this summary">
        <Button
          onClick={play}
          variant={status === "idle" ? "secondary" : "primary"}
          aria-label={status === "idle" ? "Listen to the summary and pointers" : label}
          className="px-3.5"
        >
          {status === "playing" ? <PauseIcon width={18} height={18} /> : <SpeakerIcon width={18} height={18} />}
          {label}
        </Button>
        {status !== "idle" && (
          <Button onClick={stop} variant="ghost" aria-label="Stop listening" className="px-3.5">
            <StopIcon width={16} height={16} />
            Stop
          </Button>
        )}
        <div role="group" aria-label="Voice" className="inline-flex rounded-xl border border-line bg-sunken p-0.5">
          {GENDERS.map((g) => (
            <button
              key={g.id}
              type="button"
              aria-pressed={prefs.gender === g.id}
              onClick={() => choose({ gender: g.id })}
              className={cx(
                "min-h-10 rounded-[10px] px-3 text-[15px] font-semibold transition-colors",
                prefs.gender === g.id ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink",
              )}
            >
              {g.label}
            </button>
          ))}
        </div>
        {(options.matching.length > 0 || options.other.length > 0) && (
          <label className="inline-flex max-w-full items-center gap-1.5 text-sm text-muted">
            Voice
            <select
              value={chosen && [...options.matching, ...options.other].some((o) => o.name === chosen) ? chosen : ""}
              onChange={(e) => pickVoiceByName(e.target.value)}
              className="min-h-10 max-w-[15rem] rounded-lg border border-line bg-surface px-2 text-[15px] text-ink"
            >
              <option value="">Best available</option>
              {options.matching.length > 0 && (
                <optgroup label={prefs.gender === "female" ? "Female voices" : "Male voices"}>
                  {options.matching.map((o) => (
                    <option key={o.name} value={o.name}>
                      {o.label}
                    </option>
                  ))}
                </optgroup>
              )}
              {options.other.length > 0 && (
                <optgroup label="Other voices">
                  {options.other.map((o) => (
                    <option key={o.name} value={o.name}>
                      {o.label}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          </label>
        )}
        <Button onClick={() => preview(prefs)} variant="ghost" aria-label="Hear a sample of this voice" className="px-3.5">
          <SpeakerIcon width={16} height={16} />
          Hear it
        </Button>
        <label className="inline-flex items-center gap-1.5 text-sm text-muted">
          Speed
          <select
            value={prefs.rate}
            onChange={(e) => choose({ rate: Number(e.target.value) })}
            className="min-h-10 rounded-lg border border-line bg-surface px-2 text-[15px] text-ink"
          >
            {RATES.map((r) => (
              <option key={r} value={r}>
                {r === 1 ? "Normal" : `${r}x`}
              </option>
            ))}
          </select>
        </label>
      </div>
      {picked && !picked.voice && <p className="text-sm text-muted">This device has no English voice installed, so it can&apos;t read aloud.</p>}
      {basic && <p className="text-sm text-muted">{upgradeTip(navigator.userAgent)}</p>}
      {picked?.voice && picked.approximated && (
        <p className="text-sm text-muted">
          This device has no {prefs.gender} English voice, so the closest one is used at a different pitch.
        </p>
      )}
      <p className="sr-only" role="status" aria-live="polite">
        {status === "playing" ? "Reading the summary." : status === "paused" ? "Paused." : ""}
      </p>
    </div>
  );
}
