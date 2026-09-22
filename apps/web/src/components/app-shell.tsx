"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useOnline } from "@/lib/hooks";
import type { Profile } from "@/lib/types";
import { BookmarkIcon, CareerIcon, CompassIcon, FeedIcon, GamesIcon, Logo, SearchIcon, UserIcon } from "./icons";
import { GamePicker } from "./games/game-picker";
import { OPEN_QUIZ_EVENT, useMultiTap } from "@/lib/triple-tap";
import { PartnerBadge } from "./partner-badge";
import { SearchPalette } from "./search-palette";
import { Skeleton, cx } from "./ui";

// The game is only downloaded when someone opens it.
const QuizGame = dynamic(() => import("./quiz-game").then((m) => m.QuizGame), { ssr: false });

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

export function AppShell({ profile, children }: { profile: Profile | null; children: ReactNode }) {
  const pathname = usePathname();
  const online = useOnline();
  const [searching, setSearching] = useState(false);
  const [quiz, setQuiz] = useState(false);
  const [picker, setPicker] = useState(false);
  const openQuiz = useCallback(() => setQuiz(true), []);
  const openPicker = useCallback(() => setPicker(true), []);
  const onLogo = useMultiTap(openPicker); // tap the logo three times, opens the games picker
  const launchGame = useCallback((id: string) => {
    if (id === "pop-quiz") setQuiz(true);
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
          <p className="text-muted">You&apos;re reading as</p>
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
          <button
            onClick={() => setSearching(true)}
            aria-label="Search"
            className="-mr-2 ml-auto flex size-11 items-center justify-center rounded-full text-muted hover:text-ink"
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
    </div>
  );
}
