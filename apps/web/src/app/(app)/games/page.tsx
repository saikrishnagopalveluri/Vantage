"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { GameTiles } from "@/components/games/game-tiles";
import { useProfile } from "@/components/profile-context";
import { PageHeader } from "@/components/ui";

const QuizGame = dynamic(() => import("@/components/quiz-game").then((m) => m.QuizGame), { ssr: false });

export default function GamesPage() {
  const { profile } = useProfile();
  const [active, setActive] = useState<string | null>(null);

  return (
    <div>
      <PageHeader title="Games" subtitle="Quick breaks between stories, built from the same fields, roles and companies you follow." />
      <GameTiles onSelect={setActive} />
      {active === "pop-quiz" && <QuizGame userId={profile.user_id} onClose={() => setActive(null)} />}
    </div>
  );
}
