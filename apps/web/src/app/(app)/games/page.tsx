"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { GameTiles } from "@/components/games/game-tiles";
import { useProfile } from "@/components/profile-context";
import { PageHeader } from "@/components/ui";

const QuizGame = dynamic(() => import("@/components/quiz-game").then((m) => m.QuizGame), { ssr: false });
const SpeedRound = dynamic(() => import("@/components/speed-round").then((m) => m.SpeedRound), { ssr: false });
const MatchField = dynamic(() => import("@/components/match-field").then((m) => m.MatchField), { ssr: false });
const WordDrop = dynamic(() => import("@/components/word-drop").then((m) => m.WordDrop), { ssr: false });

export default function GamesPage() {
  const { profile } = useProfile();
  const [active, setActive] = useState<string | null>(null);

  return (
    <div>
      <PageHeader title="Games" subtitle="Quick breaks between stories, built from the same fields, roles and companies you follow." />
      <GameTiles onSelect={setActive} />
      {active === "pop-quiz" && <QuizGame userId={profile.user_id} onClose={() => setActive(null)} />}
      {active === "speed-round" && <SpeedRound userId={profile.user_id} onClose={() => setActive(null)} />}
      {active === "match-field" && <MatchField onClose={() => setActive(null)} />}
      {active === "word-drop" && <WordDrop onClose={() => setActive(null)} />}
    </div>
  );
}
