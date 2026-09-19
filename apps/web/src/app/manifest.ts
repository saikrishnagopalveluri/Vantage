import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Vantage: career & industry intelligence",
    short_name: "Vantage",
    description: "Technology, career and industry news, ranked for you, with why it matters.",
    start_url: "/feed",
    scope: "/",
    display: "standalone",
    display_override: ["standalone", "minimal-ui"],
    background_color: "#f6f2ea",
    theme_color: "#f6f2ea",
    categories: ["business", "education", "productivity"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "My feed", url: "/feed", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
      { name: "Skill gaps", url: "/career", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
      { name: "Saved", url: "/saved", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
