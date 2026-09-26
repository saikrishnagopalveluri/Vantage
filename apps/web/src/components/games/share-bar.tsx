"use client";

import { useId, useState } from "react";
import { intents } from "@/lib/share";
import { CopyIcon, DownloadIcon, ShareIcon } from "../icons";
import { Button } from "../ui";

/** The "post your score" section on a mini-game's (or a badge's) over/unlock screen: a native share
 *  sheet (with the card attached as an image, on a phone that supports it — this is what lets
 *  WhatsApp and Instagram pick it up directly), WhatsApp/LinkedIn/X links as a fallback, and a plain
 *  save/copy for anywhere else. Shared so every card looks and behaves the same way; only the card
 *  data, how it's drawn, and the wording change per caller. */
export function ShareBar<T>({
  card,
  draw,
  heading = "Post your score",
  subheading = "Your post shows only your score. Not your name, email or profile.",
  fileName,
  shareTitle,
  shareText,
  url,
}: {
  card: T;
  /** How to render `card` onto the canvas — e.g. `drawShareCard` for a game's score card. */
  draw: (card: T, origin: string) => Promise<Blob>;
  heading?: string;
  subheading?: string;
  fileName: string;
  shareTitle: string;
  shareText: string;
  url: string;
}) {
  const [status, setStatus] = useState("");
  const titleId = useId();
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  const image = () => draw(card, origin);

  const share = async () => {
    try {
      const blob = await image();
      const file = new File([blob], fileName, { type: "image/png" });
      const withFile = navigator.canShare?.({ files: [file] }) ? { files: [file] } : {};
      await navigator.share({ title: shareTitle, text: shareText, url, ...withFile });
    } catch (e) {
      if ((e as Error).name !== "AbortError") setStatus("Sharing didn't work here. Try one of the buttons instead.");
    }
  };
  const save = async () => {
    try {
      const blob = await image();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = fileName;
      a.click();
      window.setTimeout(() => URL.revokeObjectURL(href), 2000);
      setStatus("Image saved. Attach it to your post.");
    } catch {
      setStatus("Couldn't make the image in this browser.");
    }
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${shareText} ${url}`);
      setStatus("Copied. Paste it wherever you like.");
    } catch {
      setStatus("Couldn't copy. Select the text and copy it yourself.");
    }
  };

  const link = "btn-raised inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-[15px] font-semibold text-ink";
  return (
    <section aria-labelledby={titleId} className="raised rounded-2xl p-4">
      <h3 id={titleId} className="font-display text-xl">
        {heading}
      </h3>
      <p className="mt-1 text-sm text-muted">{subheading}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {canShare && (
          <Button variant="primary" onClick={share} className="px-3.5">
            <ShareIcon width={18} height={18} />
            Share
          </Button>
        )}
        <a className={link} href={intents.linkedin(url)} target="_blank" rel="noopener noreferrer">
          LinkedIn
        </a>
        <a className={link} href={intents.x(shareText, url)} target="_blank" rel="noopener noreferrer">
          X
        </a>
        <a className={link} href={intents.whatsapp(shareText, url)} target="_blank" rel="noopener noreferrer">
          WhatsApp
        </a>
        <Button onClick={save} className="px-3.5">
          <DownloadIcon width={18} height={18} />
          Save image
        </Button>
        <Button onClick={copy} className="px-3.5">
          <CopyIcon width={18} height={18} />
          Copy text
        </Button>
      </div>
      <p role="status" className="mt-2 min-h-5 text-sm text-muted">
        {status}
      </p>
    </section>
  );
}
