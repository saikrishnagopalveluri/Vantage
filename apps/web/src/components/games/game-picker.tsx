"use client";

import { Sheet } from "../sheet";
import { GameTiles } from "./game-tiles";

/** The triple-tap easter egg: a light picker over whatever page you're on. The Games nav page shows
 *  the same tiles inline, without this wrapper. */
export function GamePicker({ open, onClose, onLaunch }: { open: boolean; onClose: () => void; onLaunch: (id: string) => void }) {
  return (
    <Sheet open={open} onClose={onClose} title="Games">
      <GameTiles
        onSelect={(id) => {
          onClose();
          onLaunch(id);
        }}
      />
    </Sheet>
  );
}
