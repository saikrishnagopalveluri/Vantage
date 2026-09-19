"use client";

import Link from "next/link";
import { Contact, LegalLayout, List, P, Section } from "@/components/legal-layout";
import type { LegalInfo } from "@/lib/types";

const TOC: [string, string][] = [
  ["who", "Who is responsible"],
  ["collect", "What we collect and why"],
  ["basis", "Our legal basis"],
  ["storage", "Cookies and browser storage"],
  ["sharing", "Who we share it with"],
  ["keep", "How long we keep it"],
  ["rights", "Your rights"],
  ["use-rights", "How to use your rights"],
  ["children", "Age limit"],
  ["automated", "Automated ranking"],
  ["security", "Security and breaches"],
  ["transfers", "Where data is stored"],
  ["changes", "Changes to this policy"],
  ["contact", "Contact and grievances"],
];

const who = (info: LegalInfo) => info.operator_name ?? "the person running this copy of Vantage";

export default function PrivacyPage() {
  return (
    <LegalLayout title="Privacy Policy" version={(i) => i.privacy_version} toc={TOC}>
      {(info) => (
        <>
          <P>
            This policy says what personal data Vantage keeps, why, and what you can do about it. It is written to meet India&apos;s Digital Personal
            Data Protection Act, 2023 (DPDP Act) and the EU and UK General Data Protection Regulation (GDPR). It is in English. Versions in Indian
            languages aren&apos;t available yet.
          </P>

          <Section id="who" title="Who is responsible">
            <P>
              {who(info)} decides why and how your data is used. That makes us the &quot;Data Fiduciary&quot; under the DPDP Act and the
              &quot;controller&quot; under the GDPR. You are the &quot;Data Principal&quot; or &quot;data subject&quot;. Contact details are at the
              bottom of this page.
            </P>
          </Section>

          <Section id="collect" title="What we collect and why">
            <P>We collect only what the app needs. Here is all of it:</P>
            <dl className="divide-y divide-line rounded-2xl border border-line">
              {(
                [
                  ["Account", "Your email address and a salted hash of your password (never the password itself), and when you signed up. To let you sign in and to keep your profile safe."],
                  ["Your agreement", "Which versions of the terms and this policy you agreed to, when, that you said you are 18 or older, and whether it was at sign-up or as a guest. As proof that you agreed."],
                  ["Your profile", "The fields you follow, roles and companies you want, skills and tools you have, whether you are job hunting or working, and your current role, company and industry if you gave them. To rank stories and work out your skill gaps."],
                  ["Story activity", "Which stories you save, hide or open, and when. To move similar stories up or down for you."],
                  ["Job descriptions", "The text you paste in, a title, any company or role you link, and the skills we found. To show what you are missing across the jobs you care about."],
                  ["Guest id", "If you use Vantage without an account, a random id kept in your browser stands in for your account. It holds no personal details."],
                  ["Technical data", "A session cookie if you have an account, and the usual server records of each request (your IP address, the time and the page asked for). To keep you signed in, keep the service secure and fix faults."],
                ] as [string, string][]
              ).map(([term, text]) => (
                <div key={term} className="grid gap-1 p-4 sm:grid-cols-[9rem_1fr] sm:gap-4">
                  <dt className="font-semibold">{term}</dt>
                  <dd className="text-[15px] leading-relaxed text-muted">{text}</dd>
                </div>
              ))}
            </dl>
            <P>
              We don&apos;t use advertising, analytics or tracking scripts. We don&apos;t collect your location, contacts, payment details or anything from
              your device beyond the above. Please don&apos;t put sensitive details, such as health, religion or other people&apos;s private information,
              into a job description or anywhere else. We don&apos;t need it.
            </P>
          </Section>

          <Section id="basis" title="Our legal basis">
            <List
              items={[
                <span key="a">
                  <strong>DPDP Act:</strong> your consent, which you give by ticking the box when you start, and which you can withdraw by deleting your
                  data. Some technical records are kept for security and legal reasons, which the Act allows as certain legitimate uses.
                </span>,
                <span key="b">
                  <strong>GDPR:</strong> to provide the service you asked for (Article 6(1)(b)), your consent for a guest profile and for the record of
                  your agreement (6(1)(a)), and our legitimate interest in keeping the service secure and preventing abuse (6(1)(f)).
                </span>,
              ]}
            />
          </Section>

          <Section id="storage" title="Cookies and browser storage">
            <List
              items={[
                "One cookie, vantage_session. It keeps you signed in, is set only if you have an account, lasts 30 days, and can't be read by page scripts.",
                "Browser storage on your device holds your user id, whether it is an account, and your light or dark theme choice.",
                "The app keeps a copy of your recent feed and profile on your device so it works offline. Logging out or resetting the device clears it.",
              ]}
            />
            <P>These are all strictly necessary for the app to work, so we don&apos;t show a cookie banner. There are no advertising or analytics cookies.</P>
          </Section>

          <Section id="sharing" title="Who we share it with">
            <P>We don&apos;t sell your data or share it for advertising. The app doesn&apos;t send your personal data to any third-party service.</P>
            <List
              items={[
                "The company that hosts the service handles the data for us and only on our instructions. Hosting is set up by whoever runs this copy of Vantage.",
                "When you click a story, you go to the publisher's own site, and their policy applies there.",
                "We may disclose data if a court or authority legally requires it, or to protect someone's safety or our legal rights.",
              ]}
            />
          </Section>

          <Section id="keep" title="How long we keep it">
            <P>
              We keep your data until you delete it. We don&apos;t yet delete inactive accounts automatically. When you delete your account, your
              profile, activity, job descriptions, agreement record and account are removed from the live database straight away. Backups, if any are kept,
              are overwritten on their normal cycle, and server request records are kept for the period the hosting set-up allows.
            </P>
          </Section>

          <Section id="rights" title="Your rights">
            <P>Under the DPDP Act you can:</P>
            <List
              items={[
                "get a summary of your personal data and how it is used;",
                "have inaccurate or incomplete data corrected and have data erased;",
                "withdraw your consent whenever you like;",
                "complain to us and get a reply, and then to the Data Protection Board of India if you are not satisfied;",
                "nominate another person to use these rights for you if you die or can't act.",
              ]}
            />
            <P>Under the GDPR you also have the right to:</P>
            <List
              items={[
                "access your data and receive a copy in a common format (portability);",
                "have it corrected or erased, or its use restricted;",
                "object to processing based on our legitimate interests;",
                "complain to the data protection authority in your country.",
              ]}
            />
          </Section>

          <Section id="use-rights" title="How to use your rights">
            <List
              items={[
                <span key="a">
                  <strong>Get a copy:</strong> Profile, then Your data, then Download my data. You get a file with everything listed above, in words rather
                  than ids.
                </span>,
                <span key="b">
                  <strong>Correct:</strong> change your fields, roles, companies and skills on the Profile page at any time.
                </span>,
                <span key="c">
                  <strong>Erase or withdraw consent:</strong> Profile, then Your data, then Delete my account and data. It takes effect immediately and
                  can&apos;t be undone.
                </span>,
                <span key="d">
                  <strong>Anything else</strong>, including nominating someone: email us using the contact details below. We aim to reply within 30 days.
                </span>,
              ]}
            />
          </Section>

          <Section id="children" title="Age limit">
            <P>
              Vantage is for people aged 18 and over, and we ask you to confirm it. We don&apos;t knowingly keep data about anyone under 18. If you think we
              do, tell us and we will delete it.
            </P>
          </Section>

          <Section id="automated" title="Automated ranking">
            <P>
              Your feed is ranked by fixed, visible rules applied to your choices: your target companies, your field, your role, the skills you are missing
              and how recent a story is. No one is judged by it and it has no legal or similarly significant effect on you. Each story tells you which of
              your choices made it appear. You can change your choices, or hide stories, at any time.
            </P>
          </Section>

          <Section id="security" title="Security and breaches">
            <List
              items={[
                "Passwords are stored only as salted scrypt hashes.",
                "Your session cookie can't be read by page scripts and is only sent to this site.",
                "Repeated wrong passwords pause sign-in for that email for a while.",
                "Deleting an account needs your password, so someone borrowing your open browser can't do it.",
              ]}
            />
            <P>
              If a breach affects your personal data we will tell you and the authorities as the law requires, and say what happened and what to do.
            </P>
          </Section>

          <Section id="transfers" title="Where data is stored">
            <P>
              Your data is stored where this copy of Vantage is hosted: <strong>{info.hosting_region ?? "not set yet"}</strong>. If it is moved out of
              India, or out of the UK or EEA, the person running the service must use the safeguards the DPDP Act and GDPR require.
            </P>
          </Section>

          <Section id="changes" title="Changes to this policy">
            <P>
              When we change this policy, the version date at the top changes. New sign-ups agree to the current version, and we record which one. Read the{" "}
              <Link href="/terms" className="font-semibold text-accent underline underline-offset-4">
                Terms of Use
              </Link>{" "}
              too.
            </P>
          </Section>

          <Section id="contact" title="Contact and grievances">
            <P>
              For privacy questions, to use a right, or to make a complaint, write to us here. The grievance officer is the person who answers complaints
              about how we handle your data.
            </P>
            <Contact info={info} />
          </Section>
        </>
      )}
    </LegalLayout>
  );
}
