import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Everything under the app shell needs a signed-in/guest identity from localStorage to render
// anything real, so there is no point letting a crawler spend budget on an empty splash screen
// there (see sitemap.ts) — same for the API proxy and the private data-export/quiz-share-image
// routes. AI answer-engine crawlers are explicitly allowed, not just left to the default: the
// whole point of being indexed by them is to be citable in an AI Overview/Perplexity/ChatGPT answer.
const DISALLOW = ["/api/", "/feed", "/explore", "/career", "/games", "/profile", "/saved", "/quiz/share"];

const AI_CRAWLERS = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-Web", "anthropic-ai", "PerplexityBot", "Google-Extended", "Applebot-Extended"];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: DISALLOW }, ...AI_CRAWLERS.map((userAgent) => ({ userAgent, allow: "/", disallow: DISALLOW }))],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
