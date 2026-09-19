"use client";

import { useInstall } from "@/lib/hooks";
import { ShareIcon } from "./icons";
import { Button, Card } from "./ui";

export function InstallCard() {
  const { canPrompt, install, ios, standalone } = useInstall();

  return (
    <Card>
      <h2 className="font-display text-xl">Install Vantage</h2>
      {standalone ? (
        <p className="mt-2 text-[15px] text-muted">Vantage is installed on this device. It opens full screen from your home screen or apps list.</p>
      ) : (
        <>
          <p className="mt-2 text-[15px] text-muted">
            Add it to your device for a full-screen app, quick launch, and your last feed available offline.
          </p>
          {canPrompt ? (
            <Button variant="primary" className="mt-4" onClick={install}>
              Install app
            </Button>
          ) : ios ? (
            <p className="mt-3 flex flex-wrap items-center gap-1.5 text-[15px]">
              On iPhone or iPad, tap
              <ShareIcon width={18} height={18} className="text-accent" />
              <strong>Share</strong>, then <strong>Add to Home Screen</strong>.
            </p>
          ) : (
            <p className="mt-3 text-[15px]">
              Open your browser menu and choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.
            </p>
          )}
        </>
      )}
    </Card>
  );
}
