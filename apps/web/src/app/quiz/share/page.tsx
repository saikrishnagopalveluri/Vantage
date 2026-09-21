import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { PartnerBadge } from "@/components/partner-badge";
import { RANKS, parseResult, resultQuery } from "@/lib/quiz";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

/** The address people land on from a shared post. Everything on it comes from a few numbers in the link, clamped and printed as text. */
export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const r = parseResult(await searchParams);
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto")?.split(",")[0].trim() ?? (host.startsWith("localhost") ? "http" : "https");
  const title = `${r.score.toLocaleString("en-IN")} points on the Vantage pop quiz`;
  const description = `${r.correct} right, a best streak of ${r.bestStreak} and the title of ${RANKS[r.rank].title}. Think you can beat that?`;
  const image = `/quiz/share/image?${resultQuery(r)}`;
  return {
    metadataBase: new URL(`${proto}://${host}`),
    title,
    description,
    robots: { index: false, follow: false },
    openGraph: { title, description, type: "website", siteName: "Vantage", images: [{ url: image, width: 1200, height: 630, alt: title }] },
    twitter: { card: "summary_large_image", title, description, images: [image] },
  };
}

export default async function SharedResult({ searchParams }: Props) {
  const r = parseResult(await searchParams);
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-xl flex-col justify-center px-4 py-10">
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-accent">Vantage pop quiz</p>
      <h1 className="mt-2 font-display text-[34px] leading-[1.1]">
        Someone scored {r.score.toLocaleString("en-IN")}. Can you beat it?
      </h1>
      <section aria-label="The result" className="raised mt-6 rounded-2xl p-6 text-center">
        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Title</p>
        <p className="mt-1 font-display text-4xl text-accent">{RANKS[r.rank].title}</p>
        <p className="mt-5 font-display text-7xl tabular-nums">{r.score.toLocaleString("en-IN")}</p>
        <p className="text-muted">points</p>
        <dl className="mt-6 grid grid-cols-3 gap-2 text-center">
          {[
            [r.correct, "right"],
            [r.bestStreak, "best streak"],
            [r.level, "level reached"],
          ].map(([value, label]) => (
            <div key={String(label)} className="rounded-xl bg-sunken px-2 py-3">
              <dd className="font-display text-2xl">{value}</dd>
              <dt className="text-sm text-muted">{label}</dt>
            </div>
          ))}
        </dl>
      </section>
      <p className="mt-6 text-[17px] leading-relaxed text-muted">
        Vantage is a news feed for management students and early careers, ranked around your fields, roles and companies. The pop quiz asks
        questions from your own world and keeps going until you get three wrong.
      </p>
      <Link href="/" className="btn-primary mt-6 inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-[15px] font-semibold">
        Try Vantage
      </Link>
      <PartnerBadge size="sm" className="mt-8 border-t border-line pt-5" />
    </main>
  );
}
