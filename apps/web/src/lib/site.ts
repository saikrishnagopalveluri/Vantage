/** The site's own public URL, for anything that needs an absolute address — metadataBase, the
 * sitemap, JSON-LD. `NEXT_PUBLIC_SITE_URL` wins when set (a custom domain); otherwise Vercel's own
 * production URL env var, which is always the same across deploys, unlike the per-deployment
 * `VERCEL_URL`; falling back to localhost for `npm run dev`. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000");

export const SITE_NAME = "Vantage";
export const SITE_TAGLINE = "Career news that fits you";
export const SITE_DESCRIPTION =
  "Vantage reads business and tech news and tells you why each story matters for your job hunt or your job — ranked around the fields, roles, companies and skills you actually follow.";
