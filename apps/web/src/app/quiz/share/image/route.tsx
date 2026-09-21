import { ImageResponse } from "next/og";
import { RANKS, parseResult } from "@/lib/quiz";

// The preview picture LinkedIn, X and WhatsApp show for a shared score. Numbers are clamped and the title comes from a fixed list.
// The renderer wants every element to say how it lays out its children, so each one below is a flex box.
const COLOR = { paper: "#f6f2ea", surface: "#fffdf8", ink: "#1d1a16", muted: "#625a4f", line: "#e4dccd", accent: "#a94d08" };
const box = { display: "flex" } as const;
const column = { display: "flex", flexDirection: "column" } as const;

export function GET(request: Request) {
  const r = parseResult(Object.fromEntries(new URL(request.url).searchParams));
  const stat = (value: number, label: string) => (
    <div style={{ ...column, alignItems: "center", flex: 1, background: COLOR.paper, borderRadius: 20, padding: "22px 0" }}>
      <div style={{ ...box, fontSize: 60, fontWeight: 700, color: COLOR.ink }}>{String(value)}</div>
      <div style={{ ...box, fontSize: 24, color: COLOR.muted }}>{label}</div>
    </div>
  );
  return new ImageResponse(
    (
      <div style={{ ...box, width: "100%", height: "100%", background: COLOR.paper, padding: 36 }}>
        <div style={{ ...column, flex: 1, background: COLOR.surface, border: `2px solid ${COLOR.line}`, borderRadius: 32, padding: "36px 56px" }}>
          <div style={{ ...box, justifyContent: "space-between", alignItems: "center", borderBottom: `2px solid ${COLOR.line}`, paddingBottom: 18 }}>
            <div style={{ ...box, fontSize: 42, fontWeight: 700, color: COLOR.ink }}>Vantage</div>
            <div style={{ ...box, fontSize: 24, letterSpacing: 5, color: COLOR.accent }}>POP QUIZ</div>
          </div>
          <div style={{ ...box, flex: 1, alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ ...column }}>
              <div style={{ ...box, fontSize: 24, letterSpacing: 4, color: COLOR.muted }}>SCORE</div>
              <div style={{ ...box, fontSize: 150, fontWeight: 700, color: COLOR.ink, lineHeight: 1.05 }}>{r.score.toLocaleString("en-IN")}</div>
              <div style={{ ...box, fontSize: 30, color: COLOR.accent, fontWeight: 700 }}>{RANKS[r.rank].title}</div>
            </div>
            <div style={{ ...column, gap: 14, width: 250 }}>
              {stat(r.correct, "right")}
              {stat(r.bestStreak, "best streak")}
            </div>
          </div>
          <div style={{ ...column, alignItems: "center", color: COLOR.muted }}>
            <div style={{ ...box, fontSize: 28 }}>Think you can beat it?</div>
            <div style={{ ...box, fontSize: 20, marginTop: 4 }}>Powered by DOT Club, IBS Hyderabad</div>
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
