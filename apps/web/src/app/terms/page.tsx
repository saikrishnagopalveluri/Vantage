"use client";

import Link from "next/link";
import { Contact, LegalLayout, List, P, Section } from "@/components/legal-layout";
import type { LegalInfo } from "@/lib/types";

const TOC: [string, string][] = [
  ["about", "About these terms"],
  ["who", "Who can use Vantage"],
  ["account", "Your account, or a guest profile"],
  ["rules", "What you can and can't do"],
  ["content", "News, data and other people's content"],
  ["guidance", "Information, not advice"],
  ["yours", "What you put in"],
  ["changes", "Changes and availability"],
  ["ending", "Ending things"],
  ["liability", "Liability"],
  ["law", "Governing law"],
  ["contact", "Contact"],
];

const who = (info: LegalInfo) => info.operator_name ?? "the person running this copy of Vantage";

export default function TermsPage() {
  return (
    <LegalLayout title="Terms of Use" version={(i) => i.terms_version} toc={TOC}>
      {(info) => (
        <>
          <Section id="about" title="About these terms">
            <P>
              These terms are the agreement between you and {who(info)} (&quot;we&quot;) about using Vantage. Vantage is a website and app that
              ranks business and tech news for your career and compares what jobs ask for with what you can do. When you create an account, or
              use Vantage as a guest, you agree to these terms. If you don&apos;t agree, please don&apos;t use it.
            </P>
            <P>
              Our <Link href="/privacy" className="font-semibold text-accent underline underline-offset-4">Privacy Policy</Link> explains what we do
              with your data. It is part of the deal, so please read it too.
            </P>
          </Section>

          <Section id="who" title="Who can use Vantage">
            <P>You must be 18 or older. If you are under 18 you can&apos;t create an account or use the app, and we ask you to confirm your age when you start.</P>
            <P>You must also be able to make a binding agreement where you live, and not be barred from using the service by any law that applies to you.</P>
          </Section>

          <Section id="account" title="Your account, or a guest profile">
            <List
              items={[
                "Give a real email address that is yours, and keep it up to date.",
                "Keep your password to yourself. One account is for one person. Tell us quickly if you think someone else has it.",
                "You are responsible for what happens under your account, unless it happened because of something we did wrong.",
                "A guest profile lives only in your browser on one device. If you clear your browser data or reset the device, it is gone, and we can't get it back.",
              ]}
            />
          </Section>

          <Section id="rules" title="What you can and can't do">
            <P>Use Vantage for yourself, for your own career research. Please don&apos;t:</P>
            <List
              items={[
                "copy the site's data in bulk, scrape it, or resell it;",
                "try to break in, probe for weaknesses, overload the service or get around its limits;",
                "use someone else's account, or pretend to be someone you are not;",
                "paste in a job description you have no right to use, or put other people's private details into one;",
                "upload anything unlawful, or use the app to harass or mislead anyone.",
              ]}
            />
          </Section>

          <Section id="content" title="News, data and other people's content">
            <List
              items={[
                "Every news story belongs to its publisher. We show a headline, a short excerpt and a summary picked from the publisher's own feed text, and we always link to the original. Read the full story on the publisher's site.",
                "Job titles, tools and skills include information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration, used under the CC BY 4.0 license. O*NET is a trademark of USDOL/ETA.",
                "Company names come from SEC EDGAR, the NSE equity list and Wikidata. Company and product names belong to their owners, and their appearance here doesn't mean they endorse us or we endorse them.",
                "The Vantage software, design and our own written text belong to us or our licensors. These terms don't hand you any ownership of them.",
              ]}
            />
          </Section>

          <Section id="guidance" title="Information, not advice">
            <P>
              Vantage is here to help you think about your career. It is not career, financial, investment or legal advice, and we don&apos;t promise you
              a job, an interview or any other result.
            </P>
            <List
              items={[
                "Story ranking, the “why it matters” text and skill gaps come from fixed rules applied to your choices. They can be wrong or out of date.",
                "Skill lists for the roles we wrote by hand are starting points, not job postings. Imported lists describe typical US jobs. Check them against the real posting.",
                "Which companies hire for a role is worked out from industry and field, not from live openings.",
              ]}
            />
          </Section>

          <Section id="yours" title="What you put in">
            <P>
              You keep ownership of what you enter: your profile choices and any job descriptions you paste in. You give us permission to store and
              process it only to run Vantage for you, as the Privacy Policy describes, and for as long as you keep it here.
            </P>
            <P>You can download or delete all of it whenever you like from the Profile page.</P>
          </Section>

          <Section id="changes" title="Changes and availability">
            <P>
              We may add, change or remove features, and the service may be down now and then. We provide it as it is and try to keep it running, but we
              can&apos;t promise it will always be available or error free.
            </P>
            <P>
              We may update these terms. The version date at the top changes when we do. If a change matters to you, you can stop using Vantage and delete
              your data.
            </P>
          </Section>

          <Section id="ending" title="Ending things">
            <P>
              You can stop at any time and delete your account and data from the Profile page. We may suspend or close an account that breaks these terms
              or puts the service or other people at risk, and we will say why unless the law stops us.
            </P>
          </Section>

          <Section id="liability" title="Liability">
            <P>
              To the extent the law allows, we aren&apos;t liable for indirect or consequential loss, or for decisions you make based on what you read in
              Vantage. Nothing in these terms limits liability that the law doesn&apos;t allow us to limit, or any rights you have as a consumer.
            </P>
          </Section>

          <Section id="law" title="Governing law">
            <P>
              These terms are governed by the laws of India. Disputes go to the courts of India, without taking away any right you have to bring a claim
              in the place where you live.
            </P>
          </Section>

          <Section id="contact" title="Contact">
            <P>Questions about these terms, or want to tell us something is wrong? Write to us here.</P>
            <Contact info={info} />
          </Section>
        </>
      )}
    </LegalLayout>
  );
}
