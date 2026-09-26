import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Vantage — career news that fits you";

const COLOR = { paper: "#f6f2ea", surface: "#fffdf8", ink: "#1d1a16", muted: "#625a4f", line: "#e4dccd", accent: "#a94d08" };
const box = { display: "flex" } as const;
const column = { display: "flex", flexDirection: "column" } as const;

export default function Image() {
  return new ImageResponse(
    (
      <div style={{ ...box, width: "100%", height: "100%", background: COLOR.paper, padding: 40 }}>
        <div
          style={{
            ...column,
            flex: 1,
            justifyContent: "center",
            background: COLOR.surface,
            border: `2px solid ${COLOR.line}`,
            borderRadius: 32,
            padding: "0 72px",
          }}
        >
          <div style={{ ...box, fontSize: 26, letterSpacing: 5, color: COLOR.accent, fontWeight: 700 }}>VANTAGE</div>
          <div style={{ ...box, fontSize: 76, fontWeight: 700, color: COLOR.ink, marginTop: 18, lineHeight: 1.08 }}>Career news that fits you.</div>
          <div style={{ ...box, fontSize: 32, color: COLOR.muted, marginTop: 28, maxWidth: 820 }}>
            Business and tech news, ranked around your fields, roles, companies and skills.
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
