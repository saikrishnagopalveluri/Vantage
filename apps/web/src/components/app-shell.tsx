"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { useOnline } from "@/lib/hooks";
import type { Profile, Streak } from "@/lib/types";
import { BookmarkIcon, CareerIcon, CompassIcon, FeedIcon, FlameIcon, GamesIcon, Logo, SearchIcon, UserIcon } from "./icons";
import { GamePicker } from "./games/game-picker";
import { OPEN_QUIZ_EVENT, useMultiTap } from "@/lib/triple-tap";
import { PartnerBadge } from "./partner-badge";
import { SearchPalette } from "./search-palette";
import { Skeleton, cx } from "./ui";

// Each game is only downloaded when someone opens it.
const QuizGame = dynamic(() => import("./quiz-game").then((m) => m.QuizGame), { ssr: false });
const SpeedRound = dynamic(() => import("./speed-round").then((m) => m.SpeedRound), { ssr: false });
const MatchField = dynamic(() => import("./match-field").then((m) => m.MatchField), { ssr: false });
const WordDrop = dynamic(() => import("./word-drop").then((m) => m.WordDrop), { ssr: false });
const ConnectDots = dynamic(() => import("./connect-dots").then((m) => m.ConnectDots), { ssr: false });

const NAV = [
  { href: "/feed", label: "Feed", Icon: FeedIcon },
  { href: "/explore", label: "Explore", Icon: CompassIcon },
  { href: "/career", label: "Skill gaps", Icon: CareerIcon },
  { href: "/games", label: "Games", Icon: GamesIcon },
  { href: "/saved", label: "Saved", Icon: BookmarkIcon },
  { href: "/profile", label: "Profile", Icon: UserIcon },
];

function statusLine(profile: Profile): string {
  if (profile.profile_status === "placed" && profile.current_company) {
    return `${profile.current_role?.title ?? "Working"} at ${profile.current_company.name}`;
  }
  return profile.target_roles[0] ? `Aiming for ${profile.target_roles[0].title}` : "Still exploring";
}

/** A day counted today shows warm; a streak that hasn't been touched yet today still shows the count,
 *  just in a quieter color, so it doesn't read as already lost. */
function StreakBadge({ streak, className }: { streak: Streak; className?: string }) {
  if (streak.current_streak === 0) return null;
  const label = `${streak.current_streak} day${streak.current_streak === 1 ? "" : "s"} in a row${streak.longest_streak > streak.current_streak ? `, best ${streak.longest_streak}` : ""}`;
  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      className={cx("inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-xs font-semibold", streak.active_today ? "text-accent" : "text-muted", className)}
    >
      <FlameIcon width={14} height={14} />
      <span aria-hidden data-testid="streak-count">{streak.current_streak}</span>
    </span>
  );
}

export function AppShell({ profile, children }: { profile: Profile | null; children: ReactNode }) {
  const pathname = usePathname();
  const online = useOnline();
  const [searching, setSearching] = useState(false);
  const [quiz, setQuiz] = useState(false);
  const [speedRound, setSpeedRound] = useState(false);
  const [matchField, setMatchField] = useState(false);
  const [wordDrop, setWordDrop] = useState(false);
  const [connectDots, setConnectDots] = useState(false);
  const [picker, setPicker] = useState(false);
  const [streak, setStreak] = useState<Streak | null>(null);
  const openQuiz = useCallback(() => setQuiz(true), []);
  const openPicker = useCallback(() => setPicker(true), []);
  const onLogo = useMultiTap(openPicker); // tap the logo three times, opens the games picker
  const launchGame = useCallback((id: string) => {
    if (id === "pop-quiz") setQuiz(true);
    if (id === "speed-round") setSpeedRound(true);
    if (id === "match-field") setMatchField(true);
    if (id === "word-drop") setWordDrop(true);
    if (id === "connect-dots") setConnectDots(true);
  }, []);
  const active = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setSearching(true);
      }
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_QUIZ_EVENT, openQuiz);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_QUIZ_EVENT, openQuiz);
    };
  }, [openQuiz]);

  // Opening the app at all counts as today's visit. A repeat touch the same day is a no-op on the
  // server, so this doesn't need to be more careful than "once profile is known".
  useEffect(() => {
    if (!profile) return;
    let cancelled = false;
    api
      .touchStreak(profile.user_id)
      .then((s) => {
        if (!cancelled) setStreak(s);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [profile]);

  return (
    <div className="min-h-dvh md:pl-64">
      {/* Desktop and tablet sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-line bg-paper px-4 py-6 md:flex">
        <Link href="/feed" onClick={onLogo} className="mb-6 flex touch-manipulation select-none items-center gap-3 px-2">
          <Logo size={32} />
          <span className="font-display text-2xl">Vantage</span>
        </Link>
        <button
          onClick={() => setSearching(true)}
          className="btn-raised mb-4 flex min-h-11 items-center gap-2.5 rounded-xl px-3 text-left text-[15px] text-muted"
        >
          <SearchIcon width={18} height={18} />
          <span className="flex-1">Search</span>
          <kbd className="rounded border border-line px-1.5 font-mono text-[11px]">/</kbd>
        </button>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {NAV.map(({ href, label, Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={active(href) ? "page" : undefined}
              className={cx(
                "flex min-h-11 items-center gap-3 rounded-xl px-3 text-[15px] font-semibold transition-colors",
                active(href) ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface hover:text-ink",
              )}
            >
              <Icon />
              {label}
            </Link>
          ))}
        </nav>
        <div className="raised mt-auto rounded-xl p-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <p className="text-muted">You&apos;re reading as</p>
            {streak && <StreakBadge streak={streak} />}
          </div>
          {profile ? (
            <p className="mt-0.5 font-semibold leading-snug">{statusLine(profile)}</p>
          ) : (
            <div className="mt-1.5" aria-hidden>
              <Skeleton className="h-4 w-36" />
            </div>
          )}
        </div>
        <PartnerBadge size="sm" className="mt-4 px-1" />
      </aside>

      {/* Mobile top bar */}
      <header className="pt-safe sticky top-0 z-30 border-b border-line bg-paper md:hidden">
        <div className="px-safe flex h-12 items-center gap-2.5">
          <Link href="/feed" onClick={onLogo} aria-label="Vantage home" className="flex touch-manipulation select-none items-center gap-2.5">
            <Logo size={26} />
            <span className="font-display text-xl">Vantage</span>
          </Link>
          {streak && <StreakBadge streak={streak} className="ml-auto" />}
          <button
            onClick={() => setSearching(true)}
            aria-label="Search"
            className={cx("-mr-2 flex size-11 items-center justify-center rounded-full text-muted hover:text-ink", !streak && "ml-auto")}
          >
            <SearchIcon />
          </button>
        </div>
      </header>

      {!online && (
        <div role="status" className="border-b border-line bg-accent-soft px-4 py-2 text-center text-sm text-accent">
          You&apos;re offline. This is what was on your device the last time you were connected.
        </div>
      )}

      <main className="px-safe mx-auto w-full max-w-5xl pb-[calc(6rem+env(safe-area-inset-bottom))] pt-4 md:px-8 md:pb-16 md:pt-8">
        {children}
      </main>

      {/* Mobile bottom tabs */}
      <nav
        aria-label="Main"
        className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-paper md:hidden"
      >
        <ul className="grid grid-cols-6">
          {NAV.map(({ href, label, Icon }) => (
            <li key={href}>
              <Link
                href={href}
                aria-current={active(href) ? "page" : undefined}
                className={cx(
                  "flex min-h-16 flex-col items-center justify-center gap-1 text-[11px] font-semibold transition-colors",
                  active(href) ? "text-accent" : "text-muted",
                )}
              >
                <Icon />
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <SearchPalette open={searching} onClose={() => setSearching(false)} />
      <GamePicker open={picker} onClose={() => setPicker(false)} onLaunch={launchGame} />
      {quiz && profile && <QuizGame userId={profile.user_id} onClose={() => setQuiz(false)} />}
      {speedRound && profile && <SpeedRound userId={profile.user_id} onClose={() => setSpeedRound(false)} />}
      {matchField && <MatchField onClose={() => setMatchField(false)} />}
      {wordDrop && <WordDrop onClose={() => setWordDrop(false)} />}
      {connectDots && <ConnectDots onClose={() => setConnectDots(false)} />}
    </div>
  );
}
