"use client";

import type { ComponentType, SVGProps } from "react";
import { GamesIcon, LightningIcon, LinkIcon, WordIcon } from "../icons";

export interface GameDef {
  id: string;
  name: string;
  tagline: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
}

/** Every mini-game lives here. Add one row to grow the picker and the Games page together. */
export const GAMES: GameDef[] = [
  { id: "pop-quiz", name: "Pop quiz", tagline: "How well do you know your field? Runs until three wrong answers.", Icon: GamesIcon },
  { id: "speed-round", name: "Speed Round", tagline: "One minute on the clock. How many can you get right?", Icon: LightningIcon },
  { id: "match-field", name: "Match the Field", tagline: "One minute on the clock. How many companies can you match to their industry?", Icon: LinkIcon },
  { id: "word-drop", name: "Word Drop", tagline: "Guess a real skill or tool in six tries.", Icon: WordIcon },
];

/** The tile grid used by both the Games page and the triple-tap picker. */
export function GameTiles({ onSelect }: { onSelect: (id: string) => void }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {GAMES.map((g) => (
        <li key={g.id}>
          <button
            onClick={() => onSelect(g.id)}
            aria-label={g.name}
            className="btn-raised flex min-h-24 w-full flex-col items-start gap-2 rounded-xl p-4 text-left"
          >
            <g.Icon width={22} height={22} className="text-accent" />
            <span className="font-display text-lg leading-none">{g.name}</span>
            <span className="text-sm text-muted">{g.tagline}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
