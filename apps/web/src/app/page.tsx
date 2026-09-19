"use client";

import Link from "next/link";
import { ArrowIcon, ExternalIcon, Logo } from "@/components/icons";
import { RolePeek } from "@/components/role-peek";
import { LinkButton, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { DomainBadge } from "@/lib/domains";
import { timeAgo } from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import { useDeletedNotice, useUserId } from "@/lib/session";
import type { Pulse } from "@/lib/types";

const STEPS = [
  {
    title: "Tell us where you are",
    body: "A management student getting ready for placements, or someone already in a job. Pick up to four fields, the roles you want and the companies you are watching. We list the roles, skills and recruiters that business-school students go for first.",
  },
  {
    title: "We read the news for you",
    body: "About 90 official news feeds, every hour. A story is kept only when it names something in our lists of roles, companies, skills and topics, so nothing is guessed.",
  },
  {
    title: "You get a reason, not just a headline",
    body: "Each story comes with one plain sentence on why it matters to you and a small next step. A separate view compares what employers ask for with what you can already do.",
  },
];

const CARE = [
  {
    title: "Rules, not a chatbot",
    body: "Tagging is rule-based. If a story does not say it, we do not tag it. Two outlets covering the same story show up once.",
  },
  {
    title: "Honest about what is placeholder",
    body: "Skill lists for our hand-written roles are starting points, not job-posting data. Paste real job descriptions to check them against the postings you care about.",
  },
  {
    title: "Light on your data",
    body: "We keep headlines, links and short excerpts, and always link to the publisher. An account is an email and a salted password hash, plus the fields, roles and companies you pick. There are no ads and no tracking scripts.",
  },
];

const FAQ = [
  {
    q: "Do I need an account?",
    a: "No. You can try Vantage as a guest. A guest profile lives only on that device, so an account is what lets you keep it safe and use it on another phone or laptop.",
  },
  {
    q: "Where does the news come from?",
    a: "Official RSS feeds from publishers such as Mint, Economic Times, Marketing Dive, Fierce Healthcare and Nature. Every story links back to the publisher.",
  },
  {
    q: "Where do the roles and companies come from?",
    a: "Job titles, tools and skills are from O*NET, a US Department of Labor database. Companies are from SEC filings, the NSE list and Wikidata. We also wrote a few hundred roles and companies by hand, including the ones from our course handouts.",
  },
  {
    q: "Why does a story rank where it does?",
    a: "Scoring is a set of visible rules: your target companies, your field, your role and the skills you are missing all add points, and older stories lose some. The card tells you which of those matched.",
  },
];

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="font-mono text-[26px] font-medium leading-none md:text-3xl">{value}</p>
      <p className="mt-1.5 text-sm text-muted">{label}</p>
    </div>
  );
}

function PulseCard({ pulse, loading }: { pulse: Pulse | undefined; loading: boolean }) {
  const n = (v: number) => v.toLocaleString();
  return (
    <div className="raised rounded-2xl p-5 md:p-6" aria-busy={loading}>
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent">Right now</p>
        {pulse?.updated_at && <p className="text-xs text-muted">Feeds checked {timeAgo(pulse.updated_at)}</p>}
      </div>

      {!pulse ? (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : (
        <>
          <div className="mt-4 grid grid-cols-3 gap-3">
            <Stat value={n(pulse.stories_today)} label="stories in the last day" />
            <Stat value={n(pulse.job_titles)} label="job titles" />
            <Stat value={n(pulse.companies)} label="companies" />
          </div>

          {pulse.headlines.length > 0 && (
            <>
              <h2 className="mt-5 font-display text-lg">Fresh from the feeds</h2>
              <ul className="mt-1 divide-y divide-line">
                {pulse.headlines.map((h) => (
                  <li key={h.url}>
                    <a
                      href={h.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start justify-between gap-3 py-3 hover:text-accent"
                    >
                      <span className="min-w-0">
                        <span className="block text-[15px] font-semibold leading-snug">{h.title}</span>
                        <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                          {h.field && <DomainBadge name={h.field} />}
                          {h.source} · {timeAgo(h.published_at)}
                        </span>
                      </span>
                      <ExternalIcon width={14} height={14} className="mt-1 shrink-0 opacity-50" />
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}

export default function Home() {
  const userId = useUserId();
  const signedIn = Boolean(userId);
  const [deleted, dismissDeleted] = useDeletedNotice();
  const { data: pulse, loading } = useAsync((signal) => api.pulse(signal), "pulse");

  return (
    <div className="min-h-dvh">
      <header className="pt-safe sticky top-0 z-30 border-b border-line bg-paper/90 backdrop-blur">
        <div className="px-safe mx-auto flex h-14 w-full max-w-5xl items-center gap-2 md:px-8">
          <Link href="/" className="flex items-center gap-2.5" aria-label="Vantage home">
            <Logo size={28} />
            <span className="font-display text-xl">Vantage</span>
          </Link>
          <nav aria-label="Site" className="ml-auto flex items-center gap-1">
            <a href="#about" className="hidden min-h-11 items-center rounded-lg px-3 text-[15px] font-semibold text-muted hover:text-ink sm:inline-flex">
              About
            </a>
            {signedIn ? (
              <LinkButton href="/feed" variant="primary" className="min-h-10 px-4">
                Open your feed
              </LinkButton>
            ) : (
              <>
                <Link href="/login" className="inline-flex min-h-11 items-center rounded-lg px-3 text-[15px] font-semibold text-muted hover:text-ink">
                  Log in
                </Link>
                <LinkButton href="/login?mode=signup" variant="primary" className="min-h-10 px-4">
                  Get started
                </LinkButton>
              </>
            )}
          </nav>
        </div>
      </header>

      {deleted && (
        <div role="status" className="border-b border-line bg-accent-soft px-4 py-3 text-center text-[15px] text-accent">
          Your account and data have been deleted.{" "}
          <button onClick={dismissDeleted} className="ml-1 min-h-11 font-semibold underline underline-offset-4">
            Dismiss
          </button>
        </div>
      )}

      <main className="px-safe mx-auto w-full max-w-5xl md:px-8">
        <section className="grid gap-8 py-10 md:py-16 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
          <div className="rise">
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">For management students first, and people already working</p>
            <h1 className="mt-3 font-display text-[40px] leading-[1.04] md:text-[58px]">Career news that fits you.</h1>
            <p className="mt-4 max-w-lg text-[17px] leading-relaxed text-muted">
              Vantage reads business and tech news, then tells you why each story matters for your job hunt or your job. It is built first for MBA and PGDM
              students getting ready for placements.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              {signedIn ? (
                <LinkButton href="/feed" variant="primary" className="px-5">
                  Open your feed <ArrowIcon width={16} height={16} />
                </LinkButton>
              ) : (
                <>
                  <LinkButton href="/login?mode=signup" variant="primary" className="px-5">
                    Create your account <ArrowIcon width={16} height={16} />
                  </LinkButton>
                  <LinkButton href="/onboarding">Try it as a guest</LinkButton>
                </>
              )}
            </div>
            <p className="mt-4 text-sm text-muted">
              {signedIn ? (
                "You are signed in on this device."
              ) : (
                <>
                  Already have an account?{" "}
                  <Link href="/login" className="font-semibold text-accent underline underline-offset-4">
                    Log in
                  </Link>
                </>
              )}
            </p>
          </div>

          <div className="rise" style={{ "--n": 2 } as React.CSSProperties}>
            <PulseCard pulse={pulse} loading={loading} />
          </div>
        </section>

        <section aria-label="Try it" className="pb-12 md:pb-16">
          <div className="max-w-2xl">
            <RolePeek />
          </div>
        </section>

        <section id="about" aria-labelledby="about-title" className="scroll-mt-20 border-t border-line py-12 md:py-16">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted">About</p>
          <h2 id="about-title" className="mt-2 max-w-2xl font-display text-[30px] leading-[1.1] md:text-[40px]">
            A news feed built around your next move
          </h2>
          <p className="mt-4 max-w-2xl text-[17px] leading-relaxed">
            Most news apps show everyone the same front page. Vantage checks each story against the fields, roles, companies and skills you
            care about, ranks it, and writes one sentence on why it matters to you. It started as a tool for MBA and PGDM students getting
            ready for placements, so roles like associate brand manager, consultant, investment banking associate and management trainee, and the
            firms that recruit for them, come first. It works just as well once you have a job.
          </p>

          <ol className="mt-8 grid gap-4 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="raised rounded-2xl p-5">
                <span className="font-mono text-sm text-accent">{i + 1}</span>
                <h3 className="mt-2 font-display text-xl leading-snug">{s.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-muted">{s.body}</p>
              </li>
            ))}
          </ol>

          <h3 className="mt-12 font-display text-2xl">What we are careful about</h3>
          <div className="mt-4 grid gap-6 md:grid-cols-3">
            {CARE.map((c) => (
              <div key={c.title}>
                <h4 className="font-semibold">{c.title}</h4>
                <p className="mt-1.5 text-[15px] leading-relaxed text-muted">{c.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section aria-labelledby="faq-title" className="border-t border-line py-12 md:py-16">
          <h2 id="faq-title" className="font-display text-[28px] leading-tight md:text-[34px]">
            Questions people ask
          </h2>
          <div className="mt-5 max-w-2xl divide-y divide-line border-y border-line">
            {FAQ.map((f) => (
              <details key={f.q} className="group py-1">
                <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 text-[16px] font-semibold marker:hidden [&::-webkit-details-marker]:hidden">
                  {f.q}
                  <span aria-hidden className="text-accent transition-transform duration-200 group-open:rotate-45">
                    +
                  </span>
                </summary>
                <p className="pb-4 pr-6 text-[15px] leading-relaxed text-muted">{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        {!signedIn && (
          <section aria-label="Get started" className="mb-12 rounded-3xl bg-accent-soft px-6 py-10 text-center md:mb-16 md:py-14">
            <h2 className="mx-auto max-w-xl font-display text-[28px] leading-tight md:text-[36px]">Two minutes to a feed that knows your field</h2>
            <p className="mx-auto mt-3 max-w-md text-[15px] text-muted">Pick your fields, a few roles and companies, and what you can already do.</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <LinkButton href="/login?mode=signup" variant="primary" className="px-5">
                Create your account
              </LinkButton>
              <LinkButton href="/onboarding">Try it as a guest</LinkButton>
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-line">
        <div className="px-safe mx-auto max-w-5xl space-y-2 py-8 text-sm text-muted md:px-8">
          <p>
            Job titles, tools and skills include information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and
            Training Administration, used under the CC BY 4.0 license. Company names come from SEC EDGAR, the NSE equity list and Wikidata.
          </p>
          <p>Every story belongs to its publisher. We show a headline and a short excerpt, and link to the original.</p>
          <p>
            <Link href="/terms" className="font-semibold text-accent underline underline-offset-4">
              Terms of Use
            </Link>
            {" · "}
            <Link href="/privacy" className="font-semibold text-accent underline underline-offset-4">
              Privacy Policy
            </Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
