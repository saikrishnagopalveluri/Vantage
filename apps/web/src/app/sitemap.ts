import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Only the pages that render real content without a signed-in profile. Everything under the app
// shell (feed, explore, career, games, profile, saved) needs a device/account id from localStorage
// to show anything, so a crawler would only ever see an empty splash screen there — see robots.ts.
export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: SITE_URL, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/onboarding`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE_URL}/login`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];
}
